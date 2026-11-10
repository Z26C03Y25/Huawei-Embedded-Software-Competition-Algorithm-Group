"""Offline controller recovery, budget and immutable-archive checks; no browser."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import online_round_20261030 as module


class OnlineRoundTests(unittest.TestCase):
    def setUp(self):
        workspace_temp = Path(__file__).resolve().parents[1] / "build/controller_tests"
        workspace_temp.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=workspace_temp)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.original = b"int main(){return 0;}\n"
        (self.root / "main.cpp").write_bytes(self.original)
        module.save(self.root / "data/versions/online_search/results.json", [
            dict(job_id="parent", sha256=module.digest(self.original), score=210599)])
        module.save(self.root / "data/versions/manifest.json", dict(recorded_best_score=210599, files=[]))
        self.controller = module.Controller(self.root, dict(submission_url=module.TARGET,
                                                          runs_directory=str(self.root / "runs")))

    def job(self, name, contents, score, failed=False):
        source = self.root / (name + ".cpp")
        source.write_bytes(contents)
        job = self.controller.store.create(source, [])
        job.update(state="failed" if failed else "completed", score=score,
                   submission_attempt_at="2026-10-30T02:15:00+08:00",
                   bound_submission_id=name, record=dict(submitted_at="2026-10-30 02:15:00", submission_id=name))
        self.controller.store.save(job)
        return job

    def test_completed_resume_never_submits_and_tie_keeps_parent(self):
        contents = self.original + b"// tie\n"
        job = self.job("tie", contents, 210599)
        with patch.object(self.controller, "judge", side_effect=AssertionError("No child command permitted")):
            self.assertEqual(self.controller.resume(job["job_id"]), 0)
            self.assertEqual(self.controller.resume(job["job_id"]), 0)
        self.assertEqual((self.root / "main.cpp").read_bytes(), self.original)
        self.assertEqual(len(module.read(self.controller.results_path)), 1)
        self.assertEqual(len(self.controller.delivered()[1]), 1)
        archive = self.root / "data/versions/online_search" / f"scored_210599_{module.digest(contents)[:12]}.cpp"
        self.assertEqual(archive.read_bytes(), contents)

    def test_improvement_promotes_once_and_archives_without_changing_old_bytes(self):
        contents = self.original + b"// better\n"
        job = self.job("better", contents, 211000)
        self.controller.resume(job["job_id"])
        self.controller.resume(job["job_id"])
        self.assertEqual((self.root / "main.cpp").read_bytes(), contents)
        self.assertEqual((self.controller.out / "best.cpp").read_bytes(), contents)
        self.assertEqual((self.controller.out / "initial_best.cpp").read_bytes(), self.original)
        self.assertTrue(module.read(self.controller.results_path)[0]["accepted"])
        self.assertEqual(self.controller.state["best_score"], 211000)
        index = module.read(self.controller.index_path)
        self.assertEqual(len([r for r in index if r.get("job_id") == job["job_id"]]), 1)

    def test_failed_job_consumes_budget_and_keeps_parent(self):
        job = self.job("bad", self.original + b"// failed\n", None, True)
        self.assertEqual(self.controller.resume(job["job_id"]), 3)
        self.assertEqual(len(self.controller.delivered()[1]), 1)
        self.assertEqual((self.root / "main.cpp").read_bytes(), self.original)
        self.assertEqual(len(module.read(self.controller.index_path)), 1)

    def test_static_review_rejects_external_access(self):
        for source in (b'int main(){system("x");}', b'// https://example.com',
                       b'#include <fstream>\n', b'// access_token', b'int main(){getenv("X");}'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                module.candidate_review(source)
        self.assertTrue(module.candidate_review(self.original)["passed"])

    def test_quota_consistency_and_date_fail_closed(self):
        text = "【上传次数】您所在团队当前阶段每日可上传30次作品，团队已经上传\u00a00\u00a0次（0/30）"
        self.assertEqual(module.parse_quota(text)["remaining"], 30)
        with self.assertRaises(RuntimeError):
            module.parse_quota(text.replace("0/30", "1/30"))
        with patch.object(module, "now", return_value="2026-10-31T00:00:00+08:00"), \
                patch.object(module, "connect", side_effect=AssertionError("No browser allowed")):
            with self.assertRaises(RuntimeError):
                self.controller.quota_check()

    def test_local_30_attempt_cap_precedes_browser(self):
        for i in range(30):
            self.job("budget" + str(i), self.original + f"// {i}".encode(), None, True)
        with patch.object(module, "now", return_value="2026-10-30T02:00:00+08:00"), \
                patch.object(module, "connect", side_effect=AssertionError("No browser allowed")):
            with self.assertRaisesRegex(RuntimeError, "budget is exhausted"):
                self.controller.quota_check()

    def test_unknown_submit_is_invoked_only_once_even_when_run_again(self):
        source = self.root / "uncertain.cpp"
        source.write_bytes(self.original + b"// uncertain\n")
        with patch.object(self.controller, "preflight"), patch.object(self.controller, "quota_check", return_value={}), \
                patch.object(module, "now", return_value="2026-10-30T02:00:00+08:00"), \
                patch.object(self.controller, "judge", return_value=(None, None)) as child:
            with self.assertRaisesRegex(RuntimeError, "No unique saved job"):
                self.controller.start("uncertain", source, "offline uncertainty test")
            with self.assertRaisesRegex(RuntimeError, "already has a prepared/uncertain round"):
                self.controller.start("uncertain", source, "offline uncertainty test")
            self.assertEqual(child.call_count, 1)
            self.assertEqual(child.call_args.args[0][0], "submit")
            self.assertIn("--no-wait", child.call_args.args[0])
            self.assertNotIn("--repeat", child.call_args.args[0])

    def test_timed_out_wait_resumes_same_job_without_submit(self):
        job = self.job("waiting", self.original + b"// pending\n", None)
        job["state"] = "pending"
        self.controller.store.save(job)
        calls = []
        def child(args, entry, timeout):
            calls.append(args)
            current = self.controller.store.load(job["job_id"])
            current.update(state="timed_out" if len(calls) == 1 else "completed",
                           score=None if len(calls) == 1 else 210500)
            self.controller.store.save(current)
            return {}, 2 if len(calls) == 1 else 0
        with patch.object(self.controller, "judge", side_effect=child), patch.object(module.time, "sleep"):
            self.assertEqual(self.controller.resume(job["job_id"]), 0)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(args[:2] == ["wait", job["job_id"]] for args in calls))


if __name__ == "__main__":
    unittest.main()
