"""Long-array scout and distant rising-side sampling budget experiments.

These are replayable mutations of the supplied incumbent. The long-scout
alternatives update the current known long band rather than stacking changes.
Previous step_n10 affected a different non-rising branch and is not evidence
against the rising-side experiment below. No upload or main.cpp edit occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

if __package__:
    from .structure_candidates_20261030 import AnchorError, replace_once, variant
else:
    from structure_candidates_20261030 import AnchorError, replace_once, variant


def long_scout(source: str, coefficient: str, low: int, high: int) -> str:
    pattern = re.compile(r"clamp\(static_cast<int>\(f\.halfLeft\*(1\.2|1\.0|0\.8)\),(96,144|80,112|64,96)\)\);")
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise AnchorError(f"Expected exactly one recognized long scout tail, got {len(matches)}")
    match = matches[0]
    allowed = {("1.2", "96,144"), ("1.0", "80,112"), ("0.8", "64,96")}
    if match.groups() not in allowed:
        raise AnchorError(f"Inconsistent incumbent scout coefficient and band: {match.groups()}")
    replacement = f"clamp(static_cast<int>(f.halfLeft*{coefficient}),{low},{high}));"
    if match[0] == replacement:
        raise AnchorError("Long scout already matches this experiment")
    return replace_once(source, match[0], replacement)


def long_rising16(source: str) -> str:
    return replace_once(source,
        "                if (f.leftEdge && rightmost-best>=48) { use(Op::H01); break; }",
        r'''                // A 16-position step preserves the parent's 8-grid phase.
                // Only a clearly rising, significant, low-noise long curve can
                // skip the intermediate probe. A wrong extrapolation can miss
                // a narrow raw peak; this is not a bound on the actual curve.
                if (n>650 && f.significant && !f.noisy && f.rises>=2 && f.falls==0 && f.x.size()>=4) {
                    const size_t count=f.x.size();
                    const int before=f.x[count-4],a=f.x[count-3],b=f.x[count-2],c=f.x[count-1];
                    if (value[before]<value[a] && value[a]<value[b] && value[b]<value[c]) {
                        const double sl=static_cast<double>(value[b]-value[a])/(b-a);
                        const double sr=static_cast<double>(value[c]-value[b])/(c-b);
                        const double curve=(sr-sl)/(c-a);
                        if (curve<-1e-12) {
                            const double predicted=(a+b)/2.0-sl/(2*curve);
                            if (isfinite(predicted) && predicted-rightmost>=32.0) step=16;
                        }
                    }
                }
                // Otherwise the ordinary step=8 assignment above applies,
                // including when the predicted concave peak is less than 32 away.
                if (f.leftEdge && rightmost-best>=48) { use(Op::H01); break; }''')


def mid_scout64(source: str) -> str:
    return replace_once(source,
        "n<=650 ? clamp(static_cast<int>(f.halfLeft*1.05),80,112)",
        "n<=650 ? clamp(static_cast<int>(f.halfLeft*0.8),64,96)")


def mid_factor_or_cap(source: str, *, coefficient: str | None = None, cap: int | None = None) -> str:
    # Preserve every incumbent parameter except the single requested factor or
    # upper cap. In particular, never lower the sentinel's minimum scout of 80.
    pattern = re.compile(r"n<=650 \? clamp\(static_cast<int>\(f\.halfLeft\*(1\.05|0\.8)\),80,(112|96)\)")
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise AnchorError(f"Expected one recognized middle scout with floor 80, got {len(matches)}")
    match = matches[0]
    factor = coefficient if coefficient is not None else match[1]
    upper = cap if cap is not None else int(match[2])
    replacement = f"n<=650 ? clamp(static_cast<int>(f.halfLeft*{factor}),80,{upper})"
    if replacement == match[0]:
        raise AnchorError("Middle scout already has the requested factor/cap")
    return replace_once(source, match[0], replacement)


variants = [
    variant("long_scout80", "仅N>650将确认带改为1.0×半宽、80至112格", lambda s: long_scout(s,"1.0",80,112),
            "若命中不变，少走的出程/回程/冗余均可省分；退分可能是长数组第二峰未覆盖。"),
    variant("long_scout64", "仅N>650将确认带改为0.8×半宽、64至96格，可替换已接受80带", lambda s: long_scout(s,"0.8",64,96),
            "更强止损对照；覆盖损失风险高于80带，但不以旧的本地结果预先否定线上。"),
    variant("long_rising16", "长数组显著低噪连续上升、三点凹顶预测仍远时按16格推进", long_rising16,
            "省上升侧查询并保持8格相位；距预测峰小于32格恢复8。错误外推或原始尖峰会导致漏峰。"),
    variant("mid_scout64", "仅501至650将确认带改为0.8×半宽、64至96格", mid_scout64,
            "中段强止损对照；历史中段轻微缩短曾线上降分，因此漏后峰风险明确，仍由本轮正式对照判断。"),
    variant("mid_factor08_keep80", "仅中段系数改0.8，保留当前80下界和上夹取", lambda s: mid_factor_or_cap(s,coefficient="0.8"),
            "单独检验系数而不把下界降到哨兵激活区间80以下；旧mid076和mid110同时改系数及下界，不能替代这个对照。"),
    variant("mid_cap96_keep80", "仅中段上夹取改96，保留当前系数和80下界", lambda s: mid_factor_or_cap(s,cap=96),
            "只限制宽峰的确认行程；若系数实验已接受则保留其新系数，避免恢复旧值造成混杂。"),
]


def validate(source_path: Path, out: Path) -> bool:
    if __package__:
        from .local_judge import make_suite, run_case
    else:
        from local_judge import make_suite, run_case
    root = Path(__file__).resolve().parents[2]
    out.mkdir(parents=True, exist_ok=True)
    compiler = root/"dev/toolchains/w64devkit/bin/g++.exe"
    source_bytes = source_path.read_bytes()
    report = dict(parent=str(source_path), parent_sha256=hashlib.sha256(source_bytes).hexdigest(),
                  purpose="Compile and protocol-only smoke; no local performance selection.", variants=[])
    for item in variants:
        row = dict(name=item["name"], description=item["description"])
        try:
            text = item["apply"](source_bytes.decode("utf-8"))
            path, exe = out/(item["name"]+".cpp"), out/(item["name"]+".exe")
            path.write_text(text, encoding="utf-8", newline="\n")
            row["source_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            args = [str(compiler), "-O3", "-Wall", "-Wextra", "-Wpedantic", "-std=c++17", str(path), "-o", str(exe)]
            build = subprocess.run(args, capture_output=True, text=True)
            row["build"] = dict(command=args, exit_code=build.returncode, stdout=build.stdout, stderr=build.stderr)
            if build.returncode or build.stderr:
                raise RuntimeError("Compiler error or warning")
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
            row["smoke"] = rows
            row["passed"] = all(r["ok"] for r in rows)
        except (AnchorError, RuntimeError) as error:
            row.update(passed=False, error=str(error))
        report["variants"].append(row)
        print(item["name"],row["passed"],flush=True)
    (out/"protocol_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return all(row["passed"] for row in report["variants"])


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--source", type=Path, default=root/"main.cpp")
    parser.add_argument("--out", type=Path, default=root/"dev/build/budget_20261030_protocol")
    args = parser.parse_args()
    if args.validate:
        return 0 if validate(args.source.resolve(), args.out.resolve()) else 1
    for item in variants:
        print(item["name"],item["description"],item["interpretation"],sep="\t")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
