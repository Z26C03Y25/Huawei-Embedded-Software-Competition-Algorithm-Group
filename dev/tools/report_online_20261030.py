"""Generate a sanitized local snapshot of the 2026-10-30 official rounds.

  python/runtime/python.exe dev/tools/report_online_20261030.py

Reads local state/results/jobs only. Writes just the day's README.md and
summary.json; never contacts the browser, submits, polls, or changes solver,
state, results, archive index or manifest files. Saved leaderboard references
are explicitly dated, and are not presented as a fresh leaderboard reading.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/experiments/online_20261030"
DATE = "2026-10-30"
TZ = timezone(timedelta(hours=8))


def read(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def public_source(raw, root=ROOT):
    if not isinstance(raw, str):
        return None
    path = Path(raw)
    path = (root / path).resolve() if not path.is_absolute() else path.resolve()
    if not path.is_relative_to(root) or path.suffix.lower() != ".cpp":
        return None
    relative = path.relative_to(root).as_posix()
    return relative if relative == "main.cpp" or relative.startswith("data/") else None


def safe_name(raw):
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(raw))[:100]


def official_score(job):
    score = job.get("score")
    return score if job.get("state") == "completed" and type(score) is int else None


def attempt_day(job):
    stamp = job.get("submission_attempt_at")
    if stamp:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(TZ).date().isoformat()
    if job.get("state") != "snapshot_ready":
        return (job.get("record") or {}).get("submitted_at", "")[:10]
    return None


def timestamp(raw):
    try:
        value = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return value.timestamp() if value.tzinfo else value.replace(tzinfo=TZ).timestamp()
    except (ValueError, TypeError):
        return 0


def load_inputs(root=ROOT):
    out = root / "data/experiments/online_20261030"
    config_base = root / "automation/online_judge"
    config = read(config_base / "config.json", {})
    runs = (config_base / config.get("runs_directory", "runs")).resolve()
    if not runs.is_relative_to(config_base) or runs == config_base:
        raise RuntimeError("Configured jobs directory is outside the dedicated online_judge directory")
    # Atomic writers can advance while a report runs. Retry if the controller
    # state/results change during collection, without taking its submission lock.
    for _ in range(3):
        before = (sha(out / "state.json"), sha(out / "results.json"))
        state = read(out / "state.json")
        if state is None:
            raise RuntimeError("The day's controller state.json does not exist")
        results = read(out / "results.json", [])
        jobs = {}
        for path in sorted(runs.glob("*/job.json")):
            job = read(path)
            if isinstance(job, dict) and job.get("job_id") == path.parent.name:
                jobs[job["job_id"]] = job
        after = (sha(out / "state.json"), sha(out / "results.json"))
        if before == after:
            return state, results, jobs, dict(state_sha256=after[0], results_sha256=after[1],
                                            collection_state_stable=True)
    return state, results, jobs, dict(state_sha256=after[0], results_sha256=after[1],
                                    collection_state_stable=False)


def build_report(state, results, jobs, root=ROOT):
    if state.get("date") != DATE:
        raise RuntimeError("Unexpected controller date")
    entries = list(state.get("rounds", []))
    identities = {(e.get("job_id"), e.get("sha256"), e.get("name")) for e in entries}
    for entry in results:
        identity = (entry.get("job_id"), entry.get("sha256"), entry.get("name"))
        if identity not in identities:
            entries.append(entry)
            identities.add(identity)
    day_jobs = {key: job for key, job in jobs.items() if attempt_day(job) == DATE}
    represented = {entry.get("job_id") for entry in entries}
    for key, job in day_jobs.items():
        if key not in represented:
            entries.append(dict(job_id=key, name=Path(job.get("source_path", "unregistered")).stem,
                                sha256=job.get("sha256"), source_path=job.get("source_path"),
                                state="unregistered_job", imported_existing_job=True))
    rows = []
    for number, entry in enumerate(entries, 1):
        job = jobs.get(entry.get("job_id"), {})
        valid_identity = bool(job) and job.get("sha256") == entry.get("sha256")
        score = official_score(job) if valid_identity else None
        parent = entry.get("parent_score")
        parent = parent if type(parent) is int else None
        live_state = job.get("state", "missing_job") if valid_identity else "unverified_job_identity"
        if not entry.get("job_id"):
            live_state = entry.get("state", "prepared")
        preflight = entry.get("preflight") or {}
        source = public_source(entry.get("archive"), root) or public_source(entry.get("source_path"), root)
        source_sha = entry.get("sha256")
        source_valid = bool(source) and sha(root / source) == source_sha
        manual = root / "dev/build" / f"online_{safe_name(entry.get('name', 'unknown'))}_smoke.json"
        manual_rows = read(manual) if entry.get("imported_existing_job") and manual.is_file() else None
        manual_evidence = None
        if isinstance(manual_rows, list):
            manual_evidence = dict(path=manual.relative_to(root).as_posix(), cases=len(manual_rows),
                                   note="Separate manually run smoke report; no source SHA binding in this JSON. Not counted as controller preflight.")
        rows.append(dict(
            round=number, name=safe_name(entry.get("name", "unregistered")),
            parent_score=parent, official_score=score, delta=score-parent if score is not None and parent is not None else None,
            accepted=bool(entry.get("accepted")) and score is not None,
            status=live_state, controller_status=entry.get("state"),
            official_confirmation="completed job with matching source SHA" if score is not None else "not yet confirmed",
            submission_id=job.get("bound_submission_id") or (job.get("record") or {}).get("submission_id") or entry.get("submission_id"),
            submitted_at=(job.get("record") or {}).get("submitted_at") or entry.get("submitted_at"),
            source_path=source, sha256=source_sha, source_bytes_verified=source_valid,
            parent_sha256=entry.get("parent_sha256"),
            parent_reconstructed_on_resume=bool(entry.get("parent_reconstructed_on_resume")),
            awaiting_controller_registration=score is not None and entry.get("score") != score,
            preflight=dict(passed=preflight.get("passed") is True,
                           cases=preflight.get("cases", 0), synthetic_zero_scores=preflight.get("zero_scores"),
                           static_review_passed=(preflight.get("static_review") or {}).get("passed") is True,
                           completed_at=preflight.get("completed_at")),
            manual_smoke_evidence=manual_evidence,
        ))
    best_score = state.get("best_score")
    snapshots = []
    for job in jobs.values():
        saved = job.get("ranking_after")
        if not isinstance(saved, dict) or type((saved.get("leader") or {}).get("score")) is not int:
            continue
        snapshots.append(dict(leader_score=saved["leader"]["score"], captured_at=saved.get("captured_at"),
                              refreshed_at=saved.get("refreshed_at"), scope=saved.get("scope", "unknown")))
    ranking = max(snapshots, key=lambda s: timestamp(s["captured_at"]), default=None)
    if ranking:
        ranking["gap_from_registered_best"] = ranking["leader_score"]-best_score if type(best_score) is int else None
        ranking["note"] = "Existing saved ranking_after only; no leaderboard request was made. This is not a live rank or current first-place guarantee."
    delivered_hashes = {job["sha256"] for job in day_jobs.values() if job.get("sha256")}
    maximum = state.get("maximum_unique_delivered_sources", 30)
    latest_quota = state.get("last_quota") or {}
    quota = {key: latest_quota.get(key) for key in ("used", "maximum", "remaining", "captured_at", "beijing_date")}
    quota["note"] = "Saved pre-upload page reading; later attempts may already have consumed more quota."
    preflight_rows = [row for row in rows if row["preflight"]["passed"]]
    positive_scores = [row["official_score"] for row in rows if row["official_score"] is not None]
    return dict(
        date=DATE, generated_at=datetime.now(TZ).isoformat(timespec="seconds"),
        mode="Local read-only snapshot; only README.md and summary.json are written",
        new_uploads_stopped=(root / "data/experiments/online_20261030/stop_after_current").exists(),
        initial_best=dict(score=state.get("initial_best_score"), sha256=state.get("initial_best_sha256")),
        current_best=dict(score=best_score, sha256=state.get("best_sha256"), source_path="main.cpp",
                          main_bytes_match_state=sha(root / "main.cpp") == state.get("best_sha256")),
        maximum_confirmed_score_in_snapshot=max(positive_scores + [best_score]) if type(best_score) is int else max(positive_scores, default=None),
        budget=dict(actual_attempt_jobs=len(day_jobs), unique_delivered_sources=len(delivered_hashes),
                    duplicate_source_attempt_jobs=len(day_jobs)-len(delivered_hashes), maximum=maximum,
                    remaining_by_local_attempt_jobs=max(0, maximum-len(day_jobs)),
                    remaining_by_local_unique_sources=max(0, maximum-len(delivered_hashes)),
                    job_states=dict(Counter(job.get("state", "unknown") for job in day_jobs.values())),
                    saved_page_quota=quota,
                    note="Includes failed, pending and delivery-uncertain jobs with a dated submission attempt. Preparation-only snapshots are not counted."),
        statistics=dict(rounds=len(rows), confirmed_numeric_scores=len(positive_scores),
                        pending_or_unconfirmed=sum(row["official_score"] is None and row["status"] != "failed" for row in rows),
                        failed=sum(row["status"] == "failed" for row in rows),
                        accepted=sum(row["accepted"] for row in rows),
                        controller_compile_and_smoke_passed_rounds=len(preflight_rows),
                        controller_smoke_cases=sum(row["preflight"]["cases"] for row in preflight_rows),
                        controller_synthetic_zeros=sum(row["preflight"]["synthetic_zero_scores"] or 0 for row in preflight_rows),
                        static_review_passed_rounds=sum(row["preflight"]["static_review_passed"] for row in rows),
                        separate_manual_smoke_rounds=sum(row["manual_smoke_evidence"] is not None for row in rows)),
        saved_leaderboard_reference=ranking, rounds=rows,
        notes=["Official scores come only from matching completed job records; pending/unknown jobs have no official score.",
               "A tie keeps the previous best. Accepted is the controller's actual promotion flag, not an inferred win.",
               "The first two imported rounds have separate manual smoke evidence under dev/build; controller preflight metadata is absent.",
               "Synthetic zero counts are diagnostic, and do not invalidate official results.",
               "No browser profiles, credentials, raw config, job diagnostics or absolute local paths are exported."],
    )


def markdown(report, root=ROOT):
    best, initial, budget, stats = (report[key] for key in ("current_best", "initial_best", "budget", "statistics"))
    lines = ["# 2026-10-30 线上逐轮优化", "", f"本地快照：{report['generated_at']}。只读现有记录，本报告不联网、不提交。", "",
             f"初始最高分 **{initial['score']}**，当前采用最高分 **{best['score']}**，"
             f"变化 **{best['score']-initial['score']:+}**。main.cpp 与保存的最高分 SHA "
             f"{'一致' if best['main_bytes_match_state'] else '不一致，需人工核查'}。", "",
             f"当日实际投递尝试 **{budget['actual_attempt_jobs']}/{budget['maximum']}**，"
             f"唯一已投递源码 **{budget['unique_delivered_sources']}**，重复源码尝试 {budget['duplicate_source_attempt_jobs']} 次；"
             f"按本地实际尝试计剩余 {budget['remaining_by_local_attempt_jobs']} 次。失败及待判分均计入。", ""]
    if report.get("new_uploads_stopped"):
        lines.extend(["已按用户最新要求停止后续上传，转入[多维特征分析与算法设计](../../../docs/research/README.md)。剩余次数没有继续使用。", ""])
    ranking = report["saved_leaderboard_reference"]
    if ranking:
        lines.extend([f"已有榜单参考：榜首 **{ranking['leader_score']}**，当前采用版本差 **{ranking['gap_from_registered_best']}**。"
                      f"采集时间 {ranking['captured_at']}，榜单自身刷新时间 {ranking['refreshed_at']}，范围 {ranking['scope']}。"
                      "该缓存不是实时榜单，本次未请求榜单。", ""])
    else:
        lines.extend(["本地没有可用的已有榜单参考；未新增榜单请求。", ""])
    lines.extend(["## 逐轮正式结果", "", "| 轮 | 名称 | 父分数 | 正式分数 | 相对父版本 | 采用 | 本地 job 状态 |",
                  "| ---: | --- | ---: | ---: | ---: | --- | --- |"])
    for row in report["rounds"]:
        score = row["official_score"]
        value = str(score) if score is not None else ("失败" if row["status"] == "failed" else "待确认")
        delta = f"{row['delta']:+}" if row["delta"] is not None else "—"
        lines.append(f"| {row['round']} | {row['name']} | {row['parent_score'] if row['parent_score'] is not None else '未记录'} | "
                     f"{value} | {delta} | {'是' if row['accepted'] else '否'} | {row['status']} |")
    lines.extend(["", "正式分数仅取源码 SHA 匹配且状态 completed 的已有 job。待判分、未知与失败不会被写成零分。平分保留原版。", "",
                  "## 源码与作品标识", "", "| 轮 | 公开赛事源码 | SHA256 | 作品 ID |", "| ---: | --- | --- | --- |"])
    for row in report["rounds"]:
        source = row["source_path"]
        if source:
            target = Path(os.path.relpath(root / source, root / "data/experiments/online_20261030")).as_posix().replace(" ", "%20")
            source = f"[{source}]({target})"
        lines.append(f"| {row['round']} | {source or '暂无可公开源码路径'} | {row['sha256'] or '未记录'} | {row['submission_id'] or '待绑定'} |")
    lines.extend(["", "## 已有检查证据", "",
                  f"控制器记录严格编译及烟测通过 {stats['controller_compile_and_smoke_passed_rounds']} 轮、"
                  f"真实管道烟测 {stats['controller_smoke_cases']} 条，包含 {stats['controller_synthetic_zeros']} 条合成零分；"
                  f"源码静态审查通过 {stats['static_review_passed_rounds']} 轮。合成零分与协议违规分别记录。", "",
                  "最初两轮通过 --resume 导入，缺少控制器 preflight 元数据；另有人工作业的 dev/build 烟测证据，未冒充为控制器自动检查。", ""])
    for row in report["rounds"]:
        evidence = row["manual_smoke_evidence"]
        if evidence:
            lines.append(f"- {row['name']}：{evidence['path']}，{evidence['cases']} 条；该 JSON 不含源码 SHA 绑定。")
    lines.extend(["", "本地报告只更新本目录 README.md 与 summary.json；不修改 main.cpp、状态、正式结果、版本索引或归档哈希。", ""])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    state, results, jobs, evidence = load_inputs()
    report = build_report(state, results, jobs)
    report["evidence"] = evidence
    # Prepare both outputs before replacing either, leaving every input intact.
    OUT.mkdir(parents=True, exist_ok=True)
    for name, content in (("summary.json", json.dumps(report, ensure_ascii=False, indent=2) + "\n"),
                          ("README.md", markdown(report))):
        path = OUT / name
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
    print(json.dumps(dict(rounds=report["statistics"]["rounds"], confirmed=report["statistics"]["confirmed_numeric_scores"],
                          actual_attempt_jobs=report["budget"]["actual_attempt_jobs"],
                          unique_delivered_sources=report["budget"]["unique_delivered_sources"],
                          best=report["current_best"]["score"], output="data/experiments/online_20261030/summary.json"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
