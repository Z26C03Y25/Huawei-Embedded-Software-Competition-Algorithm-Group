"""All-N economic suffix experiment without mandatory-candidate completion.

This derives from the replayable mandatory_suffix policy, removing only its
high-priority completion prerequisite. It is equivalent in mechanism to the
earlier all_suffix experiment plus VMAX exclusion and positive parking score.
No model-window experiment is added. The six interpolation scenarios can miss
an unread nearby higher peak even when best+-3 is complete; early zero scores
are an explicit risk. No submission or main.cpp edit is performed here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

if __package__:
    from .structure_candidates_20261030 import AnchorError, mandatory_suffix, replace_once, variant
else:
    from structure_candidates_20261030 import AnchorError, mandatory_suffix, replace_once, variant


def economic_suffix_allN(source: str) -> str:
    source = mandatory_suffix(source)
    source = replace_once(source,
        "    bool structuralSuffixStop(const vector<int>& suffix,const vector<Point>& required) {",
        "    bool economicSuffixStop(const vector<int>& suffix) {")
    source = replace_once(source, r'''        for (const auto& point:required)
            if (point.priority>=100 && value[point.x]<0) return false;
''', r'''        // Deliberately allow stopping before other high-priority points.
        // An unread nearby higher peak can invalidate this economic forecast.
''')
    return replace_once(source,
        "if (structuralSuffixStop(suffix,candidates)) { use(Op::K07); return; }",
        "if (economicSuffixStop(suffix)) { use(Op::K07); return; }")


variants = [variant(
    "economic_suffix_allN",
    "全N经济止损：取消高优先级点必读门槛，保留±3完整与正预测停车收益保护",
    economic_suffix_allN,
    "提分支持及时取消无价值后缀；退分尤其可能来自尚未读取的近邻更高峰。保留VMAX禁用、低噪非平台、远端竞争峰排除及随机/状态恢复。",
)]


def validate(source_path: Path, out: Path) -> bool:
    if __package__:
        from .local_judge import make_suite, run_case
    else:
        from local_judge import make_suite, run_case
    root = Path(__file__).resolve().parents[2]
    out.mkdir(parents=True, exist_ok=True)
    source_bytes = source_path.read_bytes()
    generated = variants[0]["apply"](source_bytes.decode("utf-8"))
    path, exe = out/"economic_suffix_allN.cpp", out/"economic_suffix_allN.exe"
    path.write_text(generated, encoding="utf-8", newline="\n")
    args = [str(root/"dev/toolchains/w64devkit/bin/g++.exe"), "-O3", "-Wall", "-Wextra",
            "-Wpedantic", "-std=c++17", str(path), "-o", str(exe)]
    build = subprocess.run(args, capture_output=True, text=True)
    report = dict(parent=str(source_path), parent_sha256=hashlib.sha256(source_bytes).hexdigest(),
                  source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  purpose="Protocol-only smoke; no local performance selection.",
                  build=dict(command=args, exit_code=build.returncode, stdout=build.stdout, stderr=build.stderr))
    if build.returncode or build.stderr:
        raise RuntimeError(f"Compiler error or warning: {build.stderr}")
    rows = []
    for case in make_suite("smoke"):
        r = run_case([str(exe)], case)
        positions = r["query_positions"]
        winner = min(positions, key=lambda x: (-case.values[x], abs(2*x-(len(case.values)-1)), x)) if positions else None
        ok = (r["status"]=="ok" and r["queries"]<=199 and r["oscillations"]<=6 and
              positions and positions[-1]==winner)
        rows.append(dict(name=case.name, ok=bool(ok), status=r["status"], queries=r["queries"],
                         oscillations=r["oscillations"], parked_observed_winner=bool(positions and positions[-1]==winner),
                         error=r["error"]))
    report["smoke"] = rows
    report["passed"] = all(r["ok"] for r in rows)
    (out/"protocol_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(dict(passed=report["passed"], smoke_cases=len(rows), smoke_passed=sum(r["ok"] for r in rows)), ensure_ascii=False))
    return report["passed"]


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--source", type=Path, default=root/"main.cpp")
    parser.add_argument("--out", type=Path, default=root/"dev/build/economic_20261030_protocol")
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
