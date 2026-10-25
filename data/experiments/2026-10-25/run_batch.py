"""Offline batch A: M/R ablation and small-edge audit; never uploads."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "dev"))
sys.path.insert(0, str(ROOT / "automation"))
from tools.local_judge import Case, make_suite, run_case
from tools.compare_solvers import make_benchmark
from online_judge.jobs import SubmissionLock

SOURCES = {
    "M1_R12_best": "data/versions/main_online_199291.cpp",
    "M0_R16_scored": "data/versions/online_search/scored_198409_df9d86a0152c.cpp",
    "M0_R12": "data/versions/online_search/day20261025_m0r12.cpp",
    "M1_R16": "data/versions/online_search/day20261025_m1r16.cpp",
    "edge_reverse8": "data/experiments/2026-10-25/edge_reverse8.cpp",
}
REPORT = ROOT / "dev/build/research/2026-10-25_batchA.json"


def save(report):
    temporary = REPORT.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(REPORT)


def cases():
    out = [("smoke", c) for c in make_suite("smoke")]
    # Fixed before evaluating this batch. Do not tune against the holdout here.
    for group, seed in (("development", 314159), ("holdout", 271828)):
        out += [(group, item.case) for item in make_benchmark(seed, 84)]
    # Shift/width/mirror/paired controls test transfer away from the known point.
    for start in (176, 184, 192, 200, 208, 216, 224):
        for width in (97, 145, 201):
            for hidden in (False, True):
                a = [0] * 1000
                a[start:start+width] = [10000] * width
                a[start+min(136, width-8)] = 10090
                a[start+1] = 10100 if hidden else 10000
                for mirrored in (False, True):
                    values = tuple(reversed(a)) if mirrored else tuple(a)
                    name = f"edge_s{start}_w{width}_hidden{int(hidden)}_mirror{int(mirrored)}"
                    out.append(("edge_variants", Case(name, values, "edge_variants", "challenging")))
    assert len({c.name for _, c in out}) == len(out)
    return out


def summary(rows):
    return {"cases": len(rows), "total_score": sum(x["score"] for x in rows),
            "zero_scores": sum(x["score"] == 0 for x in rows),
            "queries": sum(x["queries"] for x in rows),
            "movement": sum(x["travel"] for x in rows),
            "max_queries": max((x["queries"] for x in rows), default=0),
            "max_turns": max((x["oscillations"] for x in rows), default=0),
            "protocol_errors": sum(x["status"] != "ok" for x in rows)}


def main():
    dataset = cases()
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    hashes = {name: digest(ROOT / source) for name, source in SOURCES.items()}
    main_hash = digest(ROOT / "main.cpp")
    identities = [{"set": group, "name": c.name, "values": c.values,
                   "family": c.family, "difficulty": c.difficulty} for group, c in dataset]
    fingerprint = hashlib.sha256(json.dumps({"sources": hashes, "cases": identities},
                                           sort_keys=True).encode()).hexdigest()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with SubmissionLock(ROOT / "automation/online_judge/runs/.offline-research.lock"):
        if REPORT.exists():
            report = json.loads(REPORT.read_text(encoding="utf-8"))
            if report["input_fingerprint"] != fingerprint:
                raise RuntimeError("Batch inputs changed; use a new report, never overwrite evidence")
        else:
            report = {"batch": "2026-10-25_A", "official_scores": False,
                      "input_fingerprint": fingerprint, "sources": SOURCES,
                      "source_sha256": hashes, "main_sha256_before": main_hash,
                      "cases": identities, "results": {}}
            save(report)
        for name, source in SOURCES.items():
            exe = REPORT.parent / (name + (".exe" if os.name == "nt" else ""))
            compile_result = subprocess.run(["g++", "-O3", "-Wall", "-Wextra", "-Wpedantic",
                "-std=c++17", str(ROOT/source), "-o", str(exe)], capture_output=True, text=True)
            if compile_result.returncode or compile_result.stderr:
                raise RuntimeError("Compilation failed/warned: " + compile_result.stderr)
            rows = report["results"].setdefault(name, [])
            for group, case in dataset[len(rows):]:
                result = run_case([str(exe)], case)
                expected = min(set(result["query_positions"]),
                    key=lambda i: (-case.values[i], abs(2*i-(len(case.values)-1)), i)) if result["query_positions"] else None
                legal = result["status"] == "ok" and result["queries"] <= 199 and result["oscillations"] <= 6
                legal = legal and result["final_position"] == expected
                rows.append({"set": group, **result, "observed_winner_ok": result["final_position"] == expected})
                if len(rows) % 10 == 0 or not legal:
                    save(report)
                if not legal:
                    raise RuntimeError("Protocol/action/parking regression in " + name + ":" + case.name)
            save(report)
            print(json.dumps({"solver": name, **summary(rows)}), flush=True)
        report["summaries"] = {}
        baseline = report["results"]["M1_R12_best"]
        for name, rows in report["results"].items():
            report["summaries"][name] = {}
            for group in ("smoke", "development", "holdout", "edge_variants"):
                selected = [x for x in rows if x["set"] == group]
                prior = [x for x in baseline if x["set"] == group]
                report["summaries"][name][group] = summary(selected) | {
                    "delta_vs_best": sum(x["score"]-y["score"] for x,y in zip(selected,prior)),
                    "resolved_zero": sum(y["score"]==0 and x["score"]>0 for x,y in zip(selected,prior)),
                    "new_zero": sum(y["score"]>0 and x["score"]==0 for x,y in zip(selected,prior))}
        assert digest(ROOT / "main.cpp") == main_hash
        report["complete"] = True
        report["main_unchanged"] = True
        save(report)
        print(json.dumps(report["summaries"], ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()
