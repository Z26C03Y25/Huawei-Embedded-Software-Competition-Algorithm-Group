"""Offline CLI safety contracts: fake page/clock, no Chrome or network access."""

from contextlib import redirect_stderr, redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from online_judge import judge
from online_judge.jobs import JobStore
from online_judge.records import parse_submission_html


ROOT = Path(__file__).resolve().parents[3]


def row(second=0, *, score="154353", status="success", filename="main.cpp"):
    return f"""<tr data-rowid="temporary_{second}">
      <td data-colid="col_1">{filename}</td>
      <td data-colid="col_2">C++</td>
      <td data-colid="col_3">2026-10-24 19:00:{second:02d}</td>
      <td data-colid="col_6"><span class="{status}">{status}</span></td>
      <td data-colid="col_7"><span class="scoringBox">{score}</span></td>
    </tr>"""


def table(*rows):
    return '<table class="tiny-grid__body"><tbody>' + "".join(rows) + "</tbody></table>"


class FakeClock:
    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        if seconds <= 0:
            raise AssertionError("Polling must make forward progress")
        self.sleeps.append(seconds)
        self.now += seconds


class FakePage:
    def __init__(self, frames, *, on_table=None, on_upload=None):
        if not frames:
            raise ValueError("Supply at least one fake table frame")
        self.frames = list(frames)
        self.on_table = on_table
        self.on_upload = on_upload
        self.table_calls = []
        self.upload_calls = []

    def table_html(self, *, refresh=False):
        index = len(self.table_calls)
        self.table_calls.append(refresh)
        if self.on_table:
            self.on_table(index)
        return self.frames[min(index, len(self.frames) - 1)]

    def upload(self, snapshot):
        snapshot = Path(snapshot)
        self.upload_calls.append(snapshot)
        if self.on_upload:
            self.on_upload(snapshot)


class FakeConnection:
    def __init__(self, page):
        self.page = page

    def __enter__(self):
        return self.page

    def __exit__(self, *unused):
        return False


class CliTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "dev/tmp"
        scratch.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="online_cli_", dir=scratch)
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.store = JobStore(self.directory / "runs")
        self.source = self.directory / "working source.cpp"
        self.original = b"\xef\xbb\xbf// frozen original\r\nint main() { return 0; }\r\n"
        self.source.write_bytes(self.original)
        self.config = {"runs_directory": str(self.store.root),
                       "submission_url": "https://developer.huaweicloud.com/competition/information/1300000312/submission",
                       "profile_directory": str(self.directory / "fake-profile"),
                       "timeout_seconds": 5, "poll_interval_seconds": 1}
        self.old_html = table(row())

    def invoke(self, arguments, page=None):
        output, errors = StringIO(), StringIO()
        clock = FakeClock()
        with mock.patch.object(judge, "load_config", return_value=dict(self.config)), \
                mock.patch.object(judge, "connect", return_value=FakeConnection(page)) as connect, \
                mock.patch.object(judge, "time", clock), \
                redirect_stdout(output), redirect_stderr(errors):
            code = judge.main(arguments)
        return code, json.loads(output.getvalue()), connect, clock, errors.getvalue()

    def create_job(self, *, state="delivery_uncertain"):
        job = self.store.create(self.source, parse_submission_html(self.old_html))
        job["state"] = state
        self.store.save(job)
        return job

    def assert_no_upload(self, page):
        self.assertEqual(page.upload_calls, [], "Read/resume paths must never upload")

    def test_first_submit_uploads_frozen_bytes_once_after_uncertain_state_is_saved(self):
        observed = []

        def upload(snapshot):
            saved = self.store.load(snapshot.parent.name)
            observed.append(saved)
            self.assertEqual(saved["state"], "delivery_uncertain")
            self.assertTrue(saved["submission_attempt_at"])
            self.assertEqual(snapshot.name, "main.cpp")
            self.assertNotEqual(snapshot, self.source)
            self.assertEqual(snapshot.read_bytes(), self.original)
            self.assertEqual(saved["sha256"], hashlib.sha256(self.original).hexdigest())

        page = FakePage([self.old_html], on_upload=upload)
        code, result, connect, clock, _ = self.invoke(
            ["submit", "--file", str(self.source), "--no-wait"], page)
        self.assertEqual(code, 2)
        self.assertEqual(len(page.upload_calls), 1)
        self.assertEqual(len(observed), 1)
        self.assertEqual(connect.call_count, 1)
        self.assertEqual(clock.sleeps, [])
        self.assertEqual(result["state"], "delivery_uncertain")
        self.assertTrue(self.store.load(result["job_id"])["upload_action_finished"])

    def test_upload_exception_is_not_retried_and_second_submit_resumes_same_job(self):
        def broken_upload(snapshot):
            self.assertEqual(self.store.load(snapshot.parent.name)["state"], "delivery_uncertain")
            raise RuntimeError("connection lost after selecting the file")

        first = FakePage([self.old_html], on_upload=broken_upload)
        code, result, _, _, _ = self.invoke(
            ["submit", "--file", str(self.source), "--no-wait"], first)
        self.assertEqual(code, 2)
        self.assertEqual(len(first.upload_calls), 1)
        saved = self.store.load(result["job_id"])
        self.assertEqual(saved["state"], "delivery_uncertain")
        self.assertIn("Upload outcome uncertain", saved["last_error"])

        pending = table(row(1, score="0", status="pending"), row())
        final = table(row(1, score="145904"), row())
        resumed = FakePage([pending, final, final])
        code, completed, _, _, stderr = self.invoke(
            ["submit", "--file", str(self.source)], resumed)
        self.assertEqual(code, 0)
        self.assertEqual(completed["job_id"], result["job_id"])
        self.assertEqual(completed["score"], 145904)
        self.assertIn("no second upload", stderr)
        self.assert_no_upload(resumed)
        self.assertEqual(len(list(self.store.root.glob("*/job.json"))), 1)

    def test_existing_pending_same_hash_submit_resumes_wait_without_upload(self):
        job = self.create_job(state="pending")
        final = table(row(1, score="145904"), row())
        page = FakePage([final, final])
        code, result, _, _, _ = self.invoke(["submit", "--file", str(self.source)], page)
        self.assertEqual(code, 0)
        self.assertEqual(result["job_id"], job["job_id"])
        self.assertEqual(result["score"], 145904)
        self.assertEqual(len(page.table_calls), 2)
        self.assert_no_upload(page)

    def test_snapshot_ready_same_hash_can_make_its_first_upload(self):
        job = self.create_job(state="snapshot_ready")
        page = FakePage([self.old_html])
        code, result, _, _, _ = self.invoke(
            ["submit", "--file", str(self.source), "--no-wait"], page)
        self.assertEqual(code, 2)
        self.assertEqual(result["job_id"], job["job_id"])
        self.assertEqual(page.upload_calls, [Path(job["snapshot_path"])])
        self.assertEqual(len(list(self.store.root.glob("*/job.json"))), 1)

    def test_other_hash_pending_job_blocks_new_upload_before_connecting(self):
        self.create_job(state="pending")
        self.source.write_bytes(b"// different source fingerprint\n")
        page = FakePage([self.old_html])
        code, result, connect, _, _ = self.invoke(
            ["submit", "--file", str(self.source), "--no-wait"], page)
        self.assertEqual(code, 5)
        self.assertIn("unfinished", result["error"])
        connect.assert_not_called()
        self.assert_no_upload(page)

    def test_completed_same_hash_is_reused_without_a_browser_or_repeat_upload(self):
        job = self.create_job(state="completed")
        job["score"] = 145904
        self.store.save(job)
        code, result, connect, _, _ = self.invoke(["submit", "--file", str(self.source)])
        self.assertEqual(code, 0)
        self.assertEqual(result["job_id"], job["job_id"])
        self.assertEqual(result["score"], 145904)
        self.assertTrue(result["reused"])
        connect.assert_not_called()

    def test_explicit_repeat_creates_exactly_one_new_upload_after_completed_job(self):
        job = self.create_job(state="completed")
        job["score"] = 145904
        self.store.save(job)
        page = FakePage([self.old_html])
        code, result, _, _, _ = self.invoke(
            ["submit", "--file", str(self.source), "--repeat", "--no-wait"], page)
        self.assertEqual(code, 2)
        self.assertNotEqual(result["job_id"], job["job_id"])
        self.assertEqual(len(page.upload_calls), 1)
        self.assertEqual(len(list(self.store.root.glob("*/job.json"))), 2)

    def test_wait_timeout_keeps_job_and_pending_zero_is_not_a_final_zero(self):
        job = self.create_job()
        page = FakePage([table(row(1, score="0", status="pending"), row())])
        code, result, _, clock, _ = self.invoke(["wait", job["job_id"]], page)
        self.assertEqual(code, 2)
        self.assertEqual(result["state"], "timed_out")
        self.assertIsNone(result["score"])
        self.assertIn(job["job_id"], result["resume"])
        saved = self.store.load(job["job_id"])
        self.assertEqual(saved["state"], "timed_out")
        self.assertIsNone(saved["score"])
        self.assertEqual(saved["bound_identity"], ["main.cpp", "2026-10-24 19:00:01"])
        self.assertEqual(Path(saved["snapshot_path"]).read_bytes(), self.original)
        self.assertEqual(sum(clock.sleeps), 5)
        self.assert_no_upload(page)

    def test_latest_html_reads_first_145904_instead_of_larger_154353(self):
        html = self.directory / "history.html"
        html.write_text(table(row(2, score="145904"), row(1, score="154353")), encoding="utf-8")
        code, result, connect, _, _ = self.invoke(["latest", "--html", str(html)])
        self.assertEqual(code, 0)
        self.assertEqual(result["score"], 145904)
        self.assertEqual(result["submitted_at"], "2026-10-24 19:00:02")
        connect.assert_not_called()

    def test_history_html_retains_displayed_order_without_browser(self):
        html = self.directory / "history.html"
        html.write_text(table(row(2, score="145904"), row(1, score="154353")), encoding="utf-8")
        code, result, connect, _, _ = self.invoke(["history", "--html", str(html)])
        self.assertEqual(code, 0)
        self.assertEqual([record["score"] for record in result], [145904, 154353])
        connect.assert_not_called()

    def test_success_zero_requires_two_identical_terminal_observations(self):
        job = self.create_job()

        def check_before_second_read(index):
            if index == 1:
                saved = self.store.load(job["job_id"])
                self.assertEqual(saved["state"], "pending")
                self.assertIsNone(saved["score"])

        final = table(row(1, score="0"), row())
        page = FakePage([final, final], on_table=check_before_second_read)
        code, result, _, clock, _ = self.invoke(["wait", job["job_id"]], page)
        self.assertEqual(code, 0)
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["state"], "completed")
        self.assertEqual(len(page.table_calls), 2)
        self.assertEqual(clock.sleeps, [1])
        self.assert_no_upload(page)

    def test_success_zero_then_145904_waits_for_positive_score_to_stabilize(self):
        job = self.create_job()
        zero = table(row(1, score="0"), row())
        final = table(row(1, score="145904"), row())
        page = FakePage([zero, final, final])
        code, result, _, clock, _ = self.invoke(["wait", job["job_id"]], page)
        self.assertEqual(code, 0)
        self.assertEqual(result["score"], 145904)
        self.assertEqual(len(page.table_calls), 3)
        self.assertEqual(clock.sleeps, [1, 1])
        self.assert_no_upload(page)

    def test_bound_submission_is_followed_after_becoming_second_row(self):
        job = self.create_job()
        pending = table(row(1, score="0", status="pending"), row())
        moved = table(row(2, score="999999"), row(1, score="145904"), row())
        page = FakePage([pending, moved, moved])
        code, result, _, _, _ = self.invoke(["wait", job["job_id"]], page)
        self.assertEqual(code, 0)
        self.assertEqual(result["score"], 145904)
        self.assertEqual(result["record"]["submitted_at"], "2026-10-24 19:00:01")
        self.assertEqual(len(page.table_calls), 3)
        self.assert_no_upload(page)

    def test_edit_during_baseline_read_cannot_change_uploaded_snapshot(self):
        changed = b"// a later edit made while the browser reads baseline\n"

        def edit_source(index):
            self.assertEqual(index, 0)
            self.source.write_bytes(changed)

        def inspect_upload(snapshot):
            self.assertEqual(snapshot.read_bytes(), self.original)
            saved = self.store.load(snapshot.parent.name)
            self.assertEqual(saved["sha256"], hashlib.sha256(self.original).hexdigest())

        page = FakePage([self.old_html], on_table=edit_source, on_upload=inspect_upload)
        code, result, _, _, _ = self.invoke(
            ["submit", "--file", str(self.source), "--no-wait"], page)
        self.assertEqual(code, 2)
        self.assertEqual(len(page.upload_calls), 1)
        self.assertEqual(self.source.read_bytes(), changed)
        self.assertEqual(Path(result["snapshot_path"]).read_bytes(), self.original)

    def test_wait_does_not_reuse_old_completed_row_or_its_score(self):
        job = self.create_job()
        page = FakePage([self.old_html])
        code, result, _, _, _ = self.invoke(["wait", job["job_id"]], page)
        self.assertEqual(code, 2)
        self.assertIsNone(result["score"])
        self.assertIsNone(self.store.load(job["job_id"])["bound_identity"])
        self.assert_no_upload(page)

    def test_pending_baseline_prevents_a_new_upload(self):
        page = FakePage([table(row(1, score="0", status="pending"), row())])
        code, result, _, _, _ = self.invoke(
            ["submit", "--file", str(self.source), "--no-wait"], page)
        self.assertEqual(code, 5)
        self.assertIn("pending", result["error"])
        self.assert_no_upload(page)
        self.assertEqual(list(self.store.root.glob("*/job.json")), [])

    def ranking_snapshot(self):
        from online_judge.ranking import first_page_snapshot, parse_ranking_response
        return first_page_snapshot(parse_ranking_response({
            "total": 50, "stage_name": "test", "refresh_time": "2026-10-24 23:50:00",
            "team_ranking_list": [{"ranking": 1, "team_name": "leader", "score": 219559}],
            "current_team_ranking": []}))

    def test_ranking_command_reads_first_page_without_submission_connection_or_job(self):
        with mock.patch.object(judge, "get_ranking", return_value=(self.ranking_snapshot(), {"cache_hit": True})):
            code, result, connect, _, _ = self.invoke([
                "ranking", "--output-dir", str(self.directory/"ranking")])
        self.assertEqual(code, 0)
        self.assertFalse(result["complete"])
        self.assertTrue(result["files"]["cache_hit"])
        self.assertEqual(result["leader"]["score"], 219559)
        self.assertTrue(Path(result["files"]["snapshot_path"]).is_file())
        connect.assert_not_called()
        self.assertEqual(list(self.store.root.glob("*/job.json")), [])

    def test_ranking_capture_only_after_two_confirmed_scores_and_never_uploads(self):
        self.config["capture_ranking_on_completion"] = True
        job = self.create_job()
        final = table(row(1, score="199291"), row())
        page = FakePage([final, final])

        def collect(*args, **kwargs):
            self.assertEqual(len(page.table_calls), 2)
            self.assertEqual(self.store.load(job["job_id"])["state"], "completed")
            return self.ranking_snapshot(), {}

        with mock.patch.object(judge, "get_ranking", side_effect=collect) as capture:
            code, result, _, _, _ = self.invoke(["wait", job["job_id"]], page)
        self.assertEqual(code, 0)
        self.assertEqual(result["score"], 199291)
        self.assertEqual(result["ranking_after"]["gap_from_submission_to_leader"], 20268)
        self.assertEqual(capture.call_count, 1)
        self.assert_no_upload(page)

    def test_failed_ranking_read_preserves_confirmed_score_and_cannot_reupload(self):
        self.config["capture_ranking_on_completion"] = True
        job = self.create_job()
        final = table(row(1, score="199291"), row())
        page = FakePage([final, final])
        with mock.patch.object(judge, "get_ranking", side_effect=RuntimeError("private response")):
            code, result, _, _, _ = self.invoke(["wait", job["job_id"]], page)
        self.assertEqual(code, 0)
        self.assertEqual(result["score"], 199291)
        self.assertEqual(result["state"], "completed")
        self.assertNotIn("private response", result["ranking_error"])
        self.assert_no_upload(page)


if __name__ == "__main__":
    unittest.main()
