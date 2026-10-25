"""Read the public leaderboard through the dedicated browser's own requests.

Only rank, public team name and score are retained from each response row.
Request bodies, credentials, member lists and user/domain IDs are never read
or persisted. Only page one is read; all callers share a two-hour cache.
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from uuid import uuid4

from .browser import BrowserError, cdp_websocket
from .jobs import SubmissionLock
from .records import CHINA_TIME, parse_score


RANKING_URL = "https://developer.huaweicloud.com/competition/information/1300000312/ranking"
RANKING_API_URL = "https://devdata2.huaweicloud.com/rest/developer/fwdu/rest/developer/user/hdcompetitionservice/v1/teams/ranking"
REFRESH_INTERVAL = timedelta(hours=2)


class RankingError(RuntimeError):
    pass


def _entry(row: object) -> dict:
    if not isinstance(row, dict):
        raise RankingError("Leaderboard contains a non-object row")
    rank, name, score = row.get("ranking"), row.get("team_name"), parse_score(row.get("score"))
    if type(rank) is not int or rank < 1:
        raise RankingError("Leaderboard row has an invalid rank")
    if not isinstance(name, str) or not name.strip() or len(name) > 500:
        raise RankingError("Leaderboard row has an invalid public team name")
    if score is None:
        raise RankingError("Leaderboard row has an invalid score")
    return {"rank": rank, "team_name": name.strip(), "score": score}


def parse_ranking_response(payload: object, http_status: int = 200) -> dict:
    """Whitelist public fields; observed naive API refresh_time is UTC."""
    if http_status in (401, 403):
        raise RankingError("Leaderboard requires manual browser authentication")
    if type(http_status) is not int or not 200 <= http_status < 300:
        raise RankingError("Leaderboard returned an unsuccessful HTTP status")
    if not isinstance(payload, dict):
        raise RankingError("Leaderboard response is not an object")
    total = payload.get("total")
    rows, current = payload.get("team_ranking_list"), payload.get("current_team_ranking")
    if type(total) is not int or total < 0 or not isinstance(rows, list) or not isinstance(current, list):
        raise RankingError("Leaderboard is missing valid rows, current team or total")
    stage, refreshed = payload.get("stage_name"), payload.get("refresh_time")
    if not isinstance(stage, str) or not isinstance(refreshed, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?", refreshed):
        raise RankingError("Leaderboard has invalid stage/refresh metadata")
    try:
        timestamp = datetime.fromisoformat(refreshed.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        refreshed = timestamp.astimezone(CHINA_TIME).isoformat(timespec="seconds")
    except ValueError:
        raise RankingError("Leaderboard has an invalid refresh timestamp") from None
    return {"total": total, "stage_name": stage, "refreshed_at": refreshed,
            "entries": [_entry(row) for row in rows],
            "current_teams": [_entry(row) for row in current]}


def first_page_snapshot(head: dict) -> dict:
    """Validate page one without requiring or fetching the remaining rows."""
    entries, seen = head["entries"], set()
    for i, row in enumerate(entries):
        identity = (row["rank"], row["team_name"])
        if identity in seen:
            raise RankingError("Leaderboard page contains duplicate entries")
        seen.add(identity)
        if i and (row["rank"] < entries[i-1]["rank"] or row["score"] > entries[i-1]["score"]):
            raise RankingError("Leaderboard page is not in ranking order")
    if (head["total"] and not entries) or len(entries) > head["total"] or (entries and entries[0]["rank"] != 1):
        raise RankingError("Leaderboard first/top page is missing or invalid")
    current = head["current_teams"][0] if len(head["current_teams"]) == 1 else None
    leader = entries[0] if entries else None
    # An off-page team has no known immediate predecessor on page one.
    higher = [row["score"] for row in entries if current in entries and row["score"] > current["score"]]
    return {"schema_version": 2, "source": "browser_observed_api", "url": RANKING_URL,
            "captured_at": datetime.now(CHINA_TIME).isoformat(timespec="seconds"),
            "refreshed_at": head["refreshed_at"], "stage_name": head["stage_name"],
            "scope": "first_page", "complete": len(entries) == head["total"],
            "total": head["total"], "row_count": len(entries), "page_count": 1,
            "leader": leader, "current_team": current, "current_teams": head["current_teams"],
            "gap_to_leader": leader["score"] - current["score"] if leader and current else None,
            "gap_to_next_higher_score": min(higher) - current["score"] if higher else None,
            "entries": entries}


def _is_ranking_response(response) -> bool:
    actual, expected = urlsplit(response.url), urlsplit(RANKING_API_URL)
    return response.request.method != "OPTIONS" and (actual.scheme, actual.hostname, actual.path) == (
        expected.scheme, expected.hostname, expected.path)


def _read_response(response) -> dict:
    if response.status in (401, 403):
        raise RankingError("Leaderboard requires manual browser authentication")
    try:
        payload = response.json()
    except Exception:
        raise RankingError("Leaderboard did not return valid JSON") from None
    return parse_ranking_response(payload, response.status)


def collect_first_page(page, timeout_ms: int) -> dict:
    """One page navigation, one observed ranking response, no pagination."""
    page.set_default_timeout(timeout_ms)
    with page.expect_response(_is_ranking_response, timeout=timeout_ms) as event:
        page.goto(RANKING_URL, wait_until="domcontentloaded", timeout=timeout_ms)
    return first_page_snapshot(_read_response(event.value))


def _collect_in_context(context, timeout_ms: int) -> dict:
    page = context.new_page()
    try:
        return collect_first_page(page, timeout_ms)
    finally:
        page.close()


def collect_ranking(config: dict, *, context=None) -> dict:
    """Open a separate temporary tab; never navigate/close the submission tab."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RankingError("Playwright is required to read the live leaderboard") from None
    try:
        if context is not None:
            return _collect_in_context(context, int(config["action_timeout_ms"]))
        with sync_playwright() as runtime:
            browser = runtime.chromium.connect_over_cdp(cdp_websocket(config["cdp_url"]), timeout=10000)
            if not browser.contexts:
                raise RankingError("Dedicated Chrome has no accessible browser context")
            return _collect_in_context(browser.contexts[0], int(config["action_timeout_ms"]))
            # Exiting Playwright disconnects; do not close the attached browser.
    except RankingError:
        raise
    except BrowserError:
        raise RankingError("Dedicated Chrome is unavailable; run judge.py browser or check its connection") from None
    except Exception as exc:
        raise RankingError("Leaderboard collection failed (" + type(exc).__name__ +
                           "); check the dedicated Chrome login and ranking page") from None


def save_ranking(snapshot: dict, directory: Path) -> dict:
    """Persist normalized JSON and CSV, plus an atomic latest.json pointer."""
    directory.mkdir(parents=True, exist_ok=True)
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid4().hex[:8]
    path = directory / (name + ".json")
    csv_path = directory / (name + ".csv")
    text = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("rank", "team_name", "score"))
        writer.writeheader()
        for row in snapshot["entries"]:
            # Public team names are untrusted; prevent spreadsheet formulas.
            name_value = row["team_name"]
            writer.writerow(row | {"team_name": "'" + name_value if name_value.lstrip().startswith(
                ("=", "+", "-", "@")) else name_value})
    latest_tmp = directory / (name + ".tmp")
    latest_tmp.write_text(text, encoding="utf-8")
    latest_tmp.replace(directory / "latest.json")
    return {"snapshot_path": str(path.resolve()), "csv_path": str(csv_path.resolve()),
            **{key: snapshot[key] for key in ("captured_at", "refreshed_at", "total", "complete", "scope", "row_count",
                                             "leader", "current_team", "gap_to_leader",
                                             "gap_to_next_higher_score")}}


def _write_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Cached leaderboard time must include a timezone")
    return parsed


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def get_ranking(config: dict, *, context=None) -> tuple[dict, dict]:
    """Shared cache and attempt cooldown apply to CLI and every submission.

    Even a failed attempt consumes the two-hour check interval. No force-refresh
    option bypasses this policy. A process lock prevents parallel cache misses.
    """
    directory = Path(config["runs_directory"]) / "rankings"
    directory.mkdir(parents=True, exist_ok=True)
    with SubmissionLock(directory / ".ranking.lock"):
        now = datetime.now(CHINA_TIME)
        state_path = directory / "check_state.json"
        state = _read_json(state_path)
        cached = _read_json(directory / "latest.json")
        deadlines = []
        if cached:
            try:
                deadlines.append(_timestamp(cached["captured_at"]) + REFRESH_INTERVAL)
                if cached["url"] != RANKING_URL or not isinstance(cached["entries"], list):
                    raise ValueError("Invalid cached leaderboard")
                # Migrate the previously collected full board locally. Keep its
                # real capture time; migration is not a new network observation.
                if cached.get("scope") != "first_page":
                    original_time = cached["captured_at"]
                    cached = first_page_snapshot(cached | {"entries": cached["entries"][:10]})
                    cached["captured_at"] = original_time
                    state["files"] = save_ranking(cached, directory)
                    _write_json(state_path, state)
            except (KeyError, ValueError, TypeError, RankingError):
                cached = {}
        if state.get("next_check_at"):
            try:
                deadlines.append(_timestamp(state["next_check_at"]))
            except (ValueError, TypeError):
                pass
        next_check = max(deadlines) if deadlines else now

        def reference(cache_hit: bool, *, stale=False) -> dict:
            files = {"snapshot_path": str((directory / "latest.json").resolve()),
                     **{key: cached.get(key) for key in ("captured_at", "refreshed_at", "total", "complete",
                                                         "scope", "row_count", "leader", "current_team",
                                                         "gap_to_leader", "gap_to_next_higher_score")},
                     **state.get("files", {})}
            return {**files, "cache_hit": cache_hit, "stale": stale,
                    "next_check_at": next_check.isoformat(timespec="seconds")}

        if now < next_check:
            if cached:
                return cached, reference(True, stale=bool(state.get("last_error_type")))
            raise RankingError("Leaderboard check is throttled until " + next_check.isoformat(timespec="seconds"))

        next_check = now + REFRESH_INTERVAL
        state.update(last_attempt_at=now.isoformat(timespec="seconds"),
                     next_check_at=next_check.isoformat(timespec="seconds"))
        # Persist cooldown before any browser request, also covering interruption.
        _write_json(state_path, state)
        try:
            snapshot = collect_ranking(config, context=context)
            state["files"] = save_ranking(snapshot, directory)
            state.pop("last_error_type", None)
            _write_json(state_path, state)
            return snapshot, reference(False)
        except Exception as exc:
            state["last_error_type"] = type(exc).__name__
            _write_json(state_path, state)
            if cached:
                return cached, reference(True, stale=True)
            raise RankingError("Leaderboard reference unavailable; next check after " +
                               next_check.isoformat(timespec="seconds")) from None
