"""Public entry for online grading; delegates once, without upload retries."""
from pathlib import Path
import os
import subprocess
import sys


def main() -> int:
    base = Path(__file__).resolve().parent / "online_judge"
    python = base / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return subprocess.run([str(python) if python.is_file() else sys.executable,
                           str(base / "judge.py"), *sys.argv[1:]]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
