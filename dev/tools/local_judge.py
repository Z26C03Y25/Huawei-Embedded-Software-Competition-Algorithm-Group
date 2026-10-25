#!/usr/bin/env python3
"""Standard-library local checker for the 2026 Huawei autofocus challenge.

Examples:
    python dev/tools/local_judge.py --program dev/build/main.exe --suite smoke
    python dev/tools/local_judge.py --program main.py --suite extended --seed 2026
    python dev/tools/local_judge.py --list-cases --suite extended

These are synthetic development cases, not the official 102 recordings. In
particular, arbitrary spikes, separated peaks and flat curves are intentionally
marked challenging: they demonstrate limitations of sparse sampling. The checker
does not enforce the platform's 512 MB process memory limit.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import queue
import random
import re
import subprocess
import sys
import threading
import time
from typing import Sequence


MAX_LINE_BYTES = 64
MAX_MESSAGES = 201
OFFICIAL_TIMEOUT = 10.0
PDF_SAMPLE = (10, 14, 15, 16, 17, 12, 10, 8, 8, 9, 6, 5)


@dataclass(frozen=True)
class Case:
    name: str
    values: tuple[int, ...]
    family: str = "custom"
    difficulty: str = "standard"

    def __post_init__(self) -> None:
        if not self.values:
            raise ValueError("a case must contain at least one value")
        if any(type(v) is not int or not 0 <= v <= 2**31 - 1 for v in self.values):
            raise ValueError("clarity values must be integers in [0, 2^31-1]")

    @property
    def target(self) -> int:
        return target_index(self.values)


def target_index(values: Sequence[int]) -> int:
    """Maximum value; closest to (N-1)/2; smaller index on an exact tie."""
    if not values:
        raise ValueError("empty curve")
    highest = max(values)
    return min((i for i, v in enumerate(values) if v == highest),
               key=lambda i: (abs(2 * i - (len(values) - 1)), i))


@dataclass
class Metrics:
    queries: int = 0
    travel: int = 0
    oscillations: int = 0
    position: int = 0
    furthest_right: int = 0
    last_direction: int = 0

    def query(self, index: int) -> None:
        delta = index - self.position
        direction = (delta > 0) - (delta < 0)
        if direction:
            if self.last_direction and direction != self.last_direction:
                self.oscillations += 1
            self.last_direction = direction
        self.travel += abs(delta)
        self.position = index
        self.furthest_right = max(self.furthest_right, index)
        self.queries += 1

    @property
    def search_time(self) -> int:
        return self.queries + self.travel

    def score(self, target: int, elapsed: float = 0.0) -> dict:
        distance = abs(self.position - target)
        redundancy = max(0, self.furthest_right - target)
        zero_reasons = []
        if distance > 3:
            zero_reasons.append("distance > 3")
        if self.queries >= 200:
            zero_reasons.append("queries >= 200")
        if self.oscillations >= 7:
            zero_reasons.append("oscillations >= 7")
        if redundancy >= 200:
            zero_reasons.append("redundancy >= 200")
        if elapsed > OFFICIAL_TIMEOUT:
            zero_reasons.append("elapsed > 10 seconds")
        if not self.queries:
            zero_reasons.append("no query")
        points = max(0, 3000 - 200 * distance - self.search_time
                     - self.oscillations - redundancy)
        return {
            "queries": self.queries,
            "travel": self.travel,
            "search_time": self.search_time,
            "oscillations": self.oscillations,
            "redundancy": redundancy,
            "distance": distance,
            "final_position": self.position if self.queries else None,
            "score": 0 if zero_reasons else points,
            "zero_reasons": zero_reasons,
        }


def score_path(values: Sequence[int], positions: Sequence[int], elapsed: float = 0.0) -> dict:
    """Score a known query trajectory without starting a solver."""
    metrics = Metrics()
    for index in positions:
        if type(index) is not int or not 0 <= index < len(values):
            raise ValueError("query index outside the curve")
        metrics.query(index)
    return metrics.score(target_index(values), elapsed)


def run_case(command: Sequence[str], case: Case, timeout: float = OFFICIAL_TIMEOUT) -> dict:
    """Run one fresh solver process using a total wall-clock deadline.

    Dedicated pipe-reader threads work on Windows, where select() cannot wait on
    anonymous subprocess pipes. Output is bounded even for a broken/noisy solver.
    Every stdout byte after DONE is forbidden. stderr is drained and its first
    8192 bytes are kept for diagnostics.
    """
    if not command:
        raise ValueError("empty solver command")
    if not 0 < timeout <= OFFICIAL_TIMEOUT:
        raise ValueError("timeout must be in (0, 10] seconds")
    started = time.monotonic()
    deadline = started + timeout
    metrics = Metrics()
    messages = 0
    query_positions = []
    error = None
    status = "ok"
    done = False
    events: queue.Queue = queue.Queue(maxsize=256)
    stop = threading.Event()
    stderr = bytearray()
    process = None
    threads = []

    def emit(kind: str, payload=None) -> bool:
        while not stop.is_set():
            try:
                events.put((kind, payload), timeout=0.05)
                return True
            except queue.Full:
                pass
        return False

    def read_stdout() -> None:
        line = bytearray()
        try:
            while not stop.is_set():
                byte = process.stdout.read(1)
                if not byte:
                    if line:
                        emit("error", "stdout line is missing its newline")
                    else:
                        emit("eof")
                    return
                if byte[0] > 127:
                    emit("error", "stdout must contain ASCII only")
                    return
                if byte == b"\n":
                    content = bytes(line[:-1] if line.endswith(b"\r") else line)
                    if not emit("line", content):
                        return
                    line.clear()
                else:
                    line.extend(byte)
                    # A final CR can be the first byte of a CRLF terminator.
                    if len(line) > MAX_LINE_BYTES and not (
                        len(line) == MAX_LINE_BYTES + 1 and line[-1] == 13
                    ):
                        emit("error", "stdout line exceeds 64 bytes")
                        return
        except (OSError, ValueError):
            if not stop.is_set():
                emit("error", "failed to read solver stdout")

    def read_stderr() -> None:
        try:
            while not stop.is_set():
                block = process.stderr.read(4096)
                if not block:
                    return
                stderr.extend(block[:max(0, 8192 - len(stderr))])
        except (OSError, ValueError):
            pass

    def send(value: int) -> None:
        process.stdin.write(f"{value}\n".encode("ascii"))
        process.stdin.flush()

    try:
        process = subprocess.Popen(list(command), stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   bufsize=0)
        threads = [threading.Thread(target=read_stdout, daemon=True),
                   threading.Thread(target=read_stderr, daemon=True)]
        for thread in threads:
            thread.start()
        send(len(case.values))
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            try:
                kind, payload = events.get(timeout=remaining)
            except queue.Empty:
                raise TimeoutError from None
            if kind == "error":
                error = payload
                break
            if kind == "eof":
                if not done:
                    error = "solver exited before DONE"
                break
            messages += 1
            if messages > MAX_MESSAGES:
                error = "more than 201 solver messages (queries + DONE)"
                break
            if done:
                error = "stdout output after DONE"
                break
            if payload == b"DONE":
                done = True
                if metrics.queries == 0:
                    error = "DONE requires at least one query to define the final position"
                    break
                continue
            if re.fullmatch(rb"[+-]?[0-9]+", payload) is None:
                error = "expected an integer query index or DONE"
                break
            index = int(payload)
            if not 0 <= index < len(case.values):
                error = f"query index {index} is outside [0, {len(case.values) - 1}]"
                break
            metrics.query(index)
            query_positions.append(index)
            send(case.values[index])
        if not error:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            try:
                exit_code = process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                raise TimeoutError from None
            if exit_code != 0:
                error = f"solver exit code is {exit_code}, expected 0"
    except TimeoutError:
        status = "timeout"
        error = f"case exceeded its {timeout:g} second wall-clock limit"
    except (BrokenPipeError, OSError) as exc:
        status = "launch_error" if process is None else "protocol_error"
        error = f"{type(exc).__name__}: {exc}"
    finally:
        elapsed = time.monotonic() - started
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.wait()
            stop.set()
            for stream in (process.stdin, process.stdout, process.stderr):
                try:
                    stream.close()
                except (BrokenPipeError, OSError):
                    pass
            for thread in threads:
                thread.join(timeout=0.2)
    if error and status == "ok":
        status = "protocol_error"
    result = {
        "name": case.name, "family": case.family, "difficulty": case.difficulty,
        "length": len(case.values), "target": case.target,
        **metrics.score(case.target, elapsed),
        "messages": messages, "elapsed_seconds": round(elapsed, 6),
        "query_positions": query_positions,
        "status": status, "error": error,
        "stderr": stderr.decode("utf-8", errors="replace"),
    }
    if error:
        result["score"] = 0
    return result


def make_suite(suite: str = "smoke", seed: int = 2026) -> list[Case]:
    """Deterministic families. Only the PDF's example has N outside [400, 1000]."""
    if suite not in ("smoke", "extended"):
        raise ValueError("unknown suite")
    rng = random.Random(seed)
    cases = [Case("pdf_sample_12", PDF_SAMPLE, "pdf_sample")]

    def gaussian(n: int, peak: int, width: float, amplitude: int = 1000000) -> list[int]:
        return [100 + round(amplitude * math.exp(-0.5 * ((i - peak) / width) ** 2))
                for i in range(n)]

    smooth_specs = [(400, 47, 42), (600, 293, 75), (1000, 837, 110),
                    (400, 0, 65), (1000, 999, 130), (700, 3, 35),
                    (700, 696, 35), (800, 401, 9)]
    for n, peak, width in smooth_specs:
        family = "boundary" if peak < 4 or peak >= n - 4 else "smooth"
        cases.append(Case(f"{family}_n{n}_p{peak}_w{width}",
                          tuple(gaussian(n, peak, width)), family))
    for n, peak, width, noise in [(600, 240, 65, 200), (1000, 710, 100, 1500)]:
        values = gaussian(n, peak, width)
        values = [max(0, v + rng.randint(-noise, noise)) for v in values]
        cases.append(Case(f"noise_n{n}_p{peak}_a{noise}", tuple(values), "noise"))

    n = 600
    plateau = [max(0, 100000 - 200 * max(270 - i, 0, i - 330)) for i in range(n)]
    cases.append(Case("plateau_270_330_n600", tuple(plateau), "plateau", "challenging"))
    ties = gaussian(n, 180, 50)
    for index in (180, 419):
        ties[index] = 1200000
    cases.append(Case("equal_peaks_180_419_n600", tuple(ties), "tie", "challenging"))
    for name, peaks in [("double_later_higher", [(155, 50, 800000), (470, 65, 1100000)]),
                        ("double_earlier_higher", [(140, 45, 1100000), (470, 65, 800000)])]:
        values = [100 + sum(round(a * math.exp(-0.5 * ((i - p) / w) ** 2))
                            for p, w, a in peaks) for i in range(700)]
        cases.append(Case(name, tuple(values), "double", "challenging"))
    values = tuple(max(0, 1000 - 20 * abs(i - 140), 1200 - 24 * abs(i - 280))
                   for i in range(1000))
    cases.append(Case("double_nearby_recovery", values, "double", "challenging"))
    cases.append(Case("flat_n400", (12345,) * 400, "flat", "challenging"))
    cases.append(Case("flat_n1000", (12345,) * 1000, "flat", "challenging"))
    cases.append(Case("all_zero_n400", (0,) * 400, "flat", "challenging"))
    central_tie = tuple(max(0, 100000 - 1000 * min(abs(i - 199), abs(i - 200)))
                        for i in range(400))
    cases.append(Case("central_tie_199_200_n400", central_tie, "tie", "challenging"))
    int_max = 2**31 - 1
    values = tuple(max(0, int_max - (i - 321)**2 * 10000) for i in range(600))
    cases.append(Case("int_max_peak_n600_p321", values, "integer_range"))
    cases.append(Case("strictly_increasing_n1000",
                      tuple(i * (int_max // 999) for i in range(1000)), "monotone"))
    cases.append(Case("strictly_decreasing_n400",
                      tuple((399 - i) * (int_max // 399) for i in range(400)), "monotone"))
    for peak in (0, 337, 999):
        values = [100] * 1000
        values[peak] = 2000000000
        cases.append(Case(f"spike_n1000_p{peak}", tuple(values), "spike", "challenging"))

    if suite == "extended":
        for number in range(36):
            n = rng.randint(400, 1000)
            peak = rng.randrange(n)
            width = rng.uniform(10, n / 6)
            values = gaussian(n, peak, width)
            cases.append(Case(f"smooth_random_{number:02d}_n{n}_p{peak}",
                              tuple(values), "smooth"))
        for number in range(18):
            n = rng.randint(400, 1000)
            peak = rng.randrange(n)
            width = rng.uniform(20, n / 5)
            amplitude = rng.choice((1000, 20000, 1000000))
            noise = rng.randint(1, max(1, amplitude // 20))
            values = [max(0, v + rng.randint(-noise, noise))
                      for v in gaussian(n, peak, width, amplitude)]
            cases.append(Case(f"noise_random_{number:02d}_n{n}_p{peak}",
                              tuple(values), "noise", "challenging"))
        for number in range(8):
            n = rng.randint(400, 1000)
            values = [rng.randrange(1000) for _ in range(n)]
            cases.append(Case(f"unstructured_{number:02d}_n{n}", tuple(values),
                              "unstructured", "challenging"))
    return cases


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--program", nargs="+", help="executable and optional positional arguments; .py files also work")
    parser.add_argument("--program-arg", action="append", default=[], help="append a solver argument (use = for arguments starting with -)")
    parser.add_argument("--suite", choices=("smoke", "extended"), default="smoke")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--timeout", type=float, default=10.0, help="total seconds per case, at most 10")
    parser.add_argument("--case", help="run case names containing this text")
    parser.add_argument("--list-cases", action="store_true")
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args(argv)
    if not 0 < args.timeout <= 10:
        parser.error("--timeout must be in (0, 10]")
    cases = make_suite(args.suite, args.seed)
    if args.case:
        cases = [case for case in cases if args.case in case.name]
    if not cases:
        parser.error("no matching cases")
    if args.list_cases:
        for case in cases:
            print(f"{case.name:<42} N={len(case.values):4} target={case.target:4} "
                  f"{case.family:<13} {case.difficulty}")
        return 0
    if not args.program:
        parser.error("--program is required unless --list-cases is used")
    command = args.program + args.program_arg
    if Path(command[0]).suffix.lower() == ".py":
        command.insert(0, sys.executable)
    elif Path(command[0]).is_file():
        command[0] = str(Path(command[0]).resolve())
    print("Synthetic development curves; challenging cases have no guaranteed score.")
    print(f"{'case':<42} {'group':<11} {'score':>5} {'q':>3} {'travel':>6} "
          f"{'osc':>3} {'red':>4} {'d':>4} status", flush=True)
    results = []
    for case in cases:
        result = run_case(command, case, args.timeout)
        results.append(result)
        print(f"{case.name:<42} {case.difficulty:<11} {result['score']:5} "
              f"{result['queries']:3} {result['travel']:6} "
              f"{result['oscillations']:3} {result['redundancy']:4} "
              f"{result['distance']:4} {result['status']}", flush=True)
        if result["error"]:
            print(f"  ERROR: {result['error']}", flush=True)
    summaries = {}
    for group in ("standard", "challenging"):
        group_results = [r for r in results if r["difficulty"] == group]
        if group_results:
            summaries[group] = {"cases": len(group_results),
                                "total_score": sum(r["score"] for r in group_results),
                                "zero_scores": sum(r["score"] == 0 for r in group_results),
                                "errors": sum(r["status"] != "ok" for r in group_results)}
            summary = summaries[group]
            print(f"{group}: {summary['cases']} cases, score={summary['total_score']}, "
                  f"zero_scores={summary['zero_scores']}, errors={summary['errors']}")
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps({"suite": args.suite, "seed": args.seed,
                                                "command": command, "summary": summaries,
                                                "results": results}, indent=2,
                                               ensure_ascii=False), encoding="utf-8")
    return int(any(r["status"] != "ok" for r in results))


if __name__ == "__main__":
    raise SystemExit(main())
