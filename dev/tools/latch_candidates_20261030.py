"""Preserve a previously witnessed declining-peak frontier across noise changes.

Exports one replayable variant: decline_frontier_latch. This is a heuristic
memory of earlier evidence, not a proof that the old peak is globally maximal.
When the old peak is secondary, retaining its frontier can miss a later main
peak. Never-significant and initial rising histories do not acquire a latch.
No submission or main.cpp edit is performed by this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

if __package__:
    from .structure_candidates_20261030 import AnchorError, replace_once, variant
else:
    from structure_candidates_20261030 import AnchorError, replace_once, variant


def decline_frontier_latch(source: str) -> str:
    source = replace_once(source, "        int flatRuns=0;", r'''        int flatRuns=0;
        int latchedBest=-1,latchedLeft=-1;''')
    return replace_once(source, "            int limit=frontierLimit(f);", r'''            int limit=frontierLimit(f);
            if (best!=latchedBest) { latchedBest=best;latchedLeft=-1; }
            if (!strict) {
                // Store only a significant peak with a witnessed falling side.
                // A later noise estimate must not silently erase that history.
                // An old secondary peak can still make this latch stop early.
                if (f.significant && rightmost>best+16 && f.falls>=2)
                    latchedLeft=f.left;
                else if (!f.significant && latchedLeft>=0)
                    limit=min(limit,min(n-1,latchedLeft+199));
            }''')


variants = [variant(
    "decline_frontier_latch",
    "记住已显著且出现两次下降的峰前沿；同一最佳点后续不显著时仍守原+199边界",
    decline_frontier_latch,
    "提分支持噪声重估撤销旧下降证据会引发不可逆冗余；退分说明旧主峰可能是次峰，保留旧边界漏掉后峰。strict原路径不变。",
)]


def validate(source_path: Path, out: Path) -> bool:
    if __package__:
        from .local_judge import make_suite, run_case
    else:
        from local_judge import make_suite, run_case
    root = Path(__file__).resolve().parents[2]
    out.mkdir(parents=True, exist_ok=True)
    compiler = root/"dev/toolchains/w64devkit/bin/g++.exe"
    source_bytes = source_path.read_bytes()
    text = source_bytes.decode("utf-8")
    report = dict(parent=str(source_path), parent_sha256=hashlib.sha256(source_bytes).hexdigest(),
                  purpose="Protocol-only checks; no local performance selection.", builds=[])
    texts = dict(baseline=text, decline_frontier_latch=variants[0]["apply"](text))
    binaries = {}
    flags = ["-O3", "-Wall", "-Wextra", "-Wpedantic", "-std=c++17"]
    for name, content in texts.items():
        path, exe = out/(name+".cpp"), out/(name+".exe")
        path.write_text(content, encoding="utf-8", newline="\n")
        args = [str(compiler), *flags, str(path), "-o", str(exe)]
        build = subprocess.run(args, capture_output=True, text=True)
        report["builds"].append(dict(name=name, command=args, source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                     exit_code=build.returncode, stdout=build.stdout, stderr=build.stderr))
        if build.returncode or build.stderr:
            raise RuntimeError(f"Compiler error or warning for {name}: {build.stderr}")
        binaries[name] = exe
    rows, strict_rows = [], []
    for case in make_suite("smoke"):
        r = run_case([str(binaries["decline_frontier_latch"])], case)
        positions = r["query_positions"]
        winner = min(positions, key=lambda x: (-case.values[x], abs(2*x-(len(case.values)-1)), x)) if positions else None
        ok = (r["status"]=="ok" and r["queries"]<=199 and r["oscillations"]<=6 and
              positions and positions[-1]==winner)
        rows.append(dict(name=case.name, ok=bool(ok), status=r["status"], queries=r["queries"],
                         oscillations=r["oscillations"], parked_observed_winner=bool(positions and positions[-1]==winner),
                         error=r["error"]))
        baseline = run_case([str(binaries["baseline"]), "--strict-redundancy"], case)
        changed = run_case([str(binaries["decline_frontier_latch"]), "--strict-redundancy"], case)
        strict_rows.append(dict(name=case.name, identical_path=(baseline["query_positions"]==changed["query_positions"]),
                                status=changed["status"]))
    report["smoke"] = rows
    report["strict_path_equivalence"] = strict_rows
    report["passed"] = all(r["ok"] for r in rows) and all(r["identical_path"] and r["status"]=="ok" for r in strict_rows)
    (out/"protocol_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(dict(passed=report["passed"], smoke_passed=sum(r["ok"] for r in rows),
                          smoke_cases=len(rows), strict_equal=sum(r["identical_path"] for r in strict_rows)), ensure_ascii=False))
    return report["passed"]


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--source", type=Path, default=root/"main.cpp")
    parser.add_argument("--out", type=Path, default=root/"dev/build/latch_20261030_protocol")
    args = parser.parse_args()
    if args.validate:
        try:
            return 0 if validate(args.source.resolve(), args.out.resolve()) else 1
        except (AnchorError, RuntimeError) as error:
            print(str(error))
            return 1
    print(variants[0]["name"], variants[0]["description"], variants[0]["interpretation"], sep="\t")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
