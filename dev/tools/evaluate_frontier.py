"""Fast paired ablations, still enforcing the exact query/reply protocol.

Compile dev/tools/strategy_lab.cpp with and without LAB_BASELINE first. Curves remain
private to the adapter; the included solver only receives queried values.
"""
from collections import Counter, defaultdict
import argparse
import hashlib
import math
import json
from pathlib import Path
import subprocess
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev"))
from tools.compare_solvers import make_benchmark
from tools.local_judge import Case, make_suite, score_path


def cases_for(split):
    seeds = (31415, 27182) if split == "training" else (161803, 141421)
    cases = [item.case for seed in seeds for item in make_benchmark(seed, 280)]
    if split == "training":
        cases.extend(make_suite("extended", 2026))
        a = [0]*1000
        a[200:361] = [10000]*161
        for p, v in ((224, 10090), (248, 10089), (272, 10088), (347, 10100)):
            a[p] = v
        cases.append(Case("wide_347", tuple(a), "regression"))
        a = [0]*1000
        a[200:401] = [10000]*201
        a[201], a[336] = 10100, 10090
        cases.append(Case("wide_201", tuple(a), "regression"))
    rng = random.Random(7129 if split == "training" else 918273)
    for number in range(96):
        n = rng.randint(400, 1000)
        p = rng.randrange(n)
        width = rng.uniform(20, n/5)
        sigma = (0.05, 0.1, 0.2, 0.4, 0.6, 0.8)[number % 6]
        a = []
        for i in range(n):
            signal = math.exp(-0.5*((i-p)/width)**2) if number % 2 else max(0, 1-abs(i-p)/width)
            a.append(max(0, round(1000000*(1+signal+rng.uniform(-sigma, sigma)))))
        cases.append(Case(f"noisy_snr_{number}", tuple(a), f"noise_snr_{sigma}"))
    return cases


def evaluate(command, cases):
    payload = str(len(cases))+"\n"+"".join(
        str(len(c.values))+"\n"+" ".join(map(str, c.values))+"\n" for c in cases)
    result = subprocess.run(command, input=payload, text=True, capture_output=True, timeout=180)
    if result.returncode:
        raise RuntimeError(result.stderr)
    lines = result.stdout.splitlines()
    if len(lines) != len(cases):
        raise ValueError("missing case results")
    rows = []
    for case, line in zip(cases, lines):
        fields = list(map(int, line.split()))
        metrics = score_path(case.values, fields[7:])
        expected = [metrics[k] for k in ("score", "queries", "travel", "oscillations",
                                         "redundancy", "distance", "final_position")]
        if fields[:7] != expected:
            raise AssertionError((case.name, fields[:7], expected))
        if metrics["queries"] > 199 or metrics["oscillations"] > 6:
            raise AssertionError((case.name, metrics))
        rows.append({"name": case.name, "family": case.family, **metrics,
                     "positions": fields[7:]})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("training", "holdout"), default="training")
    parser.add_argument("--profiles", nargs="+", type=int, default=[1, 2, 3])
    parser.add_argument("--replay-json", type=Path, help="replay exact arrays retained by an earlier ablation")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.replay_json:
        payload = json.loads(args.replay_json.read_text(encoding="utf-8"))
        cases = [Case(c["name"], tuple(c["values"]), c["family"], c.get("group", "structured"))
                 for c in payload["cases"]]
    else:
        cases = cases_for(args.split)
    results = {}
    commands = {"159487": [str(ROOT / "dev/build/lab_baseline.exe")]}
    commands.update({f"p{i}": ([str(ROOT / "dev/build/lab_flat199.exe")] if i == 10 else
                              [str(ROOT / "dev/build/lab_trend.exe"), str(4 if i == 11 else 6)] if i in (11, 12) else
                              [str(ROOT / "dev/build/lab_candidate.exe"), str(i)]) for i in args.profiles})
    for name, command in commands.items():
        rows = evaluate(command, cases)
        results[name] = rows
        family = defaultdict(lambda: [0, 0, 0])
        for r in rows:
            family[r["family"]][0] += r["score"]
            family[r["family"]][1] += r["score"] == 0
            family[r["family"]][2] += 1
        print(name, "total", sum(r["score"] for r in rows), "zero", sum(r["score"] == 0 for r in rows),
              "max_q", max(r["queries"] for r in rows), "max_o", max(r["oscillations"] for r in rows),
              "reasons", dict(Counter(x for r in rows for x in r["zero_reasons"])), flush=True)
        print(dict(sorted(family.items())), flush=True)
    args.output.parent.mkdir(exist_ok=True, parents=True)
    args.output.write_text(json.dumps({"split": args.split,
        "candidate_source_sha256": hashlib.sha256((ROOT / "data/versions/main_frontier_candidate.cpp").read_bytes()).hexdigest(),
        "flat199_source_sha256": hashlib.sha256((ROOT / "data/versions/main_flat199_candidate.cpp").read_bytes()).hexdigest(),
        "trend_source_sha256": hashlib.sha256((ROOT / "data/versions/main_trend_candidate.cpp").read_bytes()).hexdigest(),
        "seeds": [31415, 27182] if args.split == "training" else [161803, 141421],
        "cases": [{"name": c.name, "family": c.family,
                   "group": "information_limited" if c.family in {"random_unstructured", "single_spike"} else "structured",
                   "values": c.values} for c in cases],
        "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
