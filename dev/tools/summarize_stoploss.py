"""Summarize completed stoploss_study phases, including paired path costs.

  python/runtime/python.exe dev/tools/summarize_stoploss.py --out dev/build/stoploss_20261029

Only completed phases enter this report. Qualification requires all three phases
and the existing robust_score checks. Principal aggregates deduplicate exact base
arrays in phase order, matching robust_score; transformed siblings remain in the
protocol and new-zero audit. No compilation, solver runs or networking occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev"))
from tools import robust_score

PHASES = robust_score.FRESH
BANDS = ("N<=500", "501<=N<=650", "N>650")
COSTS = ("queries", "travel", "oscillations", "redundancy", "distance_cost", "counter_cost", "score_loss")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def array_id(values):
    # Use only the clarity array, not its metadata/name, as independent identity.
    return hashlib.sha256(json.dumps(values, separators=(",", ":")).encode()).hexdigest()


def band(n):
    return BANDS[0] if n <= 500 else BANDS[1] if n <= 650 else BANDS[2]


def costs(row):
    return dict(queries=row["queries"], travel=row["travel"], oscillations=row["oscillations"],
                redundancy=row["redundancy"], distance_cost=200 * row["distance"],
                counter_cost=row["queries"] + row["travel"] + row["oscillations"]
                             + row["redundancy"] + 200 * row["distance"],
                score_loss=3000 - row["score"])


def paired_costs(items):
    if not items:
        return {"cases": 0}
    n = len(items)
    candidate = [costs(r) for r, _, _ in items]
    baseline = [costs(b) for _, b, _ in items]
    avg = lambda data, key: sum(row[key] for row in data) / n
    return dict(cases=n,
                mean={key: avg(candidate, key) for key in COSTS},
                baseline_mean={key: avg(baseline, key) for key in COSTS},
                mean_delta={key: avg(candidate, key) - avg(baseline, key) for key in COSTS})


def stats(items):
    if not items:
        return {"cases": 0}
    mean = robust_score.mean
    scores = [r["score"] for r, _, _ in items]
    base = [b["score"] for _, b, _ in items]
    both = [p for p in items if p[0]["score"] > 0 and p[1]["score"] > 0]
    changed_both = [p for p in both if p[0]["query_positions"] != p[1]["query_positions"]]
    return dict(cases=len(items), mean_score=mean(scores), baseline_mean_score=mean(base),
                mean_delta=mean(scores) - mean(base),
                zero_scores=sum(s == 0 for s in scores), baseline_zero_scores=sum(s == 0 for s in base),
                new_zeros=sum(r["score"] == 0 and b["score"] > 0 for r, b, _ in items),
                resolved_zeros=sum(r["score"] > 0 and b["score"] == 0 for r, b, _ in items),
                cvar25=robust_score.cvar25(scores), baseline_cvar25=robust_score.cvar25(base),
                cvar25_delta=robust_score.cvar25(scores) - robust_score.cvar25(base),
                mean_redundancy_delta=mean([r["redundancy"] - b["redundancy"] for r, b, _ in items]),
                mean_distance_delta=mean([r["distance"] - b["distance"] for r, b, _ in items]),
                all_counter_costs=paired_costs(items),
                paired_positive_score_costs=paired_costs(both),
                changed_paired_positive_score_costs=paired_costs(changed_both))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True, help="existing stoploss_study output directory")
    parser.add_argument("--min-cases", type=int, default=1000)
    parser.add_argument("--min-families", type=int, default=12)
    parser.add_argument("--bootstrap", type=int, default=1000)
    args = parser.parse_args(argv)
    if args.min_cases < 1 or args.min_families < 1 or args.bootstrap < 100:
        parser.error("positive case/family minimums and at least 100 bootstrap replicates required")
    out = Path(args.out)
    out = (ROOT / out).resolve() if not out.is_absolute() else out.resolve()
    manifest = read(out / "manifest.json")
    names = list(manifest["sources"])
    if not names or names[0] != "baseline":
        raise RuntimeError("study must contain baseline as its first source")
    rows = {name: [] for name in names}
    cases = []
    completed = []
    evidence = {"manifest_sha256": sha(out / "manifest.json")}
    for split in PHASES:
        phase = out / split
        if not (phase / "completion.json").exists():
            continue
        completion = read(phase / "completion.json")
        if not completion.get("complete") or completion.get("solvers") != names:
            raise RuntimeError(f"Invalid completion for {split}")
        dataset = read(phase / "cases.json")
        if completion.get("cases") != len(dataset["cases"]):
            raise RuntimeError("Case count mismatch")
        fingerprints = {"cases_sha256": sha(phase / "cases.json"), "rows_sha256": {}}
        for name in names:
            path = phase / (name + ".json")
            result = read(path)
            if result["dataset_sha256"] != dataset["dataset_sha256"] or \
                    result["source_sha256"] != manifest["sources"][name]["sha256"]:
                raise RuntimeError("Evaluation source/dataset identity mismatch")
            if [r["name"] for r in result["rows"]] != [c["name"] for c in dataset["cases"]]:
                raise RuntimeError("Incomplete or reordered evaluation")
            rows[name].extend(result["rows"])
            fingerprints["rows_sha256"][name] = sha(path)
        cases.extend(dataset["cases"])
        completed.append(split)
        evidence[split] = fingerprints
    metadata = [c["metadata"] for c in cases]
    curve_ids = [array_id(c["values"]) for c in cases]
    selected = []
    seen = set()
    for i, (case, identity) in enumerate(zip(cases, curve_ids)):
        if case["metadata"]["transform"] == "base" and identity not in seen:
            seen.add(identity)
            selected.append(i)
    solvers = {}
    for name in names:
        if not cases:
            solvers[name] = {"qualification": dict(eligible=False, reasons=["no completed phases"])}
            continue
        robust = robust_score.analyze(rows[name], rows["baseline"], metadata, curve_ids,
                                     args.min_cases, args.min_families, args.bootstrap)
        if len(completed) != len(PHASES):
            robust["qualification"]["eligible"] = False
            robust["qualification"]["reasons"].insert(0, "all three frozen phases must complete before qualification")
        items = [(rows[name][i], rows["baseline"][i], cases[i]) for i in selected]
        solvers[name] = dict(
            robust_score=robust, independent_base=stats(items),
            by_n={b: stats([p for p in items if band(p[2]["N"]) == b]) for b in BANDS},
            by_phase={split: dict(
                overall=stats([p for p in items if p[2]["metadata"]["split"] == split]),
                by_n={b: stats([p for p in items if p[2]["metadata"]["split"] == split
                               and band(p[2]["N"]) == b]) for b in BANDS}) for split in completed},
        )
        summary = solvers[name]["independent_base"]
        print(f"{name}: mean={summary['mean_score']:.2f} delta={summary['mean_delta']:+.2f} "
              f"CVaR25 delta={summary['cvar25_delta']:+.2f} "
              f"zeros={summary['zero_scores']} eligible={robust['qualification']['eligible']}", flush=True)
        for b, group in solvers[name]["by_n"].items():
            if group["cases"]:
                print(f"  {b}: n={group['cases']} delta={group['mean_delta']:+.2f} "
                      f"dR={group['mean_redundancy_delta']:+.2f} dd={group['mean_distance_delta']:+.2f} "
                      f"CVaR25 delta={group['cvar25_delta']:+.2f}", flush=True)
    payload = dict(official=False, completed_phases=completed,
                   missing_phases=[split for split in PHASES if split not in completed],
                   summarizer_sha256=sha(Path(__file__)), robust_score_sha256=sha(ROOT / "dev/tools/robust_score.py"),
                   thresholds=dict(min_cases=args.min_cases, min_families=args.min_families, bootstrap=args.bootstrap),
                   notes=["Principal cost summaries use deduplicated base arrays.",
                          "counter_cost=Q+M+O+R+200*d; it is not the actual loss on invalid/zero-score cases.",
                          "score_loss=3000-score includes hard-zero penalties.",
                          "paired_positive_score_costs compare only cases where both solvers scored above zero.",
                          "CVaR25 is the mean of the worst quarter, with fractional mass for small samples.",
                          "Partial phases cannot qualify a candidate. Synthetic cohorts do not identify official performance."],
                   evidence=evidence, solvers=solvers)
    target = out / "robust_summary.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(target)
    print(f"Completed: {', '.join(completed) or 'none'}; report: {target}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
