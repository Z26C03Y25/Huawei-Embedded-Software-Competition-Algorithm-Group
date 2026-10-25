"""Offline, resumable submission jobs. This module never uploads or retries.

JobStore.root is the runs directory itself. Callers hold SubmissionLock around
operations that may submit or update the shared store; JSON replacement is
atomic even when a reader does not hold that lock.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Iterable
from uuid import uuid4

from .records import SubmissionRecord, normalize_record


TERMINAL_STATES = frozenset(("completed", "failed"))
_JOB_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _records(records: Iterable[SubmissionRecord | dict]) -> list[SubmissionRecord]:
    return [record if isinstance(record, SubmissionRecord) else normalize_record(record)
            for record in records]


def _server_id(record: SubmissionRecord) -> str | None:
    return getattr(record, "submission_id", None)


def _baseline_server_ids(job: dict) -> set[str]:
    # Derive from full rows as well, so jobs saved before this field was added
    # remain compatible when their rows already happened to contain IDs.
    return {str(value) for value in job.get("baseline_submission_ids", [])
            if value is not None} | {
        str(row["submission_id"]) for row in job.get("baseline", [])
        if row.get("submission_id") is not None}


def validate_snapshot(job: dict) -> None:
    """Raise ValueError if saved source bytes, length or digest have changed."""
    try:
        contents = Path(job["snapshot_path"]).read_bytes()
    except (KeyError, OSError, TypeError) as exc:
        raise ValueError("Submission snapshot is missing or unreadable") from exc
    if len(contents) != job.get("size"):
        raise ValueError("Submission snapshot size does not match the saved job")
    if hashlib.sha256(contents).hexdigest() != job.get("sha256"):
        raise ValueError("Submission snapshot SHA-256 does not match the saved job")


def observe(job: dict, records: Iterable[SubmissionRecord | dict]) -> str:
    """Update a job from history rows without saving it or sending any request.

    Server submission IDs take precedence over the legacy filename/time pair.
    After an ID is bound, DOM rows without IDs cannot complete the job: their
    displayed timestamp may alias a different submission within the same second.
    A timeout is resumable; graded/failed terminal jobs never get downgraded.
    """
    if job.get("state") in TERMINAL_STATES:
        return job["state"]
    current = _records(records)
    job["last_observed_at"] = _now()
    bound = job.get("bound_identity")
    bound_id = job.get("bound_submission_id")
    if bound_id is None and job.get("state") == "ambiguous" and (
            bound is None or job.get("ambiguous_submission_ids")):
        # Pagination or a transient refresh can hide one of the competing
        # rows. Its disappearance is not evidence that the other row is ours.
        job["last_error"] = "Submission identity remains ambiguous; explicitly select a bound_submission_id or unique bound_identity"
        return job["state"]
    if bound_id is not None:
        matches = [record for record in current if _server_id(record) == bound_id]
        if not matches:
            job["state"] = "pending"
            job["last_error"] = (
                "The bound server submission ID is absent; waiting for API history. "
                "DOM filename/time matches cannot identify same-second submissions safely")
            return job["state"]
    elif bound is not None:
        identity = tuple(bound)
        matches = [record for record in current if record.identity == identity]
        if not matches:
            job["state"] = "pending"
            job["last_error"] = "The bound submission row is temporarily absent from history"
            return job["state"]
    else:
        baseline = {tuple(identity) for identity in job.get("baseline_identities", [])}
        latest_baseline_time = max((identity[1] for identity in baseline), default=None)
        baseline_ids = _baseline_server_ids(job)
        known_api_identities = {
            (row["filename"], row["submitted_at"]) for row in job.get("baseline", [])
            if row.get("submission_id") is not None}
        matches = []
        for record in current:
            if record.filename != "main.cpp":
                continue
            submission_id = _server_id(record)
            if submission_id is not None and baseline_ids:
                # A new ID can distinguish a same-second upload, but discovering
                # an older page or adding API IDs to former DOM rows cannot.
                if submission_id in baseline_ids:
                    continue
                if latest_baseline_time is not None and record.submitted_at < latest_baseline_time:
                    continue
                if record.identity in baseline and record.identity not in known_api_identities:
                    continue
            elif record.identity in baseline or (
                    latest_baseline_time is not None and record.submitted_at <= latest_baseline_time):
                # DOM-only baselines do not prove whether a newly visible API
                # ID belongs to an old or new upload in the same display second.
                continue
            matches.append(record)
        if not matches:
            job["state"] = "pending"
            job["last_error"] = "No new main.cpp submission row is visible yet; do not re-upload"
            return job["state"]
    if len(matches) != 1:
        job["state"] = "ambiguous"
        job["candidate_records"] = [record.to_dict() for record in matches]
        job["ambiguous_submission_ids"] = sorted({
            _server_id(record) for record in matches if _server_id(record) is not None})
        job["last_error"] = "Multiple matching submission rows are visible; identity is ambiguous"
        return job["state"]

    record = matches[0]
    job["bound_identity"] = list(record.identity)
    if _server_id(record) is not None:
        job["bound_submission_id"] = _server_id(record)
    job["record"] = record.to_dict()
    job.pop("candidate_records", None)
    job.pop("ambiguous_submission_ids", None)
    job["last_error"] = None
    if record.status == "success" and record.score is not None:
        job["state"] = "completed"
        job["score"] = record.score  # A final zero is a valid result.
        job["finished_at"] = _now()
    elif record.status == "failed":
        job["state"] = "failed"
        job["score"] = None
        job["finished_at"] = _now()
        job["last_error"] = record.status_text or "Submission judging failed"
    else:
        job["state"] = "pending"
        job["score"] = None
        if record.status == "unknown":
            job["last_error"] = "Unknown submission status: " + (record.status_text or "(empty)")
        elif record.status == "success":
            job["last_error"] = "Submission reports success but its final score is not available"
    return job["state"]


class JobStore:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def _directory(self, job_id: str) -> Path:
        if not isinstance(job_id, str) or not _JOB_ID.fullmatch(job_id):
            raise ValueError("Invalid submission job ID")
        return self.root / job_id

    def create(self, source_path: Path, baseline: list[SubmissionRecord], *,
               contents: bytes | None = None) -> dict:
        source = Path(source_path).resolve(strict=True)
        contents = source.read_bytes() if contents is None else contents
        if not isinstance(contents, bytes) or not contents:
            raise ValueError("Submission source must contain nonempty original bytes")
        rows = _records(baseline)
        job_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ_") + uuid4().hex[:12]
        directory = self._directory(job_id)
        directory.mkdir(parents=True, exist_ok=False)
        snapshot = directory / "main.cpp"
        snapshot.write_bytes(contents)
        job = {
            "version": 1,
            "job_id": job_id,
            "state": "snapshot_ready",
            "created_at": _now(),
            "source_path": str(source),
            "snapshot_path": str(snapshot),
            "sha256": hashlib.sha256(contents).hexdigest(),
            "size": len(contents),
            "baseline": [record.to_dict() for record in rows],
            "baseline_identities": [list(record.identity) for record in rows],
            "baseline_submission_ids": sorted({
                _server_id(record) for record in rows if _server_id(record) is not None}),
            "bound_identity": None,
            "bound_submission_id": None,
            "record": None,
            "score": None,
            "last_error": None,
        }
        self.save(job)
        return job

    def load(self, job_id: str) -> dict:
        path = self._directory(job_id) / "job.json"
        with path.open("r", encoding="utf-8") as stream:
            job = json.load(stream)
        if not isinstance(job, dict) or job.get("version") != 1 or job.get("job_id") != job_id:
            raise ValueError("Submission job metadata has an invalid version or identity")
        job.setdefault("baseline_submission_ids", sorted(_baseline_server_ids(job)))
        old_record = job.get("record") or {}
        old_identity = (old_record.get("filename"), old_record.get("submitted_at"))
        upgrade_id = (old_record.get("submission_id")
                      if old_identity == tuple(job.get("bound_identity") or ()) else None)
        job.setdefault("bound_submission_id", upgrade_id)
        return job

    def save(self, job: dict) -> None:
        directory = self._directory(job["job_id"])
        directory.mkdir(parents=True, exist_ok=True)
        # Serialize before touching the prior metadata. A failed write/replace
        # leaves the old complete JSON usable for recovery.
        payload = json.dumps(job, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                             dir=directory, prefix="job_", suffix=".tmp",
                                             delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, directory / "job.json")
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def pending_for_hash(self, sha: str) -> list[dict]:
        if not self.root.exists():
            return []
        pending = []
        for path in sorted(self.root.glob("*/job.json")):
            job = self.load(path.parent.name)
            if job.get("sha256") == sha and job.get("state") not in TERMINAL_STATES:
                pending.append(job)
        return pending

    def validate_snapshot(self, job: dict) -> None:
        expected = self._directory(job["job_id"]) / "main.cpp"
        if Path(job["snapshot_path"]).resolve() != expected.resolve():
            raise ValueError("Snapshot path is outside its submission job directory")
        validate_snapshot(job)

    observe = staticmethod(observe)


class SubmissionLock:
    """Nonblocking OS-backed cross-process lock; lock files are never deleted."""
    def __init__(self, path: Path):
        self.path = Path(path)
        self._stream = None

    def __enter__(self):
        if self._stream is not None:
            raise RuntimeError("SubmissionLock is already held by this instance")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stream = self.path.open("a+b")
        try:
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            stream.close()
            raise RuntimeError(f"Another submission process holds the lock: {self.path}") from exc
        self._stream = stream
        return self

    def __exit__(self, exc_type, exc, traceback):
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                if os.name == "nt":
                    import msvcrt
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            finally:
                stream.close()
        return False
