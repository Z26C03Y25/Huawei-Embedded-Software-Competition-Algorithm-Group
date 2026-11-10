"""Run explicitly named, reviewed variants sequentially under the 30-round authorization.

Each variant derives from the latest confirmed best, passes the single-round
controller, and finishes grading before the next source is generated. No schedule.
"""
from pathlib import Path
import argparse
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev"))
from tools.narrow_candidates_20261030 import variants as narrow
from tools.structure_candidates_20261030 import variants as structure
from tools.phase_candidates_20261030 import variants as phase
from tools.reach_candidates_20261030 import variants as reach
from tools.noise_sampling_candidates_20261030 import variants as noise
from tools.latch_candidates_20261030 import variants as latch
from tools.economic_candidates_20261030 import variants as economic
from tools.online_round_20261030 import main as run_round


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    available = {v["name"]: v for v in [*narrow, *structure, *phase, *reach, *noise, *latch, *economic]}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="+", choices=list(available))
    parser.add_argument("--stop-on-improvement", action="store_true",
                        help="return after a promotion so the caller can reassess incompatible alternatives")
    args = parser.parse_args()
    out = ROOT / "data/experiments/online_20261030"
    for name in args.names:
        if (out / "stop_after_current").exists():
            print("Stopped before another upload by stop_after_current.", flush=True)
            return 0
        v = available[name]
        parent = (ROOT / "main.cpp").read_bytes()
        transformed = v["apply"](parent.decode("utf-8-sig").replace("\r\n", "\n"))
        path = out / f"{name}_{hashlib.sha256(parent).hexdigest()[:8]}.cpp"
        contents = transformed.encode("utf-8")
        if path.exists() and path.read_bytes() != contents:
            raise RuntimeError("Frozen variant source already exists with different bytes")
        path.write_bytes(contents)
        print(f"NEXT REVIEWED VARIANT {name}: {v['description']}", flush=True)
        result = run_round(["--name", name, "--source", str(path), "--description", v["description"]])
        if result:
            print(f"Stopped on round exit {result}; inspect/resume the existing job before any new upload.", flush=True)
            return result
        if args.stop_on_improvement and (ROOT / "main.cpp").read_bytes() != parent:
            print("Confirmed best improved; stop this batch for the caller's next decision.", flush=True)
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
