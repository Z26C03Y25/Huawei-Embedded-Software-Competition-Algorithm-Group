"""One explicitly selected Huawei judging round; never sweeps candidates.

Run with python/runtime/python.exe. A new round requires --name, --source and
--description; --resume JOB_ID only waits/registers an existing job, never uploads.
This CLI does not grant upload approval or bypass concrete-source tool review.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "dev"), str(ROOT / "automation")]
from tools.local_judge import make_suite, run_case
from online_judge.browser import connect, load_config
from online_judge.jobs import JobStore, SubmissionLock

DATE = "2026-10-30"
TZ = timezone(timedelta(hours=8))
LIMIT = 30
TARGET = "https://developer.huaweicloud.com/competition/information/1300000312/submission"
AUTHORIZATION = ["先启动初始化等我登录，然后你根据线上结果持续优化30次争取达到第一名", "已登录‘"]
FLAGS = ["-O3", "-Wall", "-Wextra", "-Wpedantic", "-std=c++17"]


def now():
    return datetime.now(TZ).isoformat(timespec="seconds")


def digest(contents):
    return hashlib.sha256(contents).hexdigest()


def read(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def preserve(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != contents:
            raise RuntimeError(f"Refusing to overwrite immutable bytes: {path}")
    else:
        path.write_bytes(contents)


def candidate_review(contents):
    """Conservative static admission check, not a proof of arbitrary C++ safety."""
    text = contents.decode("utf-8-sig", errors="strict")
    forbidden = {
        "network URL": r"https?://",
        "credential marker": r"\b(?:password|passwd|credential|authorization|bearer|api_key|access_token|secret_key|private_key|cookies?)\b",
        "file/network/process/environment API": r"\b(?:fopen|freopen|ifstream|ofstream|fstream|socket|connect|send|recv|curl|system|popen|_popen|exec\w*|spawn\w*|CreateProcess\w*|ShellExecute\w*|CreateFile\w*|ReadFile|WriteFile|WinHttp\w*|InternetOpen\w*|URLDownload\w*|getenv|putenv|GetEnvironmentVariable\w*|RegOpenKey\w*)\s*(?:\(|<|\b)",
        "external I/O include": r"#\s*include\s*[<\"](?:fstream|filesystem|winsock\w*\.h|winhttp\.h|wininet\.h|sys/socket\.h|unistd\.h|process\.h)[>\"]",
        "external preprocessor include": r"#\s*include\s*\"",
    }
    violations = [label for label, pattern in forbidden.items() if re.search(pattern, text, re.I)]
    if violations:
        raise ValueError("Candidate static review rejected: " + ", ".join(violations))
    return dict(passed=True, sha256=digest(contents), checked_at=now(),
                checks=list(forbidden), note="Static screen plus calling-agent review; not a sandbox or universal C++ safety proof.")


def parse_quota(text):
    normalized = text.replace("\u00a0", " ").replace("（", "(").replace("）", ")")
    pattern = r"团队已经上传\s*(\d+)\s*次\s*\(\s*(\d+)\s*/\s*(\d+)\s*\)"
    matches = list(re.finditer(pattern, normalized))
    if len(matches) != 1:
        raise RuntimeError("Cannot identify exactly one team upload quota on the submission page")
    used, numerator, maximum = map(int, matches[0].groups())
    if used != numerator or maximum != LIMIT or not 0 <= used <= maximum:
        raise RuntimeError("Upload quota fields disagree or are outside the authorized 30-round budget")
    return dict(used=used, maximum=maximum, remaining=maximum-used,
                quote=matches[0].group(), captured_at=now(), beijing_date=now()[:10],
                date_basis="Current client/host clock converted to Asia/Shanghai; quota page has no calendar date field.")


def attempt_day(job):
    stamp = job.get("submission_attempt_at")
    if stamp:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise RuntimeError("Submission attempt timestamp is missing its timezone")
        return parsed.astimezone(TZ).date().isoformat()
    if job.get("state") != "snapshot_ready":
        return (job.get("record") or {}).get("submitted_at", "")[:10]
    return None


class Controller:
    def __init__(self, root=ROOT, config=None):
        self.root = Path(root)
        self.out = self.root / "data/experiments/online_20261030"
        self.state_path = self.out / "state.json"
        self.results_path = self.out / "results.json"
        self.index_path = self.root / "data/versions/online_search/results.json"
        self.manifest_path = self.root / "data/versions/manifest.json"
        self.config = load_config() if config is None else config
        if self.config["submission_url"].rstrip("/") != TARGET:
            raise RuntimeError("Controller is restricted to Huawei competition 1300000312")
        self.store = JobStore(Path(self.config["runs_directory"]))
        self.state = read(self.state_path)
        if self.state is None:
            main = (self.root / "main.cpp").read_bytes()
            records = read(self.index_path, [])
            graded = [r for r in records if type(r.get("score")) is int and r.get("sha256") == digest(main)]
            if not graded:
                raise RuntimeError("main.cpp has no matching confirmed official parent score")
            parent_score = max(r["score"] for r in graded)
            self.state = dict(version=1, date=DATE, maximum_unique_delivered_sources=LIMIT,
                              authorization_verbatim=AUTHORIZATION, destination=TARGET,
                              approval_note="Concrete-source upload approval is still required by the calling tool; this helper cannot bypass it.",
                              initial_best_score=parent_score, initial_best_sha256=digest(main),
                              best_score=parent_score, best_sha256=digest(main), rounds=[], created_at=now())
            preserve(self.out / "initial_best.cpp", main)
            preserve(self.out / "best.cpp", main)
            self.persist()
        if self.state.get("date") != DATE or self.state.get("destination") != TARGET:
            raise RuntimeError("Controller state date/destination mismatch")

    def persist(self):
        self.state["updated_at"] = now()
        save(self.state_path, self.state)

    def jobs(self):
        return [self.store.load(path.parent.name) for path in self.store.root.glob("*/job.json")]

    def delivered(self):
        jobs = [job for job in self.jobs() if attempt_day(job) == DATE]
        hashes = {job["sha256"] for job in jobs}
        hashes.update(r["sha256"] for r in self.state["rounds"] if r.get("submit_started_at", "")[:10] == DATE)
        return jobs, hashes

    def new_metadata(self, name, contents, description, source, imported=False):
        sha = digest(contents)
        directory = self.out / "rounds" / f"{name}_{sha[:12]}"
        preserve(directory / "main.cpp", contents)
        parent = (self.out / "best.cpp").read_bytes()
        if digest(parent) != self.state["best_sha256"]:
            raise RuntimeError("Saved best.cpp does not match controller state")
        preserve(directory / "parent.cpp", parent)
        entry = dict(name=name, description=description, sha256=sha,
                     source_path=str(source), snapshot_path=str(directory / "main.cpp"),
                     parent_sha256=digest(parent), parent_score=self.state["best_score"],
                     created_at=now(), state="imported" if imported else "prepared",
                     imported_existing_job=imported, parent_reconstructed_on_resume=imported,
                     authorization_verbatim=AUTHORIZATION, destination=TARGET)
        self.state["rounds"].append(entry)
        self.persist()
        return entry

    def preflight(self, entry):
        source = Path(entry["snapshot_path"])
        review = candidate_review(source.read_bytes())
        directory = source.parent
        compiler = self.root / "dev/toolchains/w64devkit/bin/g++.exe"
        exe = directory / "candidate.exe"
        print(f"compile {entry['name']} sha256={entry['sha256']}", flush=True)
        command = [str(compiler), *FLAGS, str(source), "-o", str(exe)]
        result = subprocess.run(command, cwd=self.root, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=120)
        (directory / "compile.stdout.txt").write_text(result.stdout, encoding="utf-8")
        (directory / "compile.stderr.txt").write_text(result.stderr, encoding="utf-8")
        if result.returncode or result.stderr.strip():
            raise RuntimeError("Compilation failed or emitted warnings; inspect the frozen compile logs")
        rows = []
        for case in make_suite("smoke", 2026):
            row = run_case([str(exe)], case)
            path = row["query_positions"]
            winner = min(set(path), key=lambda x: (-case.values[x], abs(2*x-(len(case.values)-1)), x)) if path else None
            row["parked_observed_winner"] = bool(path) and row["final_position"] == winner
            rows.append(row)
        save(directory / "smoke.json", dict(official=False, sha256=entry["sha256"], rows=rows))
        if len(rows) != 26 or any(row["status"] != "ok" or row["queries"] > 199
                                or row["oscillations"] > 6 or not row["parked_observed_winner"] for row in rows):
            raise RuntimeError("26-case preflight protocol/query/turn/parking check failed")
        entry["preflight"] = dict(passed=True, cases=26, zero_scores=sum(r["score"] == 0 for r in rows),
                                   compiler_sha256=digest(compiler.read_bytes()), executable_sha256=digest(exe.read_bytes()),
                                   static_review=review, completed_at=now())
        self.persist()
        print(f"preflight 26/26 protocol/budget/parking passed; synthetic zeros={entry['preflight']['zero_scores']}", flush=True)

    def quota_check(self):
        if now()[:10] != DATE:
            raise RuntimeError(f"New uploads are authorized only on Beijing date {DATE}; resume remains available")
        delivered, hashes = self.delivered()
        if len(hashes) >= LIMIT or len(delivered) >= LIMIT:
            raise RuntimeError("The local 30-source/attempt day budget is exhausted, including failed/uncertain jobs")
        with connect(self.config) as page:
            records = page.records(refresh=True)
            if any(row.status == "pending" for row in records):
                raise RuntimeError("A submission is pending; resume it before a new upload")
            quota = parse_quota(page.page.locator("body").inner_text())
        if quota["used"] >= LIMIT or now()[:10] != DATE:
            raise RuntimeError("Platform quota exhausted or Beijing authorization date changed")
        quota["local_unique_delivered_sources"] = len(hashes)
        quota["local_attempt_jobs"] = len(delivered)
        if quota["used"] < len(delivered):
            raise RuntimeError("Platform quota is stale relative to today's saved jobs; refresh/reconcile before upload")
        self.state["last_quota"] = quota
        self.persist()
        print(f"quota {quota['used']}/{LIMIT}, local unique sources={len(hashes)}, date={DATE}", flush=True)
        return quota

    def judge(self, args, entry, timeout):
        command = [sys.executable, "-X", "utf8", str(self.root / "automation/online_judge/judge.py"), *args]
        started = time.monotonic()
        try:
            result = subprocess.run(command, cwd=self.root, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", timeout=timeout)
            stdout, stderr, code = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            code = None
        kind = "submit" if args[0] == "submit" else f"wait_{entry.get('wait_windows', 0):04d}"
        directory = Path(entry["snapshot_path"]).parent
        (directory / (kind + ".stdout.txt")).write_text(stdout, encoding="utf-8")
        (directory / (kind + ".stderr.txt")).write_text(stderr, encoding="utf-8")
        payload = None
        try:
            payload = json.loads(stdout)
        except (TypeError, json.JSONDecodeError):
            pass
        print(f"{kind}: exit={code}, elapsed={time.monotonic()-started:.1f}s, job={entry.get('job_id', '(discovering)')}", flush=True)
        return payload, code

    def attach(self, entry, job):
        self.store.validate_snapshot(job)
        if job["sha256"] != entry["sha256"]:
            raise RuntimeError("Job/source SHA mismatch")
        entry.update(job_id=job["job_id"], state=job["state"])
        self.persist()

    def start(self, name, source, description):
        source = Path(source)
        source = (self.root / source).resolve() if not source.is_absolute() else source.resolve()
        if not source.is_relative_to(self.root) or source.suffix.lower() != ".cpp":
            raise ValueError("Source must be a .cpp file within this workspace")
        contents = source.read_bytes()
        candidate_review(contents)
        sha = digest(contents)
        previous = [r for r in self.state["rounds"] if r["sha256"] == sha]
        if previous:
            entry = previous[-1]
            if entry.get("job_id"):
                return self.wait(entry)
            raise RuntimeError("This source already has a prepared/uncertain round; inspect state/jobs, never blindly upload twice")
        if any(r["state"] not in {"completed", "failed"} for r in self.state["rounds"]):
            raise RuntimeError("Another controller round is unresolved; use --resume JOB_ID")
        active = [job for job in self.jobs() if job.get("state") not in {"completed", "failed", "snapshot_ready"}]
        if active:
            raise RuntimeError("Existing unfinished job(s): " + ", ".join(j["job_id"] for j in active) + "; use --resume")
        entry = self.new_metadata(name, contents, description, source)
        old = [job for job in self.jobs() if job["sha256"] == sha and job.get("state") in {"completed", "failed"}]
        if old:
            entry["reused_existing_job"] = True
            self.attach(entry, sorted(old, key=lambda j: j.get("created_at", ""))[-1])
            return self.wait(entry)
        try:
            self.preflight(entry)
            entry["quota_before"] = self.quota_check()
        except Exception as exc:
            entry.update(state="preflight_failed", last_error=f"{type(exc).__name__}: {exc}")
            self.persist()
            raise
        # Persist BEFORE the sole submit invocation. A crash from here onward
        # never authorizes a second invocation for these bytes.
        if now()[:10] != DATE:
            raise RuntimeError("Beijing date changed before upload")
        entry.update(state="submission_started", submit_started_at=now())
        self.persist()
        print(f"ONE upload invocation to {TARGET}; frozen SHA256={sha}", flush=True)
        payload, _ = self.judge(["submit", "--file", entry["snapshot_path"], "--no-wait"], entry, 120)
        job_id = payload.get("job_id") if isinstance(payload, dict) else None
        candidates = [job for job in self.jobs() if job["sha256"] == sha and job.get("state") != "snapshot_ready"]
        if job_id:
            job = self.store.load(job_id)
        elif len(candidates) == 1:
            job = candidates[0]
        else:
            entry.update(state="submission_unknown", last_error="No unique saved job discovered; inspect judge logs/jobs. No second upload is permitted.")
            self.persist()
            raise RuntimeError(entry["last_error"])
        self.attach(entry, job)
        return self.wait(entry)

    def resume(self, job_id):
        job = self.store.load(job_id)
        self.store.validate_snapshot(job)
        found = [r for r in self.state["rounds"] if r.get("job_id") == job_id]
        if found:
            entry = found[0]
        else:
            contents = Path(job["snapshot_path"]).read_bytes()
            name = re.sub(r"[^A-Za-z0-9_-]", "_", Path(job.get("source_path", "resume")).stem)[:64] or "resume"
            entry = self.new_metadata(name, contents, "Import existing job; wait/register only, no upload", job.get("source_path"), True)
            self.attach(entry, job)
        return self.wait(entry)

    def wait(self, entry):
        job_id = entry["job_id"]
        while True:
            job = self.store.load(job_id)
            self.store.validate_snapshot(job)
            if job["sha256"] != entry["sha256"]:
                raise RuntimeError("Waiting job SHA changed")
            entry["state"] = job["state"]
            self.persist()
            if job["state"] in {"completed", "failed"}:
                return self.finish(entry, job)
            if job["state"] in {"ambiguous", "snapshot_ready"}:
                raise RuntimeError(f"Job {job_id} requires manual identity/delivery review ({job['state']}); it will not be uploaded again")
            started = time.monotonic()
            entry["wait_windows"] = entry.get("wait_windows", 0) + 1
            self.persist()
            self.judge(["wait", job_id, "--timeout", "55", "--interval", "5"], entry, 85)
            job = self.store.load(job_id)
            print(f"same job {job_id}: {job['state']}; score={job.get('score')}; never re-upload", flush=True)
            if job["state"] not in {"completed", "failed", "ambiguous", "snapshot_ready"}:
                time.sleep(max(0, 55-(time.monotonic()-started)))

    def finish(self, entry, job):
        contents = Path(job["snapshot_path"]).read_bytes()
        if digest(contents) != entry["sha256"]:
            raise RuntimeError("Completed source bytes differ from frozen round")
        score = job.get("score")
        if job["state"] == "completed" and type(score) is not int:
            raise RuntimeError("Completed job is missing a numeric confirmed score")
        improved = job["state"] == "completed" and score > entry["parent_score"] and score > self.state["best_score"]
        record = job.get("record") or {}
        entry.update(state=job["state"], score=score, submission_id=job.get("bound_submission_id") or record.get("submission_id"),
                     submitted_at=record.get("submitted_at"), finished_at=job.get("finished_at") or now(),
                     delta=None if score is None else score-entry["parent_score"], accepted=improved)
        if job["state"] == "completed":
            archive = self.root / "data/versions/online_search" / f"scored_{score}_{entry['sha256'][:12]}.cpp"
            preserve(archive, contents)
            relative = archive.relative_to(self.root).as_posix()
            entry["archive"] = relative
            indexed = dict(job_id=job["job_id"], name=entry["name"], description=entry["description"],
                           score=score, sha256=entry["sha256"], submission_id=entry["submission_id"],
                           submitted_at=entry["submitted_at"], source_path=relative,
                           parent_sha256=entry["parent_sha256"], parent_score=entry["parent_score"],
                           destination=TARGET)
            records = read(self.index_path, [])
            matching = [r for r in records if r.get("job_id") == job["job_id"]]
            if matching and any(r.get("sha256") != entry["sha256"] or r.get("score") != score for r in matching):
                raise RuntimeError("Existing score index disagrees with the completed job")
            if not matching:
                records.append(indexed)
                save(self.index_path, records)
            manifest = read(self.manifest_path)
            paths = [item for item in manifest["files"] if item["path"] == relative]
            if paths and any(item["sha256"] != entry["sha256"] or item.get("score") != score for item in paths):
                raise RuntimeError("Existing archive manifest disagrees with source/score")
            if not paths:
                manifest["files"].append(dict(path=relative, score=score, sha256=entry["sha256"], job_id=job["job_id"]))
            manifest["recorded_at"] = now()[:10]
            manifest["recorded_best_score"] = max(manifest.get("recorded_best_score", 0), score)
            if improved:
                main = self.root / "main.cpp"
                if digest(main.read_bytes()) not in {self.state["best_sha256"], entry["sha256"]}:
                    raise RuntimeError("main.cpp was changed externally; reconcile before replacing the best")
                canonical = self.root / "data/versions" / f"main_online_{score}.cpp"
                preserve(canonical, contents)
                canonical_rel = canonical.relative_to(self.root).as_posix()
                if not any(item["path"] == canonical_rel for item in manifest["files"]):
                    manifest["files"].append(dict(path=canonical_rel, score=score, sha256=entry["sha256"], job_id=job["job_id"]))
                main.write_bytes(contents)
                (self.out / "best.cpp").write_bytes(contents)
                self.state.update(best_score=score, best_sha256=entry["sha256"], best_job_id=job["job_id"])
            save(self.manifest_path, manifest)
        results = read(self.results_path, [])
        prior = next((r for r in results if r.get("job_id") == job["job_id"]), None)
        if prior is None:
            results.append(dict(entry))
        else:
            # Preserve prior acceptance on an idempotent resume after main was
            # already promoted; ties and lower scores never replace the best.
            accepted = prior.get("accepted", False)
            prior.update(entry)
            prior["accepted"] = accepted or improved
            entry["accepted"] = prior["accepted"]
        save(self.results_path, results)
        self.persist()
        jobs, hashes = self.delivered()
        self.state["delivered_unique_hashes"] = sorted(hashes)
        self.state["delivered_attempt_jobs"] = len(jobs)
        self.persist()
        print(json.dumps(dict(job_id=job["job_id"], state=job["state"], score=score,
                              delta=entry["delta"], accepted=entry["accepted"], best_score=self.state["best_score"],
                              delivered_unique_sources=len(hashes), maximum=LIMIT), ensure_ascii=False), flush=True)
        return 0 if job["state"] == "completed" else 3


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--description")
    parser.add_argument("--resume", metavar="JOB_ID")
    args = parser.parse_args(argv)
    if args.resume:
        if args.name or args.source or args.description:
            parser.error("--resume is exclusive; it only waits/registers the given existing job")
    elif not all((args.name, args.source, args.description)):
        parser.error("a new single round requires --name, --source and --description")
    elif not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,79}", args.name):
        parser.error("--name must be a safe identifier of at most 80 characters")
    try:
        out = ROOT / "data/experiments/online_20261030"
        with SubmissionLock(out / ".round.lock"):
            controller = Controller()
            return controller.resume(args.resume) if args.resume else controller.start(args.name, args.source, args.description)
    except KeyboardInterrupt:
        print("Interrupted. Resume the saved JOB_ID; never re-upload these bytes.", file=sys.stderr, flush=True)
        return 130
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
