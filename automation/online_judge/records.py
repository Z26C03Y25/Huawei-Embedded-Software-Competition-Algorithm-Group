"""Normalize Huawei submission rows without depending on a browser library.

``parse_submission_html(html)`` reads rows in DOM order from
``table.tiny-grid__body tbody tr``. ``first_record(rows)`` therefore means the
latest displayed submission, never the submission with the highest score.

Capture ``RecordBaseline.from_records(rows, source_mtime_ns=...)`` BEFORE an
upload. Then call ``first_new_record`` on subsequent snapshots, optionally with
the expected filename, a local China-time cutoff, and the snapshot file's mtime.
Changing an old row's score/status, changing its data-rowid, or merely rewriting
the snapshot file cannot create a new submission identity. A newly detected
pending row should be tracked by ``identity`` with ``find_record`` until its
status becomes terminal. A score of zero is a number; a pending score is None.

The visible stable identity is (filename, submitted_at), where submitted_at has
second precision. Two uploads of the same filename within the same displayed
second cannot be distinguished using these columns and are deliberately not
claimed as distinct submissions. File mtimes are freshness guards, not evidence
that an upload happened. No network or browser actions are performed here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import json
import re
from typing import Iterable, Mapping, Sequence


Identity = tuple[str, str]
CHINA_TIME = timezone(timedelta(hours=8))
_TIME_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\Z")
_SCORE_RE = re.compile(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)\Z")
_VOID_TAGS = frozenset(("area", "base", "br", "col", "embed", "hr", "img", "input",
                        "link", "meta", "param", "source", "track", "wbr"))
_COLUMNS = frozenset(("col_1", "col_2", "col_3", "col_6", "col_7"))


def _text(value: object) -> str:
    return " ".join(str(value).split()) if value is not None else ""


def parse_submitted_at(value: str) -> datetime:
    """Validate the exact displayed YYYY-MM-DD HH:MM:SS format (China local time)."""
    if not isinstance(value, str) or not _TIME_RE.fullmatch(value):
        raise ValueError("submitted_at must use YYYY-MM-DD HH:MM:SS")
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise ValueError(f"invalid submission date/time: {value}") from exc


def parse_score(value: object) -> int | None:
    """Return nonnegative integer scores, including 0; nonnumeric states are None."""
    if type(value) is int:
        return value if value >= 0 else None
    if not isinstance(value, str):
        return None
    value = _text(value)
    return int(value.replace(",", "")) if _SCORE_RE.fullmatch(value) else None


def normalize_status(value: object, hint: object = None) -> str:
    """Map visible status text or a CSS status hint to success/failed/pending/unknown."""
    status = _text(value).lower()
    aliases = {
        "success": "success", "succeeded": "success", "completed": "success",
        "failed": "failed", "fail": "failed", "failure": "failed", "error": "failed",
        "rejected": "failed", "pending": "pending", "running": "pending",
        "scoring": "pending", "judging": "pending", "queued": "pending",
        "waiting": "pending", "processing": "pending", "queue": "pending",
    }
    if status in aliases:
        return aliases[status]
    if any(word in status for word in ("失败", "错误", "异常", "不成功", "未成功")):
        return "failed"
    if any(word in status for word in ("排队", "评测中", "评分中", "判分中", "等待", "处理中", "待评测")):
        return "pending"
    if "成功" in status:
        return "success"
    normalized_hint = _text(hint).lower()
    return aliases.get(normalized_hint, "unknown")


@dataclass(frozen=True)
class SubmissionRecord:
    filename: str
    submission_type: str
    submitted_at: str
    score: int | None
    status: str
    status_text: str = ""
    score_text: str = ""
    row_id: str | None = None  # Diagnostic only: TinyGrid row IDs change on refresh.
    submission_id: str | None = None  # Stable server identifier when read from the API.
    source: str = "dom"

    def __post_init__(self) -> None:
        if not isinstance(self.filename, str) or not self.filename.strip():
            raise ValueError("filename must be nonempty")
        parse_submitted_at(self.submitted_at)
        if self.score is not None and (type(self.score) is not int or self.score < 0):
            raise ValueError("score must be a nonnegative integer or None")
        if self.status not in ("success", "failed", "pending", "unknown"):
            raise ValueError("status must be success, failed, pending, or unknown")
        if self.submission_id is not None and (not isinstance(self.submission_id, str) or not self.submission_id):
            raise ValueError("submission_id must be a nonempty string or None")
        if not isinstance(self.source, str) or not self.source:
            raise ValueError("source must be a nonempty string")

    @property
    def identity(self) -> Identity:
        return (self.filename, self.submitted_at)

    @property
    def identity_key(self) -> str:
        return json.dumps(self.identity, ensure_ascii=False, separators=(",", ":"))

    @property
    def is_terminal(self) -> bool:
        return self.status in ("success", "failed")

    @property
    def succeeded(self) -> bool:
        return self.status == "success"

    def to_dict(self) -> dict:
        return {**asdict(self), "identity": list(self.identity), "identity_key": self.identity_key}


def normalize_record(row: Mapping[str, object]) -> SubmissionRecord:
    """Normalize a browser-extracted mapping; canonical and col_N keys are accepted.

    Canonical keys: filename, submission_type, submitted_at, score, status.
    Optional raw fields: status_text, score_text, row_id, status_hint.
    Invalid/missing timestamps raise ValueError rather than becoming new identities.
    """
    def pick(*keys, default=""):
        for key in keys:
            if key in row and row[key] is not None:
                return row[key]
        return default

    filename = _text(pick("filename", "file_name", "name", "col_1"))
    submission_type = _text(pick("submission_type", "type", "category", "col_2"))
    submitted_at = _text(pick("submitted_at", "submittedAt", "submission_time", "time", "col_3"))
    score_value = pick("score", "score_text", "col_7", default=None)
    score_text = _text(pick("score_text", "score", "col_7"))
    status_value = pick("status", "status_text", "col_6")
    status_text = _text(pick("status_text", "status", "col_6"))
    status = normalize_status(status_value, pick("status_hint"))
    row_id = _text(pick("row_id", "data-rowid")) or None
    submission_id = pick("submission_id", "submissionId", default=None)
    source = pick("source", default="dom")
    return SubmissionRecord(filename, submission_type, submitted_at, parse_score(score_value),
                            status, status_text, score_text, row_id, submission_id, source)


@dataclass
class _Cell:
    column: str
    depth: int
    chunks: list[str] = field(default_factory=list)
    score_chunks: list[str] = field(default_factory=list)
    score_seen: bool = False
    status_hints: list[str] = field(default_factory=list)


class _SubmissionParser(HTMLParser):
    def __init__(self, strict: bool):
        super().__init__(convert_charrefs=True)
        self.strict = strict
        self.records: list[SubmissionRecord] = []
        self.stack: list[str] = []
        self.table_depth = None
        self.body_depth = None
        self.row_depth = None
        self.row_id = None
        self.cells: dict[str, _Cell] = {}
        self.cell: _Cell | None = None
        self.score_depth = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()
        depth = len(self.stack) + 1
        if tag not in _VOID_TAGS:
            self.stack.append(tag)
        if tag == "table" and self.table_depth is None and "tiny-grid__body" in classes:
            self.table_depth = depth
        elif tag == "tbody" and self.table_depth is not None and self.body_depth is None:
            self.body_depth = depth
        elif tag == "tr" and self.body_depth is not None and self.row_depth is None:
            self.row_depth = depth
            self.row_id = attrs.get("data-rowid")
            self.cells = {}
        elif tag == "td" and self.row_depth is not None and self.cell is None:
            column = attrs.get("data-colid")
            if column in _COLUMNS:
                self.cell = _Cell(column, depth)
        if self.cell is not None:
            if self.cell.column == "col_7" and "scoringBox" in classes:
                self.score_depth = depth
                self.cell.score_seen = True
            if self.cell.column == "col_6":
                self.cell.status_hints.extend(c for c in classes
                                              if c in ("success", "failed", "failure", "error", "pending", "scoring", "running"))
            if tag == "br":
                self.cell.chunks.append(" ")
                if self.score_depth is not None:
                    self.cell.score_chunks.append(" ")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.chunks.append(data)
            if self.score_depth is not None:
                self.cell.score_chunks.append(data)

    def handle_endtag(self, tag):
        if tag not in self.stack:
            return
        position = len(self.stack) - 1 - self.stack[::-1].index(tag)
        depth = position + 1
        if self.score_depth is not None and self.score_depth >= depth:
            self.score_depth = None
        if self.cell is not None and self.cell.depth >= depth:
            self.cells[self.cell.column] = self.cell
            self.cell = None
        if self.row_depth is not None and self.row_depth >= depth:
            self._finish_row()
            self.row_depth = None
        if self.body_depth is not None and self.body_depth >= depth:
            self.body_depth = None
        if self.table_depth is not None and self.table_depth >= depth:
            self.table_depth = None
        del self.stack[position:]

    def _finish_row(self):
        mapping = {column: _text("".join(cell.chunks)) for column, cell in self.cells.items()}
        # Empty-grid placeholders normally have only a colspan cell; ignore them.
        if not mapping.get("col_1") or not mapping.get("col_3"):
            return
        score_cell = self.cells.get("col_7")
        mapping["col_7"] = (_text("".join(score_cell.score_chunks))
                            if score_cell is not None and score_cell.score_seen else "")
        status_cell = self.cells.get("col_6")
        mapping["status_hint"] = status_cell.status_hints[0] if status_cell and status_cell.status_hints else ""
        mapping["row_id"] = self.row_id
        try:
            self.records.append(normalize_record(mapping))
        except ValueError:
            if self.strict:
                raise


def parse_submission_html(html: str, *, strict: bool = True) -> list[SubmissionRecord]:
    """Parse the specified grid and retain DOM order; invalid dates raise by default."""
    parser = _SubmissionParser(strict)
    parser.feed(html)
    parser.close()
    return parser.records


def first_record(records: Iterable[SubmissionRecord]) -> SubmissionRecord | None:
    """First DOM row, not max(score) and not a timestamp re-sort."""
    return next(iter(records), None)


def _normalize_identity(identity: Sequence[str] | str) -> Identity:
    if isinstance(identity, str):
        identity = json.loads(identity)
    if len(identity) != 2 or not all(isinstance(value, str) for value in identity):
        raise ValueError("identity must contain filename and submitted_at")
    filename, submitted_at = identity
    if not filename:
        raise ValueError("identity filename must be nonempty")
    parse_submitted_at(submitted_at)
    return (filename, submitted_at)


@dataclass(frozen=True)
class RecordBaseline:
    identities: frozenset[Identity]
    source_mtime_ns: int | None = None

    def __post_init__(self):
        object.__setattr__(self, "identities", frozenset(_normalize_identity(identity)
                                                       for identity in self.identities))
        if self.source_mtime_ns is not None and (type(self.source_mtime_ns) is not int or self.source_mtime_ns < 0):
            raise ValueError("source_mtime_ns must be a nonnegative integer or None")

    @classmethod
    def from_records(cls, records: Iterable[SubmissionRecord], source_mtime_ns: int | None = None):
        return cls(frozenset(record.identity for record in records), source_mtime_ns)

    def to_dict(self) -> dict:
        return {"identities": [list(identity) for identity in sorted(self.identities)],
                "source_mtime_ns": self.source_mtime_ns}

    @classmethod
    def from_dict(cls, value: Mapping[str, object]):
        return cls(frozenset(_normalize_identity(identity) for identity in value["identities"]),
                   value.get("source_mtime_ns"))


def find_record(records: Iterable[SubmissionRecord], identity: Sequence[str] | str) -> SubmissionRecord | None:
    identity = _normalize_identity(identity)
    return next((record for record in records if record.identity == identity), None)


def new_records(records: Iterable[SubmissionRecord], baseline: RecordBaseline | Iterable[Identity], *,
                expected_filename: str | None = None,
                submitted_not_before: str | datetime | None = None,
                source_mtime_ns: int | None = None) -> list[SubmissionRecord]:
    """Find identities absent from the pre-upload baseline, preserving DOM order.

    When BOTH baseline and current source mtimes are supplied, the current mtime
    must be strictly newer. A newer mtime still does not make an old identity new.
    ``submitted_not_before`` is an additional guard, not a substitute for taking
    the baseline. Naive cutoffs are China local time; aware cutoffs are converted.
    Pending rows are returned so the caller can bind their identity before polling
    completion. No status/score transition changes an identity.
    """
    if not isinstance(baseline, RecordBaseline):
        baseline = RecordBaseline(frozenset(baseline))
    if source_mtime_ns is not None:
        if type(source_mtime_ns) is not int or source_mtime_ns < 0:
            raise ValueError("source_mtime_ns must be a nonnegative integer or None")
        if baseline.source_mtime_ns is not None and source_mtime_ns <= baseline.source_mtime_ns:
            return []
    cutoff = submitted_not_before
    if isinstance(cutoff, str):
        cutoff = parse_submitted_at(cutoff)
    if cutoff is not None:
        if not isinstance(cutoff, datetime):
            raise ValueError("submitted_not_before must be a datetime or formatted date/time")
        if cutoff.tzinfo is not None:
            cutoff = cutoff.astimezone(CHINA_TIME).replace(tzinfo=None)
    seen = set(baseline.identities)
    matches = []
    for record in records:
        if record.identity in seen:
            continue
        seen.add(record.identity)
        if expected_filename is not None and record.filename != expected_filename:
            continue
        if cutoff is not None and parse_submitted_at(record.submitted_at) < cutoff:
            continue
        matches.append(record)
    return matches


def first_new_record(records: Iterable[SubmissionRecord], baseline: RecordBaseline | Iterable[Identity],
                     **filters) -> SubmissionRecord | None:
    return first_record(new_records(records, baseline, **filters))
