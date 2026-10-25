"""Pure parser for the confirmed Huawei competition submission-history endpoint.

This module neither makes requests nor accepts, stores or logs browser headers,
cookies or CSRF values. Callers pass the decoded JSON payload and HTTP status.
Only the explicit top-level results list is read, in server-provided order.
Server-created timestamps without an offset are UTC, then displayed at UTC+8.
No request-body stage/competition identifiers are hardcoded here.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Mapping

from .records import CHINA_TIME, SubmissionRecord, parse_score


API_URL = "https://devdata2.huaweicloud.com/rest/developer/fwdu/rest/developer/user/hdcompetitionservice/v1/works/get-competition-works"


class ApiResponseError(RuntimeError):
    """Unexpected status/schema; messages deliberately exclude response data."""


class ApiAuthenticationError(ApiResponseError):
    """Authentication must be completed in the user's browser session."""


_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,9})?(?:Z|[+-][0-9]{2}(?::?[0-9]{2})?)?\Z"
)


def _local_submitted_at(value: object) -> str:
    if not isinstance(value, str) or not _TIMESTAMP.fullmatch(value.strip()):
        raise ApiResponseError("API result has an invalid created_time format")
    try:
        # Python 3.10 accepts fewer ISO forms than 3.11+. Normalize all forms
        # admitted above, preserving datetime's microsecond truncation semantics.
        normalized = re.sub(r"\.(\d+)", lambda match: "." + match[1][:6].ljust(6, "0"),
                            value.strip().replace("Z", "+00:00"))
        normalized = re.sub(r"([+-]\d{2})(?::?(\d{2}))?\Z",
                            lambda match: match[1] + ":" + (match[2] or "00"), normalized)
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(CHINA_TIME).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OverflowError):
        raise ApiResponseError("API result has an invalid created_time value") from None


def _status(status: object, message: object) -> str:
    status = status.strip().lower() if isinstance(status, str) else ""
    message = message.strip().lower() if isinstance(message, str) else ""
    if message == "failed" or status in ("failed", "failure", "error", "rejected"):
        return "failed"
    if status == "completed" and message == "success":
        return "success"
    if status in ("pending", "queued", "waiting", "running", "processing", "scoring", "judging"):
        return "pending"
    return "unknown"


def parse_api_response(payload: object, http_status: int = 200) -> list[SubmissionRecord]:
    """Parse only known fields, excluding PII and every unrecognized response field.

    401/403 raise ApiAuthenticationError; other HTTP errors or malformed results
    raise ApiResponseError. Explicit results=[] is a valid empty history. Numeric
    zero is retained, but it never changes a pending/unknown state into success.
    The observed is_invalid flag is deliberately ignored: real completed work can
    have is_invalid=true and a positive score.
    """
    if type(http_status) is not int or not 100 <= http_status <= 599:
        raise ApiResponseError("Invalid HTTP status for submission history")
    if http_status in (401, 403):
        raise ApiAuthenticationError("Submission history requires browser authentication")
    if http_status >= 400:
        raise ApiResponseError(f"Submission history returned HTTP {http_status}")
    if not isinstance(payload, Mapping) or "results" not in payload:
        raise ApiResponseError("Submission history is missing its results array")
    rows = payload["results"]
    if not isinstance(rows, list):
        raise ApiResponseError("Submission history results must be an array")
    records = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ApiResponseError("Submission history contains an invalid result row")
        submission_id = row.get("id")
        filename = row.get("name")
        stage_name = row.get("stage_name", "")
        if not isinstance(submission_id, str) or not submission_id.strip():
            raise ApiResponseError("API result is missing a valid submission id")
        if not isinstance(filename, str) or not filename.strip():
            raise ApiResponseError("API result is missing a valid submission filename")
        if not isinstance(stage_name, str):
            raise ApiResponseError("API result has an invalid stage name")
        submitted_at = _local_submitted_at(row.get("created_time"))
        score = parse_score(row.get("score"))
        status = _status(row.get("status"), row.get("message"))
        # Do not retain arbitrary raw status/message/score strings: errors can
        # contain sensitive text. Preserve only enums and parsed numeric scores.
        records.append(SubmissionRecord(filename.strip(), stage_name.strip(), submitted_at,
                                        score, status, status_text=status,
                                        score_text=str(score) if score is not None else "",
                                        submission_id=submission_id, source="api"))
    return records
