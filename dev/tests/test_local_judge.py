"""Score boundaries and real pipe protocol tests; run with unittest discover."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.local_judge import Case, PDF_SAMPLE, make_suite, run_case, score_path, target_index


class ScoringTests(unittest.TestCase):
    def test_pdf_sample(self):
        result = score_path(PDF_SAMPLE, [1, 4, 6, 5, 4])
        expected = {"queries": 5, "travel": 8, "search_time": 13,
                    "oscillations": 1, "redundancy": 2, "distance": 0,
                    "final_position": 4, "score": 2984, "zero_reasons": []}
        self.assertEqual(result, expected)

    def test_peak_ties_use_center_then_lower_index(self):
        self.assertEqual(target_index([6, 8, 10, 9, 8, 10, 4, 7, 10, 4]), 5)
        self.assertEqual(target_index([9, 0, 0, 9]), 0)
        self.assertEqual(target_index([7] * 400), 199)
        self.assertEqual(target_index([7] * 401), 200)

    def test_same_position_preserves_direction(self):
        result = score_path([0, 1, 9, 0], [2, 2, 1, 1, 2])
        self.assertEqual(result["travel"], 4)
        self.assertEqual(result["oscillations"], 2)
        self.assertEqual(result["score"], 2989)
        self.assertEqual(score_path([0, 1, 9], [0, 0, 2])["oscillations"], 0)

    def test_distance_penalty_and_cutoff(self):
        values = [100, 0, 0, 0, 0]
        for distance in range(4):
            with self.subTest(distance=distance):
                result = score_path(values, [distance])
                self.assertEqual(result["score"], 3000 - 200 * distance - 1 - 2 * distance)
        self.assertEqual(score_path(values, [4])["score"], 0)

    def test_query_boundary_199_versus_200(self):
        self.assertEqual(score_path([10], [0] * 199)["score"], 2801)
        result = score_path([10], [0] * 200)
        self.assertEqual(result["score"], 0)
        self.assertIn("queries >= 200", result["zero_reasons"])

    def test_redundancy_boundary_199_versus_200(self):
        values = [100] + [0] * 200
        result = score_path(values, [199, 0])
        self.assertEqual(result["redundancy"], 199)
        self.assertEqual(result["score"], 2400)
        result = score_path(values, [200, 0])
        self.assertEqual(result["score"], 0)
        self.assertIn("redundancy >= 200", result["zero_reasons"])

    def test_oscillation_boundary_six_versus_seven(self):
        path = [1, 2, 1, 2, 1, 2, 1, 2]
        six = score_path([0, 10, 0], path)
        seven = score_path([0, 10, 0], path + [1])
        self.assertEqual(six["oscillations"], 6)
        self.assertGreater(six["score"], 0)
        self.assertEqual(seven["oscillations"], 7)
        self.assertEqual(seven["score"], 0)

    def test_elapsed_and_invalid_indices(self):
        self.assertGreater(score_path([1], [0], 10)["score"], 0)
        self.assertEqual(score_path([1], [0], 10.00001)["score"], 0)
        with self.assertRaises(ValueError):
            score_path([1], [1])

    def test_suite_is_reproducible_and_labeled(self):
        smoke = make_suite("smoke", 42)
        extended = make_suite("extended", 42)
        self.assertEqual(smoke, make_suite("smoke", 42))
        self.assertEqual(extended[:len(smoke)], smoke)
        self.assertNotEqual(make_suite("smoke", 43), smoke)
        self.assertEqual(smoke[0].values, PDF_SAMPLE)
        self.assertTrue(all(400 <= len(c.values) <= 1000 for c in extended[1:]))
        self.assertTrue({"smooth", "boundary", "noise", "plateau", "tie", "double",
                         "flat", "spike", "unstructured"} <= {c.family for c in extended})
        self.assertTrue(all(c.difficulty == "challenging" for c in extended
                            if c.family in {"flat", "spike", "double", "unstructured"}))
        by_name = {case.name: case for case in smoke}
        self.assertEqual(max(by_name["int_max_peak_n600_p321"].values), 2**31 - 1)
        self.assertEqual(by_name["central_tie_199_200_n400"].target, 199)
        self.assertEqual(set(by_name["all_zero_n400"].values), {0})
        self.assertEqual(by_name["strictly_increasing_n1000"].target, 999)
        self.assertEqual(by_name["strictly_decreasing_n400"].target, 0)


class ProtocolTests(unittest.TestCase):
    def run_script(self, source, values=PDF_SAMPLE, timeout=3.0):
        return run_case([sys.executable, "-c", source], Case("test", tuple(values)), timeout)

    def test_real_interaction_matches_pdf_sample(self):
        result = self.run_script("""import sys
assert int(input()) == 12
for i, expected in [(1,14),(4,17),(6,10),(5,12),(4,17)]:
    print(i, flush=True)
    assert int(input()) == expected
print('DONE', flush=True)
""")
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["score"], 2984)
        self.assertEqual(result["messages"], 6)
        self.assertEqual(result["query_positions"], [1, 4, 6, 5, 4])

    def test_200_queries_are_legal_zero_but_201_exceed_message_limit(self):
        source = """input()
for _ in range({count}):
    print(0, flush=True)
    input()
print('DONE', flush=True)
"""
        result = self.run_script(source.format(count=200), [10])
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["queries"], 200)
        self.assertEqual(result["messages"], 201)
        self.assertEqual(result["score"], 0)
        result = self.run_script(source.format(count=201), [10])
        self.assertEqual(result["status"], "protocol_error", result)
        self.assertIn("201", result["error"])

    def test_protocol_errors(self):
        invalid_sources = {
            "text": "input(); print('hello', flush=True)",
            "out_of_range": "input(); print(12, flush=True)",
            "negative": "input(); print(-1, flush=True)",
            "non_ascii": "import sys; input(); sys.stdout.buffer.write(b'\\xff\\n'); sys.stdout.flush()",
            "long_line": "input(); print('0'*65, flush=True)",
            "missing_done": "input(); print(0, flush=True); input()",
            "done_without_query": "input(); print('DONE', flush=True)",
            "after_done": "input(); print(0, flush=True); input(); print('DONE\\n0', flush=True)",
            "partial_line": "import sys; input(); sys.stdout.write('0'); sys.stdout.flush()",
            "nonzero_exit": "input(); print(0, flush=True); input(); print('DONE', flush=True); raise SystemExit(2)",
            "blank_line": "input(); print('', flush=True)",
        }
        for label, source in invalid_sources.items():
            with self.subTest(label=label):
                result = self.run_script(source)
                self.assertEqual(result["status"], "protocol_error", result)
                self.assertTrue(result["error"])
                self.assertEqual(result["score"], 0)

    def test_maximum_line_length_crlf_and_stderr(self):
        result = self.run_script("""import sys
input()
print('diagnostic', file=sys.stderr, flush=True)
sys.stdout.buffer.write(b'0'*64 + b'\\r\\n')
sys.stdout.flush()
input()
sys.stdout.buffer.write(b'DONE\\r\\n')
sys.stdout.flush()
""", [10])
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["score"], 2999)
        self.assertIn("diagnostic", result["stderr"])

    def test_timeout_covers_blocked_solver_and_post_done_exit(self):
        for source in ["import time; input(); time.sleep(2)",
                       "import time; input(); print(0, flush=True); input(); print('DONE', flush=True); time.sleep(2)"]:
            with self.subTest(source=source):
                result = self.run_script(source, timeout=0.25)
                self.assertEqual(result["status"], "timeout", result)
                self.assertEqual(result["score"], 0)
                self.assertLess(result["elapsed_seconds"], 1.5)

    def test_launch_failure(self):
        result = run_case([str(Path(__file__).parent / "no_such_af_solver_91872.exe")],
                          Case("test", (1,)))
        self.assertEqual(result["status"], "launch_error")


if __name__ == "__main__":
    unittest.main()
