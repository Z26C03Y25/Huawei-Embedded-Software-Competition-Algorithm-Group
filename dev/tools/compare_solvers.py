#!/usr/bin/env python3
"""Compare autofocus solvers on balanced, reproducible synthetic distributions.

Examples:
  python dev/tools/compare_solvers.py --programs v1=dev/build/main.exe v2=dev/build/new.exe
  python dev/tools/compare_solvers.py --programs v1=dev/build/main.exe --seed 2026 --seed 73 --count 144 --json-output dev/build/benchmark.json
  python dev/tools/compare_solvers.py --programs v2=dev/build/new.exe --replay-json dev/build/benchmark.json --case near_double

--count is the number of curves PER SEED (default 144). Families are interleaved
and nearly equally represented. At least half of curves use non-Gaussian models.
Unstructured random arrays and isolated single-point peaks are reported separately:
no algorithm with fewer than 200 queries can guarantee finding arbitrary maxima
in arrays of length 400-1000. Other difficult families also carry no guarantee.

Every JSON report retains complete arrays and each solver's query positions and
observed values. The structured macro mean gives each family equal weight; neither
that mean nor the synthetic total predicts the official 102-case score. Process
and protocol checks are delegated to local_judge.run_case (no memory cap).
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import random
import sys
from typing import Sequence

if __package__:
    from .local_judge import Case, run_case
else:
    from local_judge import Case, run_case


GENERATOR_VERSION = 1
INT_MAX = 2**31 - 1
FAMILIES = (
    "unimodal", "near_double", "far_double", "noisy_broad_top", "narrow_peak",
    "delayed_right_peak", "left_boundary", "right_boundary", "rippled_peak",
    "monotone", "plateau_and_ties", "flat", "random_unstructured", "single_spike",
)
INFORMATION_LIMITED = frozenset(("random_unstructured", "single_spike"))
MODELS = ("triangle", "lorentz", "asymmetric", "gaussian", "flat_top", "piecewise")


@dataclass(frozen=True)
class BenchmarkCase:
    case: Case
    metadata: dict


def peak_profile(index: int, peak: int, width: float, model: str) -> float:
    """Unit-height profiles; width is a scale, not an identical FWHM convention."""
    x = abs(index - peak) / width
    if model == "gaussian":
        return math.exp(-0.5 * x * x)
    if model == "lorentz":
        return 1.0 / (1.0 + x * x)
    if model == "triangle":
        return max(0.0, 1.0 - x)
    if model == "asymmetric":
        scale = width * (0.43 if index < peak else 1.8)
        return math.exp(-(abs(index - peak) / scale)**1.3)
    if model == "flat_top":
        return max(0.0, 1.0 - max(0.0, x - 0.3) / 0.9)
    if model == "piecewise":
        knots = ((0.0, 1.0), (0.18, 0.97), (0.45, 0.6), (1.0, 0.14), (1.9, 0.0))
        for (left, a), (right, b) in zip(knots, knots[1:]):
            if x <= right:
                return a + (b - a) * (x - left) / (right - left)
        return 0.0
    raise ValueError(f"unknown model: {model}")


def make_benchmark(seed: int = 2026, count: int = 144) -> list[BenchmarkCase]:
    """Generate independently of solver behavior, with prefix-stable case counts."""
    if count <= 0:
        raise ValueError("count must be positive")
    rng = random.Random(seed)
    cases = []
    for number in range(count):
        family = FAMILIES[number % len(FAMILIES)]
        n = rng.randint(400, 1000)
        # Advance one model on each new round of the same family. Using the
        # absolute number again would alias the periods and miss some models.
        model_index = number // len(FAMILIES) + number % len(FAMILIES)
        model = MODELS[model_index % len(MODELS)]
        amplitude = rng.choice((1000, 20000, 1000000, 500000000))
        baseline = rng.randint(0, max(1, amplitude // 30))
        peak = rng.randrange(n)
        width = rng.uniform(n * 0.045, n * 0.22)
        metadata = {"seed": seed, "number": number, "models": [model],
                    "amplitude": amplitude, "baseline": baseline}

        def profile(p=peak, w=width, m=model):
            return [peak_profile(i, p, w, m) for i in range(n)]

        if family in ("near_double", "far_double"):
            if family == "near_double":
                separation = rng.randint(35, min(180, n // 3))
                left = rng.randint(max(3, n // 12), n - separation - max(4, n // 12))
                right = left + separation
                width = separation * rng.uniform(0.18, 0.55)
            else:
                left = rng.randint(0, n * 3 // 10)
                right = rng.randint(n * 65 // 100, n - 1)
                width = rng.uniform(n * 0.025, n * 0.09)
            second_model = MODELS[(model_index + 2) % len(MODELS)]
            right_width = width * rng.uniform(0.6, 1.8)
            ratio = rng.uniform(0.58, 0.98)
            left_height, right_height = ((1.0, ratio) if rng.randrange(2) else (ratio, 1.0))
            merge = rng.choice(("max", "sum"))
            values = []
            for i in range(n):
                a = left_height * peak_profile(i, left, width, model)
                b = right_height * peak_profile(i, right, right_width, second_model)
                values.append(max(a, b) if merge == "max" else a + b)
            metadata.update(models=[model, second_model], peaks=[left, right],
                            widths=[width, right_width], heights=[left_height, right_height], merge=merge)
        elif family == "noisy_broad_top":
            peak = rng.randint(n // 5, n * 4 // 5)
            width = rng.uniform(n * 0.12, n * 0.28)
            values = profile(peak, width, "flat_top")
            noise = rng.uniform(0.003, 0.07)
            correlated = rng.choice((True, False))
            state = 0.0
            for i in range(n):
                fresh = rng.uniform(-noise, noise)
                state = 0.8 * state + fresh * 0.2 if correlated else fresh
                values[i] += state
            metadata.update(models=["flat_top"], peak=peak, width=width,
                            noise_fraction=noise, correlated_noise=correlated)
        elif family == "narrow_peak":
            peak = rng.randint(n // 12, n - 1 - n // 12)
            width = rng.uniform(1.8, 28.0)
            values = profile(peak, width)
            metadata.update(peak=peak, width=width)
        elif family == "delayed_right_peak":
            peak = rng.randint(n * 65 // 100, n - 1)
            width = rng.uniform(8.0, n * 0.11)
            model = rng.choice(("triangle", "piecewise", "flat_top"))
            values = profile(peak, width, model)
            metadata.update(models=[model], peak=peak, width=width)
        elif family in ("left_boundary", "right_boundary"):
            offset = rng.randint(0, 4)
            peak = offset if family == "left_boundary" else n - 1 - offset
            values = profile(peak, width)
            metadata.update(peak=peak, width=width)
        elif family == "rippled_peak":
            peak = rng.randint(n // 6, n * 5 // 6)
            values = profile(peak, width)
            ripple = rng.uniform(0.002, 0.04)
            period = rng.uniform(4.0, 27.0)
            phase = rng.uniform(0.0, 2 * math.pi)
            values = [v + ripple * math.sin(2 * math.pi * i / period + phase)
                      for i, v in enumerate(values)]
            metadata.update(peak=peak, width=width, ripple_fraction=ripple,
                            ripple_period=period, ripple_phase=phase)
        elif family == "monotone":
            values = []
            total = 0
            for _ in range(n):
                total += rng.randint(1, 20)
                values.append(total)
            values = [v / total for v in values]
            descending = bool(rng.randrange(2))
            if descending:
                values.reverse()
            metadata.update(models=["piecewise_monotone"], descending=descending)
        elif family == "plateau_and_ties":
            if rng.randrange(2):
                peak = rng.randint(n // 5, n * 4 // 5)
                width = rng.uniform(8, n * 0.16)
                values = profile(peak, width, "flat_top")
                metadata.update(models=["flat_top"], peak=peak, width=width)
            else:
                left = rng.randint(n // 10, n * 3 // 10)
                right = n - 1 - left
                width = rng.uniform(n * 0.025, n * 0.08)
                values = [max(peak_profile(i, left, width, "triangle"),
                              peak_profile(i, right, width, "triangle")) for i in range(n)]
                metadata.update(models=["triangle"], peaks=[left, right], width=width)
        elif family == "flat":
            values = [0.0] * n
            metadata.update(models=["constant"])
        elif family == "random_unstructured":
            values = [rng.random() for _ in range(n)]
            metadata.update(models=["independent_uniform"])
        elif family == "single_spike":
            values = [0.0] * n
            values[peak] = 1.0
            metadata.update(models=["isolated_point"], peak=peak)
        else:
            values = profile()
            metadata.update(peak=peak, width=width)
        integer_values = tuple(min(INT_MAX, max(0, round(baseline + amplitude * v)))
                               for v in values)
        group = "information_limited" if family in INFORMATION_LIMITED else "structured"
        name = f"s{seed}_{number:04d}_{family}"
        cases.append(BenchmarkCase(Case(name, integer_values, family, group), metadata))
    return cases


def describe_cases(cases: Sequence[BenchmarkCase]) -> list[dict]:
    return [{"name": item.case.name, "family": item.case.family,
             "group": item.case.difficulty, "target": item.case.target,
             "values": list(item.case.values), "metadata": item.metadata}
            for item in cases]


def decode_cases(payload: dict) -> list[BenchmarkCase]:
    result = []
    names = set()
    for row in payload["cases"]:
        if row["name"] in names:
            raise ValueError("duplicate case names in replay report")
        names.add(row["name"])
        case = Case(row["name"], tuple(row["values"]), row["family"], row["group"])
        if not 400 <= len(case.values) <= 1000:
            raise ValueError("replay curve length must be in [400, 1000]")
        result.append(BenchmarkCase(case, row.get("metadata", {})))
    return result


def summarize(results: Sequence[dict]) -> dict:
    def aggregate(rows):
        count = len(rows)
        return {"cases": count, "total_score": sum(r["score"] for r in rows),
                "mean_score": sum(r["score"] for r in rows) / count if count else 0.0,
                "zero_scores": sum(r["score"] == 0 for r in rows),
                "errors": sum(r["status"] != "ok" for r in rows),
                "exact_hits": sum(r["distance"] == 0 and r["status"] == "ok" for r in rows),
                "mean_queries": sum(r["queries"] for r in rows) / count if count else 0.0,
                "mean_travel": sum(r["travel"] for r in rows) / count if count else 0.0}

    family_rows = defaultdict(list)
    for row in results:
        family_rows[row["family"]].append(row)
    families = {family: aggregate(rows) for family, rows in sorted(family_rows.items())}
    groups = {}
    for group in ("structured", "information_limited"):
        rows = [r for r in results if r["difficulty"] == group]
        if rows:
            summary = aggregate(rows)
            group_families = {r["family"] for r in rows}
            summary["family_macro_mean_score"] = sum(families[f]["mean_score"]
                                                      for f in group_families) / len(group_families)
            groups[group] = summary
    return {"groups": groups, "families": families}


def compare_results(baseline: Sequence[dict], candidate: Sequence[dict]) -> dict:
    left = {row["name"]: row for row in baseline}
    right = {row["name"]: row for row in candidate}
    if left.keys() != right.keys():
        raise ValueError("paired comparison requires identical case names")
    deltas = []
    for name, before in left.items():
        after = right[name]
        deltas.append({"name": name, "family": before["family"],
                       "group": before["difficulty"], "baseline_score": before["score"],
                       "candidate_score": after["score"], "delta": after["score"] - before["score"]})

    def aggregate(rows):
        return {"cases": len(rows), "score_delta": sum(r["delta"] for r in rows),
                "wins": sum(r["delta"] > 0 for r in rows),
                "ties": sum(r["delta"] == 0 for r in rows),
                "losses": sum(r["delta"] < 0 for r in rows),
                "resolved_zero_scores": sum(r["baseline_score"] == 0 < r["candidate_score"] for r in rows),
                "new_zero_scores": sum(r["candidate_score"] == 0 < r["baseline_score"] for r in rows)}

    return {"groups": {group: aggregate([r for r in deltas if r["group"] == group])
                        for group in sorted({r["group"] for r in deltas})},
            "families": {family: aggregate([r for r in deltas if r["family"] == family])
                         for family in sorted({r["family"] for r in deltas})},
            "case_deltas": sorted(deltas, key=lambda r: (r["delta"], r["name"]))}


def evaluate_programs(cases: Sequence[BenchmarkCase], programs: dict[str, Sequence[str]],
                      timeout: float = 10.0, progress: bool = False) -> dict[str, list[dict]]:
    results = {}
    for name, command in programs.items():
        rows = []
        for index, item in enumerate(cases, 1):
            row = run_case(command, item.case, timeout)
            row["query_values"] = [item.case.values[i] for i in row["query_positions"]]
            rows.append(row)
            if progress and (index % 24 == 0 or index == len(cases)):
                print(f"{name}: {index}/{len(cases)} cases", file=sys.stderr, flush=True)
        results[name] = rows
    return results


def parse_programs(arguments: Sequence[str]) -> tuple[dict, dict]:
    programs, artifacts = {}, {}
    for argument in arguments:
        if "=" not in argument:
            raise ValueError("each --programs entry must be NAME=PATH")
        name, raw_path = argument.split("=", 1)
        if not name or name in programs:
            raise ValueError("program names must be nonempty and unique")
        path = Path(raw_path).resolve()
        if not path.is_file():
            raise ValueError(f"program file does not exist: {raw_path}")
        programs[name] = ([sys.executable, str(path)] if path.suffix.lower() == ".py"
                          else [str(path)])
        artifacts[name] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return programs, artifacts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--programs", nargs="+", help="named executable or Python script paths: NAME=PATH")
    parser.add_argument("--seed", action="append", type=int, help="repeat to run multiple seeds (default 2026)")
    parser.add_argument("--count", type=int, default=144, help="curves per seed, default 144")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--replay-json", type=Path, help="use full curves from an earlier report")
    parser.add_argument("--family", action="append", help="keep only this family; repeatable")
    parser.add_argument("--case", action="append", help="keep names containing this text; repeatable")
    parser.add_argument("--list-cases", action="store_true")
    args = parser.parse_args(argv)
    if args.count <= 0 or not 0 < args.timeout <= 10:
        parser.error("--count must be positive and --timeout must be in (0, 10]")
    seeds = args.seed or [2026]
    count_per_seed = args.count
    if len(set(seeds)) != len(seeds):
        parser.error("duplicate seeds would duplicate case identities")
    try:
        if args.replay_json:
            source_report = json.loads(args.replay_json.read_text(encoding="utf-8"))
            cases = decode_cases(source_report)
            seeds = source_report.get("seeds", [])
            count_per_seed = source_report.get("count_per_seed")
        else:
            cases = [item for seed in seeds for item in make_benchmark(seed, args.count)]
        if args.family:
            cases = [item for item in cases if item.case.family in args.family]
        if args.case:
            cases = [item for item in cases if any(text in item.case.name for text in args.case)]
        if not cases:
            parser.error("no matching curves")
        if args.list_cases:
            for item in cases:
                print(f"{item.case.name:<43} N={len(item.case.values):4} "
                      f"target={item.case.target:4} {','.join(item.metadata.get('models', []))}")
            return 0
        if not args.programs:
            parser.error("--programs is required unless --list-cases is used")
        programs, artifacts = parse_programs(args.programs)
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))
    print("Synthetic distribution stress test; scores do not predict the official dataset.", flush=True)
    print("Random arrays and isolated spikes are kept outside structured totals.", flush=True)
    results = evaluate_programs(cases, programs, args.timeout, progress=True)
    summaries = {name: summarize(rows) for name, rows in results.items()}
    print(f"{'family':<23} {'program':<14} {'cases':>5} {'mean':>8} {'zero':>5} {'errors':>6}")
    for family in sorted({item.case.family for item in cases}):
        for name in programs:
            row = summaries[name]["families"][family]
            print(f"{family:<23} {name:<14} {row['cases']:5} {row['mean_score']:8.1f} "
                  f"{row['zero_scores']:5} {row['errors']:6}")
    for name, summary in summaries.items():
        for group, row in summary["groups"].items():
            print(f"{name} {group}: cases={row['cases']} total={row['total_score']} "
                  f"mean={row['mean_score']:.1f} family_macro_mean={row['family_macro_mean_score']:.1f} "
                  f"zero={row['zero_scores']} errors={row['errors']}")
    baseline_name = next(iter(programs))
    comparisons = {name: compare_results(results[baseline_name], rows)
                   for name, rows in results.items() if name != baseline_name}
    for name, comparison in comparisons.items():
        for group, row in comparison["groups"].items():
            print(f"{name} vs {baseline_name} {group}: delta={row['score_delta']:+} "
                  f"wins/ties/losses={row['wins']}/{row['ties']}/{row['losses']} "
                  f"resolved_zero={row['resolved_zero_scores']} new_zero={row['new_zero_scores']}")
    if args.json_output:
        payload = {"generator_version": GENERATOR_VERSION, "seeds": seeds,
                   "count_per_seed": count_per_seed, "replay_source": str(args.replay_json) if args.replay_json else None,
                   "notes": ["Synthetic scores are not estimates of the official 102-case score.",
                             "Random arrays and isolated spikes are information-limited and scored separately.",
                             "Complete curves, query positions and observed values are retained for reproduction."],
                   "programs": {name: {"command": command, **artifacts[name]} for name, command in programs.items()},
                   "family_case_counts": dict(Counter(item.case.family for item in cases)),
                   "cases": describe_cases(cases), "results": results,
                   "summaries": summaries, "baseline_name": baseline_name, "comparisons": comparisons}
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return int(any(row["status"] != "ok" for rows in results.values() for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
