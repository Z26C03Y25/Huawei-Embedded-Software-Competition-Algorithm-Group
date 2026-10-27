"""Behavioral checks for budgeted operators and irreversible motor trajectories."""
from pathlib import Path
import hashlib
import json
import math
import os
import random
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev"))
from tools.local_judge import Case, run_case


class StrategyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which("g++")
        if not compiler:
            raise unittest.SkipTest("g++ is required")
        digest = hashlib.sha256((ROOT / "main.cpp").read_bytes()).hexdigest()[:12]
        cls.program = ROOT / "dev/build" / ("strategy_test_" + digest + (".exe" if os.name == "nt" else ""))
        cls.program.parent.mkdir(exist_ok=True)
        result = subprocess.run([compiler, "-O3", "-Wall", "-Wextra", "-Wpedantic", "-std=c++17",
                                 str(ROOT / "main.cpp"), "-o", str(cls.program)],
                                capture_output=True, text=True, timeout=60)
        if result.returncode or result.stderr:
            raise RuntimeError(result.stdout + result.stderr)

    def solve(self, name, values, *flags):
        case = Case(name, tuple(values))
        result = run_case([str(self.program), "--trace", *flags], case)
        self.assertEqual(result["status"], "ok", result)
        self.assertIsNone(result["error"], result)
        self.assertLessEqual(result["queries"], 199, result)
        self.assertLessEqual(result["oscillations"], 6, result)
        self.assertEqual(result["messages"], result["queries"] + 1, result)
        positions = result["query_positions"]
        # Re-reading a known point is only needed to park at the final winner.
        self.assertEqual(len(set(positions[:-1])), len(positions[:-1]), result)
        winner = min(set(positions), key=lambda x: (-values[x], abs(2*x-(len(values)-1)), x))
        self.assertEqual(result["final_position"], winner, result)
        line = next(line for line in result["stderr"].splitlines() if line.startswith("TRACE "))
        trace = json.loads(line[6:])
        for actual, recorded in [("queries", "queries"), ("travel", "travel"),
                                 ("oscillations", "oscillations"), ("final_position", "position")]:
            self.assertEqual(result[actual], trace[recorded], result)
        return result, trace

    def exact(self, name, values, *flags):
        result, trace = self.solve(name, values, *flags)
        self.assertEqual(result["distance"], 0, result)
        self.assertLessEqual(result["redundancy"], 199, result)
        self.assertGreater(result["score"], 0, result)
        return result, trace

    def test_disagreeing_vertices_keep_the_rippled_raw_maximum(self):
        path = ROOT / "data/experiments/2026-10-26/counterexamples/model_disagreement_ripple.json"
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        result, _ = self.exact(payload["name"], payload["values"])
        self.assertEqual(result["final_position"], 513)

    def test_multiscale_ripple_does_not_finish_five_grids_early(self):
        path = ROOT / "data/experiments/2026-10-26-B/counterexamples/rippled_early_finish.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        result, _ = self.exact(payload["name"], payload["values"])
        self.assertEqual(result["final_position"], 228)

    def test_constants_stop_at_the_central_tie_without_redundancy_zero(self):
        for n in (400, 401, 700, 999, 1000):
            for v in (0, 12345):
                with self.subTest(n=n, v=v):
                    result, _ = self.exact("constant", [v]*n)
                    self.assertEqual(result["final_position"], (n-1)//2)

    def test_boundary_peaks_and_clean_peaks_do_not_oscillate_per_refinement(self):
        for n, p, width in [(400, 0, 65), (700, 3, 35), (400, 47, 42),
                            (600, 293, 75), (1000, 837, 110), (1000, 999, 130),
                            (700, 696, 35)]:
            with self.subTest(n=n, p=p):
                a = [100+round(1000000*math.exp(-0.5*((i-p)/width)**2)) for i in range(n)]
                result, _ = self.exact("clean", a)
                self.assertLessEqual(result["oscillations"], 4)

    def test_wide_top_fills_beyond_three_ranked_hotspots(self):
        a = [0]*1000
        a[200:361] = [10000]*161
        for p, v in [(224, 10090), (248, 10089), (272, 10088), (347, 10100)]:
            a[p] = v
        self.exact("wide_right", a)

    def test_early_raw_peak_inside_wide_top_retains_redundancy_margin(self):
        a = [0]*1000
        a[200:401] = [10000]*201
        a[201], a[336] = 10100, 10090
        result, trace = self.exact("wide_left", a)
        self.assertIn(201, result["query_positions"])
        # This overflowing candidate pool must exercise actual internal planning.
        for op in ("K01", "K06", *(f"L{i:02d}" for i in range(1, 9))):
            self.assertGreater(trace["operators"].get(op, 0), 0, trace)

    def test_nearby_equal_peaks_apply_the_official_central_tie(self):
        a = [max(0, 1000-20*abs(i-140), 1000-20*abs(i-280)) for i in range(700)]
        result, trace = self.exact("equal_double", a)
        self.assertEqual(result["final_position"], 280)
        self.assertGreater(trace["operators"].get("F01", 0), 0)

    def test_late_flat_mode_recovers_a_peak_past_the_balanced_horizon(self):
        a = [max(0, 1800-100*abs(i-900)) for i in range(1000)]
        default, _ = self.solve("late_balanced", a)
        self.assertEqual(default["score"], 0)  # Documented indistinguishable-history tradeoff.
        result, trace = self.exact("late_exploration", a, "--late-flat")
        self.assertTrue(trace["late_flat"])
        self.assertIn(900, result["query_positions"])

    def test_absolute_value_certificate_stops_before_unnecessary_right_exploration(self):
        result, trace = self.exact("saturated", [2**31-1]*1000)
        self.assertEqual(max(result["query_positions"]), 499)
        self.assertGreater(trace["operators"].get("D07", 0), 0)

    def test_certified_redundancy_mode_handles_adversarial_arrays(self):
        for seed in range(10):
            rng = random.Random(78701+seed)
            n = rng.choice((400, 547, 999, 1000))
            a = [rng.randrange(2**31) for _ in range(n)]
            if seed % 3 == 0:
                a = [0]*n
                a[rng.randrange(n)] = 100
            with self.subTest(seed=seed):
                result, trace = self.solve("certified", a, "--strict-redundancy", "--late-flat")
                self.assertLessEqual(result["redundancy"], 199, result)
                self.assertTrue(trace["strict"])
                self.assertLessEqual(trace["rightmost"], trace["certified_left"]+199)

    def test_mixed_noise_sawtooth_and_plateaus_keep_hard_action_budgets(self):
        for seed in range(16):
            rng = random.Random(991+seed)
            n = rng.randint(400, 1000)
            p = rng.randrange(n)
            if seed % 4 == 0:
                a = [rng.randrange(8) for _ in range(n)]
            elif seed % 4 == 1:
                a = [max(0, 10000-40*abs(i-p))+rng.randrange(1200) for i in range(n)]
            elif seed % 4 == 2:
                a = [1000+(i % 2)*1000 for i in range(n)]
            else:
                a = [max(0, 10000-50*max(abs(i-p)-50, 0)) for i in range(n)]
            with self.subTest(seed=seed):
                self.solve("mixed", a)

    def test_internal_annealing_is_reproducible(self):
        rng = random.Random(567)
        a = [10000+rng.randrange(500) for _ in range(1000)]
        first, trace = self.solve("replay", a)
        second, other = self.solve("replay", a)
        self.assertEqual(first["query_positions"], second["query_positions"])
        self.assertEqual(trace, other)

    def test_variable_monotone_slopes_leave_budget_to_reach_the_boundary(self):
        for seed in range(10):
            rng = random.Random(1801+seed)
            n = rng.randint(700, 1000)
            a, total = [], 0
            for _ in range(n):
                total += rng.randint(1, 20)
                a.append(total*1000)
            with self.subTest(seed=seed):
                result, _ = self.exact("uneven_increasing", a)
                self.assertEqual(result["final_position"], n-1)

    def test_supported_noisy_peak_does_not_require_raw_twelve_sigma_contrast(self):
        for seed in (42, 73, 2026):
            rng = random.Random(seed)
            a = [max(0, round(1000000*(1+math.exp(-0.5*((i-160)/60)**2)+
                                      rng.uniform(-0.2, 0.2)))) for i in range(1000)]
            with self.subTest(seed=seed):
                self.exact("supported_noisy_peak", a)

    def test_flat_horizon_uses_199_without_crossing_the_zero_threshold(self):
        for n in (400, 700, 1000):
            with self.subTest(n=n):
                result, trace = self.exact("flat_budget", [12345]*n)
                self.assertEqual(result["redundancy"], 199)
                self.assertEqual(trace["rightmost"], (n-1)//2+199)


if __name__ == "__main__":
    unittest.main()
