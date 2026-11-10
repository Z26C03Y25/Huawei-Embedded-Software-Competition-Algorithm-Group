"""Frozen, offline paired studies with real query/reply pipes and N-band reports.

Run with the project Python; no PATH changes or third-party packages are needed::

  python/runtime/python.exe dev/tools/stoploss_study.py --out dev/build/stoploss \
    --source candidate=data/experiments/candidate.cpp --per-family 18
  # Keep the same output, sources and count for the next frozen phase:
  python/runtime/python.exe dev/tools/stoploss_study.py --out dev/build/stoploss \
    --source candidate=data/experiments/candidate.cpp --per-family 18 --split selection

The first run freezes all source bytes, compiler, generator and dataset options.
Changed inputs require a new study directory. Run blind_shift only after selection;
do not tune a candidate after inspecting its held-out results. These synthetic
scores do not predict the official 102-case total. No command accesses the network.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev"))
from tools.local_judge import run_case
from tools.scenario_factory import make_scenarios, VERSION, SEEDS

FLAGS = ["-O3", "-Wall", "-Wextra", "-Wpedantic", "-std=c++17"]
BANDS = ("N<=500", "501<=N<=650", "N>650")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def project_path(raw):
    path = Path(raw)
    return (ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def label(path):
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def band(n):
    return BANDS[0] if n <= 500 else BANDS[1] if n <= 650 else BANDS[2]


def statistics(pairs):
    if not pairs:
        return {"cases": 0}
    rows = [row for row, _, _ in pairs]
    baseline = [base for _, base, _ in pairs]
    size = len(rows)
    mean = lambda key: sum(row[key] for row in rows) / size
    baseline_mean = lambda key: sum(row[key] for row in baseline) / size
    families = defaultdict(list)
    for row, base, meta in pairs:
        families[meta["family"]].append(row["score"] - base["score"])
    deltas = [r["score"] - b["score"] for r, b, _ in pairs]
    return dict(
        cases=size,
        mean_score=mean("score"), baseline_mean_score=baseline_mean("score"),
        mean_delta=sum(deltas) / size, total_delta=sum(deltas),
        family_macro_delta=sum(sum(ds) / len(ds) for ds in families.values()) / len(families),
        zero_scores=sum(row["score"] == 0 for row in rows),
        baseline_zero_scores=sum(row["score"] == 0 for row in baseline),
        new_zeros=sum(r["score"] == 0 and b["score"] > 0 for r, b, _ in pairs),
        resolved_zeros=sum(r["score"] > 0 and b["score"] == 0 for r, b, _ in pairs),
        wins=sum(delta > 0 for delta in deltas), losses=sum(delta < 0 for delta in deltas),
        mean_queries=mean("queries"), mean_query_delta=mean("queries") - baseline_mean("queries"),
        mean_travel=mean("travel"), mean_travel_delta=mean("travel") - baseline_mean("travel"),
        hard_failures=sum(not row["parked_observed_winner"] or row["status"] != "ok"
                          or row["queries"] > 199 or row["oscillations"] > 6 for row in rows),
    )


def summarize(rows, baseline, cases):
    pairs = list(zip(rows, baseline, cases))
    base = [p for p in pairs if p[2]["metadata"]["transform"] == "base"]
    # Keep the Case descriptor alongside the row to avoid treating transformed
    # siblings as independent curves in the principal statistics.
    def stats(group):
        return statistics([(r, b, c["metadata"]) for r, b, c in group])
    return dict(
        base=stats(base),
        by_n={name: stats([p for p in base if band(p[2]["N"]) == name]) for name in BANDS},
        structured_base=stats([p for p in base if p[2]["difficulty"] != "information_limited"]),
        information_limited_base=stats([p for p in base if p[2]["difficulty"] == "information_limited"]),
        by_family={family: stats([p for p in base if p[2]["family"] == family])
                   for family in sorted({p[2]["family"] for p in base})},
        transformed_siblings=stats([p for p in pairs if p[2]["metadata"]["transform"] != "base"]),
    )


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True, help="study directory, shared across the three phases")
    parser.add_argument("--baseline", default="main.cpp")
    parser.add_argument("--source", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--compiler", default="dev/toolchains/w64devkit/bin/g++.exe")
    parser.add_argument("--split", choices=tuple(SEEDS), default="development")
    parser.add_argument("--per-family", type=int, default=18)
    parser.add_argument("--limit", type=int, help="limit cases for checking the study tool itself")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args(argv)
    if args.per_family < 1 or (args.limit is not None and args.limit < 1) or not 0 < args.timeout <= 10:
        parser.error("positive counts and timeout in (0,10] are required")
    out = project_path(args.out)
    compiler = project_path(args.compiler)
    sources = {"baseline": project_path(args.baseline)}
    for entry in args.source:
        if "=" not in entry:
            parser.error("--source requires NAME=PATH")
        name, raw_path = entry.split("=", 1)
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", name) or name in sources:
            parser.error("source names must be unique safe identifiers; baseline is reserved")
        sources[name] = project_path(raw_path)
    if not compiler.is_file() or any(not path.is_file() for path in sources.values()):
        parser.error("compiler and all source paths must exist")
    if not args.source:
        parser.error("at least one --source is required")
    generator = ROOT / "dev/tools/scenario_factory.py"
    judge = ROOT / "dev/tools/local_judge.py"
    manifest = dict(
        official=False, generator_version=VERSION, generator_sha256=sha(generator),
        judge_sha256=sha(judge), tool_sha256=sha(Path(__file__)),
        seeds=SEEDS, per_family=args.per_family, limit=args.limit, timeout=args.timeout,
        compiler=dict(path=label(compiler), sha256=sha(compiler)), flags=FLAGS,
        sources={name: dict(path=label(path), sha256=sha(path)) for name, path in sources.items()},
        notes=["Sources frozen before all phases; no tuning on selection/blind_shift.",
               "Principal reports use independent base curves only; siblings reported separately.",
               "Includes zero scores. Synthetic results are not official score predictions."],
    )
    manifest_path = out / "manifest.json"
    if manifest_path.exists():
        if json.loads(manifest_path.read_text(encoding="utf-8")) != manifest:
            raise RuntimeError("Frozen inputs changed; choose a new --out directory")
    else:
        save(manifest_path, manifest)
    split_names = list(SEEDS)
    prior = split_names[:split_names.index(args.split)]
    for earlier in prior:
        if not (out / earlier / "completion.json").exists():
            raise RuntimeError(f"Complete {earlier} before inspecting {args.split}")
    main_hash = sha(ROOT / "main.cpp")
    frozen = out / "sources"
    frozen.mkdir(parents=True, exist_ok=True)
    executables = {}
    for name, path in sources.items():
        source = frozen / (name + ".cpp")
        if not source.exists():
            source.write_bytes(path.read_bytes())
        if sha(source) != manifest["sources"][name]["sha256"]:
            raise RuntimeError("Frozen source copy changed")
        exe = out / "bin" / (name + ".exe")
        exe.parent.mkdir(parents=True, exist_ok=True)
        stamp = exe.with_suffix(".build.json")
        build_id = dict(source_sha256=sha(source), compiler_sha256=sha(compiler), flags=FLAGS)
        if not exe.exists() or not stamp.exists():
            result = subprocess.run([str(compiler), *FLAGS, str(source), "-o", str(exe)],
                                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
            if result.returncode:
                raise RuntimeError(result.stderr or result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            save(stamp, dict(**build_id, executable_sha256=sha(exe)))
        expected = dict(**build_id, executable_sha256=sha(exe))
        if json.loads(stamp.read_text(encoding="utf-8")) != expected:
            raise RuntimeError("Cached compiler inputs or executable changed")
        executables[name] = exe
    generated = make_scenarios(args.per_family, [args.split])
    if args.limit:
        generated = generated[:args.limit]
    cases = [dict(name=c.name, N=len(c.values), family=c.family, difficulty=c.difficulty,
                  values=list(c.values), metadata=m) for c, m in generated]
    dataset_hash = hashlib.sha256(encoded(cases)).hexdigest()
    phase = out / args.split
    case_file = phase / "cases.json"
    case_payload = dict(dataset_sha256=dataset_hash, cases=cases)
    if case_file.exists() and json.loads(case_file.read_text(encoding="utf-8")) != case_payload:
        raise RuntimeError("Cached dataset changed")
    save(case_file, case_payload)
    baseline = None
    summaries = {}
    for name, exe in executables.items():
        report_file = phase / (name + ".json")
        context = dict(dataset_sha256=dataset_hash, source_sha256=manifest["sources"][name]["sha256"],
                       executable_sha256=sha(exe), judge_sha256=manifest["judge_sha256"])
        report = dict(**context, rows=[])
        if report_file.exists():
            report = json.loads(report_file.read_text(encoding="utf-8"))
            if {key: report.get(key) for key in context} != context:
                raise RuntimeError("Cached evaluation context changed")
        rows = report["rows"]
        if len(rows) > len(cases) or [r["name"] for r in rows] != [c["name"] for c in cases[:len(rows)]]:
            raise RuntimeError("Cached evaluation order changed")
        for i in range(len(rows), len(generated)):
            case, _ = generated[i]
            row = run_case([str(exe)], case, timeout=args.timeout)
            positions = row["query_positions"]
            winner = min(set(positions), key=lambda x: (-case.values[x], abs(2*x-(len(case.values)-1)), x)) if positions else None
            row["parked_observed_winner"] = bool(positions) and row["final_position"] == winner
            rows.append(row)
            if (i + 1) % 32 == 0:
                save(report_file, report)
                print(f"{args.split} {name}: {i + 1}/{len(cases)}", flush=True)
        save(report_file, report)
        if baseline is None:
            baseline = rows
        summaries[name] = summarize(rows, baseline, cases)
        new_zeros = [dict(case=c, baseline=b, candidate=r) for c, b, r in zip(cases, baseline, rows)
                     if r["score"] == 0 and b["score"] > 0]
        save(phase / "counterexamples" / (name + ".json"), new_zeros)
        print(f"{name}: mean={summaries[name]['base'].get('mean_score', 0):.2f} "
              f"delta={summaries[name]['base'].get('mean_delta', 0):+.2f} "
              f"zero={summaries[name]['base'].get('zero_scores', 0)}", flush=True)
        for group, stats in summaries[name]["by_n"].items():
            if stats["cases"]:
                print(f"  {group}: n={stats['cases']} delta={stats['mean_delta']:+.2f} "
                      f"new/resolved={stats['new_zeros']}/{stats['resolved_zeros']} "
                      f"dQ={stats['mean_query_delta']:+.2f} dM={stats['mean_travel_delta']:+.2f}", flush=True)
        save(phase / "summary.json", dict(official=False, split=args.split,
                                         dataset_sha256=dataset_hash, solvers=summaries))
    for name, path in sources.items():
        if sha(path) != manifest["sources"][name]["sha256"]:
            raise RuntimeError("Source changed during evaluation")
    if sha(ROOT / "main.cpp") != main_hash:
        raise RuntimeError("Formal main.cpp changed during evaluation")
    save(phase / "completion.json", dict(complete=True, cases=len(cases),
         independent_base_cases=sum(c["metadata"]["transform"] == "base" for c in cases),
         solvers=list(sources), main_preserved=True, online_submissions=0))
    return int(any(s["base"].get("hard_failures", 0) or s["transformed_siblings"].get("hard_failures", 0)
                   for s in summaries.values()))


if __name__ == "__main__":
    raise SystemExit(main())
