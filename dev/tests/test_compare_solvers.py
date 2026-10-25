"""Generator diversity, fair summaries, reproduction and pipe-based comparison."""

from collections import Counter
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.compare_solvers import (BenchmarkCase, FAMILIES, INFORMATION_LIMITED, MODELS,
                                   compare_results, decode_cases, describe_cases,
                                   evaluate_programs, make_benchmark, parse_programs,
                                   peak_profile, summarize)
from tools.local_judge import Case, PDF_SAMPLE


class GeneratorTests(unittest.TestCase):
    def test_reproducible_prefix_and_distinct_seeds(self):
        cases = make_benchmark(4, 35)
        self.assertEqual(cases, make_benchmark(4, 35))
        self.assertEqual(cases, make_benchmark(4, 40)[:35])
        self.assertNotEqual(cases, make_benchmark(5, 35))
        with self.assertRaises(ValueError):
            make_benchmark(4, 0)

    def test_families_are_balanced_and_majority_non_gaussian(self):
        cases = make_benchmark(2026, 144)
        counts = Counter(item.case.family for item in cases)
        self.assertEqual(set(counts), set(FAMILIES))
        self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)
        self.assertGreaterEqual(sum("gaussian" not in item.metadata["models"] for item in cases), 72)
        for item in cases:
            self.assertTrue(400 <= len(item.case.values) <= 1000)
            self.assertTrue(all(0 <= value <= 2**31 - 1 for value in item.case.values))
            expected = "information_limited" if item.case.family in INFORMATION_LIMITED else "structured"
            self.assertEqual(item.case.difficulty, expected)

    def test_profiles_peak_at_center_and_are_bounded(self):
        for model in MODELS:
            with self.subTest(model=model):
                self.assertEqual(peak_profile(50, 50, 10, model), 1.0)
                self.assertTrue(all(0 <= peak_profile(i, 50, 10, model) <= 1 for i in range(100)))

    def test_each_variable_family_visits_all_profile_models(self):
        cases = make_benchmark(91, len(FAMILIES) * len(MODELS))
        for family in ("unimodal", "near_double", "far_double", "narrow_peak",
                       "left_boundary", "right_boundary", "rippled_peak"):
            with self.subTest(family=family):
                used = {item.metadata["models"][0] for item in cases if item.case.family == family}
                self.assertEqual(used, set(MODELS))

    def test_json_roundtrip_preserves_full_curves_and_metadata(self):
        cases = make_benchmark(123, 28)
        payload = json.loads(json.dumps({"cases": describe_cases(cases)}))
        self.assertEqual(decode_cases(payload), cases)
        payload["cases"].append(payload["cases"][0])
        with self.assertRaises(ValueError):
            decode_cases(payload)


def result(name, family, score, group="structured", distance=0, status="ok"):
    return {"name": name, "family": family, "difficulty": group, "score": score,
            "distance": distance, "status": status, "queries": 10, "travel": 100}


class ComparisonTests(unittest.TestCase):
    def test_information_limited_scores_excluded_and_macro_weights_families(self):
        rows = [result("a", "one", 1000), result("b", "one", 3000),
                result("c", "two", 0), result("d", "random_unstructured", 3000, "information_limited")]
        summary = summarize(rows)
        structured = summary["groups"]["structured"]
        self.assertEqual(structured["cases"], 3)
        self.assertEqual(structured["total_score"], 4000)
        self.assertAlmostEqual(structured["mean_score"], 4000 / 3)
        self.assertEqual(structured["family_macro_mean_score"], 1000)
        self.assertEqual(structured["zero_scores"], 1)
        self.assertEqual(summary["groups"]["information_limited"]["total_score"], 3000)

    def test_paired_comparison_detects_regressions_by_identity(self):
        before = [result("a", "one", 0), result("b", "one", 2000), result("c", "two", 1000)]
        after = [result("c", "two", 1000), result("b", "one", 0), result("a", "one", 2500)]
        compared = compare_results(before, after)
        summary = compared["groups"]["structured"]
        self.assertEqual(summary["score_delta"], 500)
        self.assertEqual((summary["wins"], summary["ties"], summary["losses"]), (1, 1, 1))
        self.assertEqual(summary["resolved_zero_scores"], 1)
        self.assertEqual(summary["new_zero_scores"], 1)
        self.assertEqual(compared["case_deltas"][0]["name"], "b")
        with self.assertRaises(ValueError):
            compare_results(before, after[:-1])

    def test_existing_runner_keeps_observed_values_and_query_trajectory(self):
        source = """input()
for i in [1,4,6,5,4]:
    print(i, flush=True)
    input()
print('DONE', flush=True)
"""
        case = BenchmarkCase(Case("sample", PDF_SAMPLE, "sample", "structured"), {})
        programs = {"first": [sys.executable, "-c", source], "second": [sys.executable, "-c", source]}
        results = evaluate_programs([case], programs, timeout=3)
        for name in programs:
            row = results[name][0]
            self.assertEqual(row["status"], "ok", row)
            self.assertEqual(row["score"], 2984)
            self.assertEqual(row["query_positions"], [1, 4, 6, 5, 4])
            self.assertEqual(row["query_values"], [14, 17, 10, 12, 17])
        self.assertEqual(compare_results(results["first"], results["second"])
                         ["groups"]["structured"]["score_delta"], 0)

    def test_program_paths_validate_and_hash(self):
        path = Path(__file__).resolve()
        programs, artifacts = parse_programs([f"stub={path}"])
        self.assertEqual(programs["stub"], [sys.executable, str(path)])
        self.assertEqual(len(artifacts["stub"]["sha256"]), 64)
        with self.assertRaises(ValueError):
            parse_programs([f"stub={path}", f"stub={path}"])
        with self.assertRaises(ValueError):
            parse_programs(["not_a_name_path_pair"])


if __name__ == "__main__":
    unittest.main()
