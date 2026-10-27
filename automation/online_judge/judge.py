#!/usr/bin/env python3
"""Upload one main.cpp snapshot, or read/resume Huawei competition judging.

Run `python automation/online_judge/judge.py --help` for commands. Browser commands require
Playwright; parsing saved HTML and viewing local jobs require only Python.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from online_judge.browser import BASE, BrowserError, connect, doctor, load_config, start_browser
from online_judge.jobs import JobStore, SubmissionLock
from online_judge.records import first_record, parse_submission_html
from online_judge.ranking import get_ranking, save_ranking


def emit(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2), flush=True)


def summary(job: dict) -> dict:
    result = {key: job.get(key) for key in ("job_id", "state", "sha256", "source_path",
                                           "snapshot_path", "score", "record", "last_error")}
    for key in ("ranking_after", "ranking_error"):
        if key in job:
            result[key] = job[key]
    return result


def capture_job_ranking(config: dict, store: JobStore, job: dict, *, context=None) -> None:
    """Optional reference data cannot change a confirmed result or re-upload."""
    if not config.get("capture_ranking_on_completion", False) or job["state"] != "completed" or job.get("ranking_after"):
        return
    try:
        snapshot, saved = get_ranking(config, context=context)
        leader = snapshot["leader"]
        saved["gap_from_submission_to_leader"] = leader["score"] - job["score"] if leader else None
        # The board has its own refresh clock and can lag the judged work.
        saved["note"] = "Leaderboard reference only; its refresh time may precede this submission"
        job["ranking_after"] = saved
        job.pop("ranking_error", None)
    except Exception as exc:
        job["ranking_error"] = "Leaderboard reference unavailable (" + type(exc).__name__ + "); confirmed submission score is unchanged"
        print(job["ranking_error"], file=sys.stderr, flush=True)
    store.save(job)


def exit_for(job: dict) -> int:
    return {"completed": 0, "failed": 3, "ambiguous": 4}.get(job["state"], 2)


def read_records(page, *, refresh: bool = False):
    reader = getattr(page, "records", None)
    if callable(reader):
        return reader(refresh=refresh)
    return parse_submission_html(page.table_html(refresh=refresh))


def wait_for_job(page, store: JobStore, job: dict, timeout: float, interval: float, *, config=None) -> int:
    """Only read records here. In particular, this function never uploads."""
    if job["state"] in {"completed", "failed", "ambiguous"}:
        capture_job_ranking(config or {}, store, job, context=getattr(getattr(page, "page", None), "context", None))
        emit(summary(job))
        return exit_for(job)
    deadline = time.monotonic() + timeout
    started = time.monotonic()
    previous_state = None
    completion_signature = None
    # A resumed/bound work can refresh immediately. Only a genuinely recent,
    # unacknowledged upload gets the remaining20-second delivery grace.
    delivery_grace = 0.0
    if job.get("bound_identity") is None and job.get("bound_submission_id") is None:
        attempted_at = job.get("submission_attempt_at")
        if attempted_at:
            try:
                attempted = datetime.fromisoformat(attempted_at.replace("Z", "+00:00"))
                if attempted.tzinfo is None:
                    raise ValueError("submission attempt timestamp needs an offset")
                age = max(0.0, (datetime.now().astimezone() - attempted).total_seconds())
                delivery_grace = max(0.0, 20.0 - age)
            except (TypeError, ValueError):
                delivery_grace = 20.0
        elif job.get("state") == "delivery_uncertain":
            delivery_grace = 20.0
    while time.monotonic() < deadline:
        try:
            # Give an unacknowledged upload a short interval to finish without
            # reloading its page and possibly aborting an in-flight request.
            refresh = (job.get("bound_identity") is not None or
                       job.get("bound_submission_id") is not None or
                       time.monotonic() - started >= delivery_grace)
            records = read_records(page, refresh=refresh)
            state = store.observe(job, records)
            if state == "completed":
                signature = (job.get("bound_submission_id"), tuple(job["bound_identity"]), job["score"])
                if not refresh or signature != completion_signature:
                    # A cached/pre-refresh DOM is not a fresh confirmation.
                    # Require two refreshed observations of the same stable ID
                    # and score, including a legitimate final score of zero.
                    completion_signature = signature if refresh else None
                    job["state"] = state = "pending"
                    job["score"] = None
                    job.pop("finished_at", None)
                    job["last_error"] = "Waiting for a second identical final score observation"
            else:
                completion_signature = None
            store.save(job)
            if state != previous_state:
                print(f"{job['job_id']}: {state}", file=sys.stderr, flush=True)
                previous_state = state
            if state in {"completed", "failed", "ambiguous"}:
                capture_job_ranking(config or {}, store, job, context=getattr(getattr(page, "page", None), "context", None))
                emit(summary(job))
                return exit_for(job)
        except BrowserError as exc:
            job["last_error"] = str(exc)
            store.save(job)
            emit(summary(job))
            return 5
        except Exception as exc:
            # A transient read/reload failure is not permission to re-upload.
            job["last_error"] = f"{type(exc).__name__}: {exc}"
            store.save(job)
            print(job["last_error"], file=sys.stderr, flush=True)
            completion_signature = None
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(interval, remaining))
    job["state"] = "timed_out"
    store.save(job)
    result = summary(job)
    result["resume"] = f"python automation/judge.py wait {job['job_id']}"
    result["note"] = "The requested polling window ended, not the judge result; resume this work ID without uploading again."
    emit(result)
    return 2


def submit(config: dict, args, store: JobStore) -> int:
    source = args.file.resolve()
    if not source.is_file() or source.suffix.lower() != ".cpp":
        raise ValueError(f"Expected an existing C++ source file: {source}")
    original_bytes = source.read_bytes()
    if not original_bytes:
        raise ValueError("Source file is empty")
    fingerprint = hashlib.sha256(original_bytes).hexdigest()
    with SubmissionLock(Path(config["runs_directory"]) / ".submission.lock"):
        saved_jobs = [store.load(path.parent.name) for path in store.root.glob("*/job.json")]
        other_active = [job for job in saved_jobs if job.get("sha256") != fingerprint and
                        job.get("state") not in {"completed", "failed", "snapshot_ready"}]
        if other_active:
            raise ValueError("Another source still has an unfinished submission: " +
                             ", ".join(job["job_id"] for job in other_active) +
                             ". Run wait JOB_ID before submitting different code.")
        previous = store.pending_for_hash(fingerprint)
        job = None
        if previous:
            if len(previous) != 1:
                raise ValueError("Multiple unfinished jobs have this source hash. Use jobs, then wait JOB_ID.")
            job = previous[0]
            if job["state"] != "snapshot_ready":
                print(f"Resuming {job['job_id']}; no second upload will be sent.", file=sys.stderr, flush=True)
                if args.no_wait:
                    emit(summary(job))
                    return exit_for(job)
                with connect(config) as page:
                    return wait_for_job(page, store, job, args.timeout, args.interval, config=config)
        if job is None and not args.repeat:
            graded = [item for item in saved_jobs if item.get("sha256") == fingerprint and
                      item.get("state") in {"completed", "failed"}]
            if graded:
                job = sorted(graded, key=lambda item: item["created_at"])[-1]
                capture_job_ranking(config, store, job)
                result = summary(job)
                result["reused"] = True
                result["note"] = "This source hash was already judged. Use --repeat for a new upload."
                emit(result)
                return exit_for(job)
        if job is not None:
            store.validate_snapshot(job)
        with connect(config) as page:
            baseline = read_records(page, refresh=True)
            if any(row.status == "pending" for row in baseline):
                raise ValueError("A submission is already pending on the page. Wait for it before another upload.")
            if job is None:
                job = store.create(source, baseline, contents=original_bytes)
            else:
                job["baseline"] = [row.to_dict() for row in baseline]
                job["baseline_identities"] = [list(row.identity) for row in baseline]
            store.validate_snapshot(job)
            # Save BEFORE clicking/selecting: either operation can start a site
            # upload. A crash afterwards must never automatically send it again.
            job["state"] = "delivery_uncertain"
            job["submission_attempt_at"] = datetime.now().astimezone().isoformat()
            job["submission_url"] = config["submission_url"]
            job["profile_directory"] = config["profile_directory"]
            store.save(job)
            print(f"Uploading {job['job_id']} sha256={job['sha256']}", file=sys.stderr, flush=True)
            try:
                page.upload(Path(job["snapshot_path"]))
                job["upload_action_finished"] = True
            except Exception as exc:
                job["last_error"] = f"Upload outcome uncertain: {type(exc).__name__}: {exc}"
                print(job["last_error"], file=sys.stderr, flush=True)
            store.save(job)
            if args.no_wait:
                emit(summary(job))
                return 2
            return wait_for_job(page, store, job, args.timeout, args.interval, config=config)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="configuration JSON, defaults to automation/online_judge/config.json")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="check files and dependencies without opening/contacting a browser")
    commands.add_parser("browser", aliases=["bootstrap"], help="start dedicated Chrome; log in manually once")
    command = commands.add_parser("ranking", help="page-one leaderboard reference, shared two-hour cache; never uploads")
    command.add_argument("--output-dir", type=Path, help="optional local export; does not bypass shared cache")
    for name in ("latest", "history"):
        command = commands.add_parser(name, help="read first row/all visible rows; no upload")
        command.add_argument("--html", type=Path, help="parse saved HTML offline instead of contacting Chrome")
    command = commands.add_parser("submit", help="upload a main.cpp snapshot once, then wait for its new row")
    command.add_argument("--file", type=Path, default=BASE.parents[1] / "main.cpp")
    command.add_argument("--no-wait", action="store_true", help="return the saved job without polling")
    command.add_argument("--repeat", action="store_true", help="upload even if this source hash has already been judged")
    command.add_argument("--timeout", type=float)
    command.add_argument("--interval", type=float)
    command = commands.add_parser("wait", help="resume reading an existing job; never uploads")
    command.add_argument("job_id")
    command.add_argument("--timeout", type=float)
    command.add_argument("--interval", type=float)
    command = commands.add_parser("jobs", help="show saved local jobs")
    command.add_argument("--job", help="show full metadata for one job")
    command = commands.add_parser("bind", help="explicitly select one previously reported ambiguous row; no upload")
    command.add_argument("job_id")
    command.add_argument("--submitted-at", required=True, help="exact displayed YYYY-MM-DD HH:MM:SS")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command == "doctor":
            result = doctor(config)
            emit(result)
            return 0 if result["ready"] else 5
        if args.command in {"browser", "bootstrap"}:
            emit(start_browser(config))
            return 0
        if args.command == "ranking":
            snapshot, saved = get_ranking(config)
            if args.output_dir:
                exported = save_ranking(snapshot, args.output_dir)
                saved = saved | exported
            emit(snapshot | {"files": saved})
            return 0
        if args.command in {"latest", "history"}:
            if args.html:
                rows = parse_submission_html(args.html.read_text(encoding="utf-8"))
            else:
                with connect(config) as page:
                    rows = read_records(page, refresh=True)
            latest = first_record(rows)
            emit(latest.to_dict() if latest else None) if args.command == "latest" else emit(
                [row.to_dict() for row in rows])
            return 0
        store = JobStore(Path(config["runs_directory"]))
        if args.command == "jobs":
            if args.job:
                emit(store.load(args.job))
            else:
                emit([summary(store.load(path.parent.name)) for path in
                      sorted(store.root.glob("*/job.json"), reverse=True)])
            return 0
        if args.command == "bind":
            with SubmissionLock(Path(config["runs_directory"]) / ".submission.lock"):
                job = store.load(args.job_id)
                if job["state"] != "ambiguous":
                    raise ValueError("bind is only available for an explicitly ambiguous job")
                candidates = [row for row in job.get("candidate_records", [])
                              if row.get("filename") == "main.cpp" and
                              row.get("submitted_at") == args.submitted_at]
                if len(candidates) != 1:
                    raise ValueError("The selected time does not identify exactly one saved candidate row")
                job["bound_identity"] = ["main.cpp", args.submitted_at]
                job["state"], job["score"], job["last_error"] = "pending", None, None
                store.save(job)
                emit(summary(job))
                return 2
        args.timeout = args.timeout if args.timeout is not None else float(config["timeout_seconds"])
        args.interval = args.interval if args.interval is not None else float(config["poll_interval_seconds"])
        if args.timeout <= 0 or not 0 < args.interval <= 30:
            raise ValueError("timeout must be positive and interval must be in (0,30]")
        if args.command == "submit":
            return submit(config, args, store)
        with SubmissionLock(Path(config["runs_directory"]) / ".submission.lock"):
            job = store.load(args.job_id)
            if job["state"] in {"completed", "failed", "ambiguous"}:
                capture_job_ranking(config, store, job)
                emit(summary(job))
                return exit_for(job)
            with connect(config) as page:
                return wait_for_job(page, store, job, args.timeout, args.interval, config=config)
    except (BrowserError, ValueError, OSError, RuntimeError) as exc:
        emit({"error": str(exc), "error_type": type(exc).__name__})
        return 5
    except Exception as exc:
        emit({"error": str(exc), "error_type": type(exc).__name__,
              "note": "No upload is retried automatically. Inspect jobs before submitting again."})
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
