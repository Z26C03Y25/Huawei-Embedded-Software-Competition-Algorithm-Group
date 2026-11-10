"""Confirm one frozen classic-study candidate on fresh V4 mixed curves.

  python/runtime/python.exe dev/tools/confirm_stoploss_mixed.py \
    --study dev/build/stoploss_20261029 --candidate all_suffix --per-family 18

Requires completed development, selection and blind_shift classic phases. A
single candidate is fixed before generating any mixed results. Uses the frozen
executables without compilation. The independent confirmation uses seed tag
20261029401 and includes all four novel families. No networking or submission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev"))
from tools import mixed_scenarios
from tools.local_judge import run_case
from tools.stoploss_study import encoded, project_path, save, sha, summarize
from tools.summarize_stoploss import main as summarize_complete

SEED_TAG = 20261029401


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--study", required=True)
    parser.add_argument("--candidate", required=True, help="one candidate name already frozen in the classic study")
    parser.add_argument("--per-family", type=int, default=18)
    parser.add_argument("--limit", type=int, help="small per-phase case limit to verify the confirmation tool itself")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args(argv)
    if args.per_family < 1 or (args.limit is not None and args.limit < 1) or not 0 < args.timeout <= 10:
        parser.error("positive counts and timeout in (0,10] are required")
    study = project_path(args.study)
    classic = read(study / "manifest.json")
    if args.candidate == "baseline" or args.candidate not in classic["sources"]:
        parser.error("--candidate must select one non-baseline frozen source")
    for split in mixed_scenarios.SEEDS:
        completion = study / split / "completion.json"
        if not completion.exists() or not read(completion).get("complete"):
            raise RuntimeError("All classic phases must complete before choosing the unique mixed-confirmation candidate")
    names = ["baseline", args.candidate]
    executables = {}
    for name in names:
        exe = study / "bin" / (name + ".exe")
        stamp = read(exe.with_suffix(".build.json"))
        if stamp["executable_sha256"] != sha(exe) or stamp["source_sha256"] != classic["sources"][name]["sha256"]:
            raise RuntimeError("Frozen executable/source identity changed")
        if sha(study / "sources" / (name + ".cpp")) != stamp["source_sha256"]:
            raise RuntimeError("Frozen source changed")
        executables[name] = exe
    out = study / "mixed_confirmation"
    main_hash = sha(ROOT / "main.cpp")
    manifest = dict(
        official=False, suite="mixed", generator_version=mixed_scenarios.VERSION,
        generator_sha256=sha(ROOT / "dev/tools/mixed_scenarios.py"),
        judge_sha256=sha(ROOT / "dev/tools/local_judge.py"), tool_sha256=sha(Path(__file__)),
        parent_manifest_sha256=sha(study / "manifest.json"), selected_candidate=args.candidate,
        seed_tag=SEED_TAG, novel=True, seeds=mixed_scenarios.SEEDS,
        per_family=args.per_family, limit=args.limit, timeout=args.timeout,
        sources={name: classic["sources"][name] for name in names},
        executable_sha256={name: sha(exe) for name, exe in executables.items()},
        notes=["Exactly one candidate fixed before any fresh confirmation result.",
               "All V4 families plus four novel families; no solver-dependent rejection sampling.",
               "Synthetic stress test; not an estimate of official performance."],
    )
    manifest_file = out / "manifest.json"
    if manifest_file.exists() and read(manifest_file) != manifest:
        raise RuntimeError("The unique mixed candidate or frozen confirmation inputs changed")
    save(manifest_file, manifest)
    had_hard_failure = False
    for split in mixed_scenarios.SEEDS:
        generated = mixed_scenarios.make_scenarios(args.per_family, [split], seed_tag=SEED_TAG, novel=True)
        if args.limit:
            generated = generated[:args.limit]
        cases = [dict(name=c.name, N=len(c.values), family=c.family, difficulty=c.difficulty,
                      values=list(c.values), metadata=m) for c, m in generated]
        dataset_hash = hashlib.sha256(encoded(cases)).hexdigest()
        phase = out / split
        case_payload = dict(dataset_sha256=dataset_hash, cases=cases)
        case_file = phase / "cases.json"
        if case_file.exists() and read(case_file) != case_payload:
            raise RuntimeError("Frozen confirmation dataset changed")
        save(case_file, case_payload)
        baseline = None
        summaries = {}
        for name, exe in executables.items():
            report_file = phase / (name + ".json")
            context = dict(dataset_sha256=dataset_hash, source_sha256=manifest["sources"][name]["sha256"],
                           executable_sha256=manifest["executable_sha256"][name], judge_sha256=manifest["judge_sha256"])
            report = read(report_file) if report_file.exists() else dict(**context, rows=[])
            if {key: report.get(key) for key in context} != context:
                raise RuntimeError("Cached confirmation result context changed")
            rows = report["rows"]
            if len(rows) > len(cases) or [r["name"] for r in rows] != [c["name"] for c in cases[:len(rows)]]:
                raise RuntimeError("Cached confirmation order changed")
            for i in range(len(rows), len(generated)):
                case, _ = generated[i]
                row = run_case([str(exe)], case, timeout=args.timeout)
                path = row["query_positions"]
                winner = min(set(path), key=lambda x: (-case.values[x], abs(2*x-(len(case.values)-1)), x)) if path else None
                row["parked_observed_winner"] = bool(path) and row["final_position"] == winner
                rows.append(row)
                if (i + 1) % 32 == 0:
                    save(report_file, report)
                if (i + 1) % 200 == 0:
                    print(f"mixed {split} {name}: {i + 1}/{len(cases)}", flush=True)
            save(report_file, report)
            if baseline is None:
                baseline = rows
            summaries[name] = summarize(rows, baseline, cases)
            save(phase / "counterexamples" / (name + ".json"),
                 [dict(case=c, baseline=b, candidate=r) for c, b, r in zip(cases, baseline, rows)
                  if r["score"] == 0 and b["score"] > 0])
            summary = summaries[name]["base"]
            print(f"mixed {split} {name}: mean={summary.get('mean_score', 0):.2f} "
                  f"delta={summary.get('mean_delta', 0):+.2f} zeros={summary.get('zero_scores', 0)}", flush=True)
            had_hard_failure |= any(summaries[name][group].get("hard_failures", 0)
                                    for group in ("base", "transformed_siblings"))
        save(phase / "summary.json", dict(official=False, split=split, dataset_sha256=dataset_hash, solvers=summaries))
        if sha(ROOT / "main.cpp") != main_hash:
            raise RuntimeError("main.cpp changed during confirmation")
        if any(sha(exe) != manifest["executable_sha256"][name] for name, exe in executables.items()):
            raise RuntimeError("Frozen executable changed during confirmation")
        save(phase / "completion.json", dict(complete=True, cases=len(cases),
             independent_base_cases=sum(c["metadata"]["transform"] == "base" for c in cases),
             solvers=names, main_preserved=True, online_submissions=0))
    summarize_complete(["--out", str(out)])
    return int(had_hard_failure)


if __name__ == "__main__":
    raise SystemExit(main())
