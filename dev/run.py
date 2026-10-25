"""Offline developer entry points. No command connects to the competition."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dev/build" / ("main.exe" if os.name == "nt" else "main")


def run(arguments: list[str]) -> int:
    print("+ " + " ".join(map(str, arguments)), flush=True)
    return subprocess.run(arguments, cwd=ROOT).returncode


def build() -> int:
    compiler = shutil.which("g++")
    if not compiler:
        print("GCC g++ was not found on PATH. Install a C++17-capable GCC toolchain.", file=sys.stderr)
        return 2
    EXE.parent.mkdir(exist_ok=True)
    return run([compiler, "-O3", "-Wall", "-Wextra", "-Wpedantic", "-std=c++17",
                str(ROOT / "main.cpp"), "-o", str(EXE)])


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "smoke", "check", "diagnostics", "docs"))
    args = parser.parse_args(argv)
    py = sys.executable
    if args.command in {"build", "smoke"}:
        result = build()
        if result or args.command == "build":
            return result
        return run([py, "dev/tools/local_judge.py", "--program", str(EXE), "--suite", "smoke",
                    "--json-output", "dev/build/smoke.json"])
    if args.command == "docs":
        return run([py, "dev/tools/check_docs.py"])
    if args.command == "diagnostics":
        print("Strategy diagnostics retain known failures; see docs/reference/known-limitations.md.", flush=True)
        return run([py, "-m", "unittest", "discover", "-s", "dev/tests", "-p", "test_strategy_solver.py", "-v"])
    if not shutil.which("g++"):
        print("The complete check needs g++; pure Python checks are documented in dev/tests/README.md.", file=sys.stderr)
        return 2
    commands = [[py, "dev/tools/check_docs.py"],
                [py, "-m", "unittest", "discover", "-s", "automation/online_judge/tests"],
                *[[py, "-m", "unittest", "discover", "-s", "dev/tests", "-p", pattern]
                  for pattern in ("test_local_judge.py", "test_compare_solvers.py", "test_solver_regressions.py")]]
    for command in commands:
        result = run(command)
        if result:
            return result
    print("Core checks passed. Full strategy diagnostics are separate and retain known failures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
