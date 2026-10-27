#!/usr/bin/env python3
"""Sweep width-step condition variants against the baseline extended results."""
from __future__ import annotations
import json
import subprocess
import sys
import tempfile
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/experiments/expected_reward_20261027/width_step.cpp"
BASE_JSON = ROOT / "dev/build/_cmp_main.json"

MARKER = "                // 峰宽自适应"
OLD_TAIL = "step=12;"

VARIANTS = {
    "v1_plateau48": (
        "// 峰宽自适应：仅在明确平台（精确最大值等值区间>=48）用大步长。\n"
        "                if (f.significant && !f.noisy && !f.rebound && f.plateau\n"
        "                    && f.plateauRight-f.plateauLeft>=48) step=12;\n"
    ),
    "v2_topwidth48": (
        "// 峰宽自适应：峰顶(tolerance 内)宽度>=48 用大步长。\n"
        "                if (f.significant && !f.noisy && !f.rebound && f.x.size()>=20\n"
        "                    && f.right-f.left>=48) step=12;\n"
    ),
    "v3_bothflanks24": (
        "// 峰宽自适应：左右半高宽均>=24 才用大步长。\n"
        "                if (f.significant && !f.noisy && !f.rebound && f.x.size()>=20\n"
        "                    && f.halfLeft>=24 && f.halfRight>=24) step=12;\n"
    ),
    "v4_plateau_or_bothflanks": (
        "// 峰宽自适应：平台或左右半高宽均宽。\n"
        "                if (f.significant && !f.noisy && !f.rebound && f.x.size()>=20\n"
        "                    && (f.plateau ? f.plateauRight-f.plateauLeft>=48\n"
        "                                   : (f.halfLeft>=24 && f.halfRight>=24))) step=12;\n"
    ),
    "v5_halfright24": (
        "// 峰宽自适应：右半高宽>=24（右翼已解析且宽）才用大步长。\n"
        "                if (f.significant && !f.noisy && !f.rebound && f.x.size()>=20\n"
        "                    && f.halfRight>=24) step=12;\n"
    ),
    "v6_flat_top_or_topwidth": (
        "// 峰宽自适应：精确平台>=48 或 tolerance 顶宽>=64。\n"
        "                if (f.significant && !f.noisy && !f.rebound && f.x.size()>=20\n"
        "                    && (f.plateauRight-f.plateauLeft>=48 || f.right-f.left>=64)) step=12;\n"
    ),
}


def build_variant(src: str, replacement: str, out_cpp: Path) -> None:
    i = src.index(MARKER)
    j = src.index(OLD_TAIL, i)
    end = src.index("}", j) + 1
    new_src = src[:i] + replacement + src[end:]
    out_cpp.write_text(new_src, encoding="utf-8")


def run_extended(exe: Path) -> dict:
    cmd = [sys.executable, str(ROOT / "dev/tools/local_judge.py"),
           "--program", str(exe), "--suite", "extended",
           "--json-output", str(ROOT / "dev/build/_sweep.json")]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    data = json.loads((ROOT / "dev/build/_sweep.json").read_text(encoding="utf-8"))
    return data


def main():
    src = SRC.read_text(encoding="utf-8")
    base = json.loads(BASE_JSON.read_text(encoding="utf-8"))
    base_by_name = {r["name"]: r for r in base["results"]}

    print(f"{'variant':<26} {'std':>7} {'chal':>7} {'net':>6} {'up':>3} {'dn':>3} {'up_sum':>6} {'dn_sum':>6}")
    results = {}
    for name, repl in VARIANTS.items():
        out_cpp = ROOT / f"dev/build/_sw_{name}.cpp"
        exe = ROOT / f"dev/build/_sw_{name}.exe"
        build_variant(src, repl, out_cpp)
        comp = subprocess.run(["g++", "-O2", "-std=c++17", str(out_cpp), "-o", str(exe)],
                              capture_output=True, text=True)
        if comp.returncode != 0:
            print(f"{name:<26} COMPILE FAIL")
            continue
        data = run_extended(exe)
        cur = {r["name"]: r for r in data["results"]}
        std = data["summary"]["standard"]["total_score"]
        chal = data["summary"]["challenging"]["total_score"]
        net = 0
        up = dn = 0
        up_sum = dn_sum = 0
        for cname, rb in cur.items():
            ra = base_by_name[cname]
            d = rb["score"] - ra["score"]
            net += d
            if d > 0:
                up += 1
                up_sum += d
            elif d < 0:
                dn += 1
                dn_sum += d
        results[name] = {"std": std, "chal": chal, "net": net,
                         "up": up, "dn": dn, "up_sum": up_sum, "dn_sum": dn_sum}
        print(f"{name:<26} {std:7} {chal:7} {net:6} {up:3} {dn:3} {up_sum:6} {dn_sum:6}")
    print()
    print("baseline std=109446 chal=57205")


if __name__ == "__main__":
    main()