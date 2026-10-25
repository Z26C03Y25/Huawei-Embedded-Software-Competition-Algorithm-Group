"""Protect immutable scored archives and validate core interaction behavior.

The entry point currently matches the recorded 199291 archive. New experiments
must preserve graded bytes; synthetic checks do not reproduce official scores.

Protocol/parking checks run against the current entry point and both scored
archives. The wide-summit and late-peak checks belong specifically to v2: their
synthetic improvements must not require replacing a higher official-score v1.
Synthetic scores do not predict the official score or guarantee arbitrary peaks.
"""

from pathlib import Path
import hashlib
import os
import random
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev"))
from tools.local_judge import Case, PDF_SAMPLE, run_case


SCORED_VERSIONS = {
    "v1_154353": (ROOT / "data/versions" / "main_v1_154353.cpp", 154353,
                  "7d0e2319335d2eabe1e48a453f84579079c8c538e4b0ac8b3f43379e1b1f7b74"),
    "v2_145904": (ROOT / "data/versions" / "main_v2_145904.cpp", 145904,
                  "39ab2920c8317a44c1015182914b139673ba131abe818382ed28dbef51d955c4"),
    "strategy_159487": (ROOT / "data/versions" / "main_strategy_159487.cpp", 159487,
                       "d98855c0f56b0c302f939252804ac8e7b38080e39bd06d43014020f1a8877336"),
    "trend_153592": (ROOT / "data/versions" / "main_trend_153592.cpp", 153592,
                     "71ac5e827f6631d2e5ca00df353d4734109f0e17a40570b7f584f0b1c7eb596c"),
    "online_199291": (ROOT / "data/versions" / "main_online_199291.cpp", 199291,
                      "fcd7096e113824a46532ead285299368507cc8ca3594dc9d9457e83ca9c31f82"),
}


class SubmissionSourceSelectionTests(unittest.TestCase):
    def test_scored_archives_are_the_exact_graded_source_bytes(self):
        for version, (source, score, expected_digest) in SCORED_VERSIONS.items():
            with self.subTest(version=version, official_score=score):
                self.assertTrue(source.is_file(), f"Missing immutable scored archive: {source}")
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), expected_digest,
                                 "An officially scored archive must not be edited in place")

    def test_pre_strategy_source_is_preserved_exactly(self):
        source = ROOT / "data/versions" / "main_before_strategy.cpp"
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),
                         "b0b2ff0bb4885dd0ed554782c0565476bba1803604d8128a68487f69e28b67dc")


class SolverRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which("g++")
        if compiler is None:
            raise unittest.SkipTest("C++ solver regressions require g++ on PATH")
        build = ROOT / "dev/build"
        build.mkdir(exist_ok=True)
        cls.solvers = {}
        compiled_by_digest = {}
        sources = {"current": ROOT / "main.cpp",
                   **{version: data[0] for version, data in SCORED_VERSIONS.items()}}
        for version, source in sources.items():
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            if digest not in compiled_by_digest:
                executable = build / (f"test_solver_{digest[:12]}" + (".exe" if os.name == "nt" else ""))
                compiled = subprocess.run(
                    [compiler, "-O3", "-Wall", "-std=c++17", str(source), "-o", str(executable)],
                    cwd=ROOT, capture_output=True, text=True, errors="replace", timeout=60,
                )
                if compiled.returncode:
                    raise RuntimeError(f"{source.name} failed to compile:\n" + compiled.stdout + compiled.stderr)
                compiled_by_digest[digest] = executable
            cls.solvers[version] = compiled_by_digest[digest]

    def run_solver(self, name, values, *, version="current"):
        case = Case(name, tuple(values))
        result = run_case([str(self.solvers[version])], case)
        result["solver_version"] = version
        self.assertEqual(result["status"], "ok", result)
        self.assertIsNone(result["error"], result)
        self.assertGreater(result["queries"], 0, result)
        self.assertLessEqual(result["queries"], 199, result)
        self.assertLess(result["oscillations"], 7, result)
        if version in {"v1_154353", "v2_145904"}:
            # The archived algorithms explicitly promised at most two turns.
            # A future higher-scoring main can use any legal trajectory.
            self.assertLessEqual(result["oscillations"], 2, result)
        self.assertEqual(result["messages"], result["queries"] + 1, result)

        # A cached value does not park the motor: the last real query must be
        # the best raw observation, using the statement's full tie rule.
        observed = set(result["query_positions"])
        expected = min(observed, key=lambda i: (
            -case.values[i], abs(2 * i - (len(case.values) - 1)), i))
        self.assertEqual(result["final_position"], expected, result)
        return case, result

    def assert_exact_positive(self, name, values, *, version="current"):
        case, result = self.run_solver(name, values, version=version)
        self.assertEqual(result["final_position"], case.target, result)
        self.assertEqual(result["distance"], 0, result)
        self.assertLess(result["redundancy"], 200, result)
        self.assertGreater(result["score"], 0, result)
        return result

    def test_wide_summit_searches_beyond_three_coarse_hotspots(self):
        values = [0] * 1000
        values[200:361] = [10000] * 161
        for index, value in ((224, 10090), (248, 10089), (272, 10088),
                             (347, 10100)):
            values[index] = value
        self.assert_exact_positive("wide_summit_raw_max_347", values, version="v2_145904")

    def test_wide_summit_keeps_redundancy_safe_for_earlier_raw_peak(self):
        values = [0] * 1000
        values[200:401] = [10000] * 201
        values[201] = 10100
        values[336] = 10090
        self.assert_exact_positive("wide_summit_raw_max_201", values, version="v2_145904")

    def test_late_narrow_peak_after_long_zero_baseline(self):
        values = [max(0, 1800 - 100 * abs(i - 900)) for i in range(1000)]
        self.assert_exact_positive("late_peak_900", values, version="v2_145904")

    def test_single_position_handles_zero_and_int_max(self):
        for version in self.solvers:
            for value in (0, 2**31 - 1):
                with self.subTest(version=version, value=value):
                    result = self.assert_exact_positive("single_position", [value], version=version)
                    self.assertEqual(result["queries"], 1, result)

    def test_pdf_sample_is_scanned_and_parked_exactly(self):
        for version in self.solvers:
            with self.subTest(version=version):
                result = self.assert_exact_positive("pdf_sample_12", PDF_SAMPLE, version=version)
                self.assertEqual(set(result["query_positions"]), set(range(12)))

    def test_198_positions_scan_int_max_ties_and_reserve_parking_query(self):
        values = [0] * 198
        for index in (0, 98, 99, 197):
            values[index] = 2**31 - 1
        for version in self.solvers:
            with self.subTest(version=version):
                result = self.assert_exact_positive("small_int_max_ties", values, version=version)
                self.assertEqual(result["final_position"], 98, result)
                self.assertEqual(set(result["query_positions"]), set(range(198)))
                self.assertEqual(result["queries"], 199, result)

    def test_constant_curve_parks_at_lower_central_position(self):
        # Long plateaus need correct central tie handling. Their score is not
        # constrained here: the finite-query heuristic may overshoot the peak.
        for version in self.solvers:
            with self.subTest(version=version):
                case, result = self.run_solver("constant_1000", [12345] * 1000, version=version)
                self.assertEqual(result["final_position"], case.target, result)
                self.assertEqual(result["final_position"], 499, result)

    def test_arbitrary_curves_preserve_protocol_budget_and_observed_best(self):
        for version in self.solvers:
            for length in (400, 547, 700, 999, 1000):
                for seed in (5, 29):
                    with self.subTest(version=version, length=length, seed=seed):
                        rng = random.Random(seed * 10000 + length)
                        # Low-cardinality odd lengths deliberately create many
                        # equal raw maxima; the other lengths cover int32 values.
                        upper = 8 if length % 2 else 2**31
                        values = [rng.randrange(upper) for _ in range(length)]
                        self.run_solver(f"arbitrary_n{length}_s{seed}", values, version=version)


if __name__ == "__main__":
    unittest.main()
