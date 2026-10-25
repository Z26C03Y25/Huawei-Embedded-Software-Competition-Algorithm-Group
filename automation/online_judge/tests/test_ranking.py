"""First-page-only reads, shared request throttling and non-uploading capture."""

from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from online_judge import judge
from online_judge import ranking
from online_judge.ranking import (RankingError, RANKING_API_URL, RANKING_URL,
                                  first_page_snapshot, collect_first_page,
                                  get_ranking, parse_ranking_response, save_ranking)
from online_judge.records import CHINA_TIME


def row(rank, name, score):
    return {"ranking": rank, "team_name": name, "score": score}


def payload(entries=None, *, total=3, refreshed="2026-10-24 23:50:00", current=None):
    return {"total": total, "refresh_time": refreshed, "stage_name": "赛事",
            "team_ranking_list": entries if entries is not None else [row(1, "A", 219559)],
            "current_team_ranking": current if current is not None else [row(2, "B", 199291)]}


def snapshot():
    return first_page_snapshot(parse_ranking_response(payload(
        [row(1, "A", 219559), row(2, "B", 199291), row(3, "C", 0)])))


class Response:
    url, status = RANKING_API_URL, 200
    request = SimpleNamespace(method="POST")

    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


class Event:
    def __init__(self, page, predicate):
        self.page, self.predicate = page, predicate

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    @property
    def value(self):
        response = Response(self.page.frames[self.page.index])
        assert self.predicate(response)
        return response


class Page:
    def __init__(self, frames):
        self.frames, self.index, self.visited = frames, -1, []

    def set_default_timeout(self, timeout):
        pass

    def expect_response(self, predicate, **kwargs):
        return Event(self, predicate)

    def goto(self, url, **kwargs):
        assert url == RANKING_URL
        self.visited.append(url)
        self.index = 0

    def locator(self, selector):
        raise AssertionError("Page-one collection must never use a pagination control")


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.scratch_root = Path(__file__).resolve().parents[3] / "dev/tmp"
        self.scratch_root.mkdir(exist_ok=True)

    def cache_config(self):
        scratch = tempfile.TemporaryDirectory(dir=self.scratch_root)
        self.addCleanup(scratch.cleanup)
        return {"runs_directory": scratch.name}

    def test_whitelists_public_fields_and_converts_refresh_utc_to_china(self):
        data = payload()
        data["team_ranking_list"][0].update(
            user_id="private-user", user_list=[{"domain_name": "private-member"}], cookie="secret")
        parsed = parse_ranking_response(data)
        self.assertEqual(parsed["refreshed_at"], "2026-10-25T07:50:00+08:00")
        self.assertEqual(parsed["entries"], [{"rank": 1, "team_name": "A", "score": 219559}])
        serialized = json.dumps(parsed)
        for private in ("private-user", "private-member", "secret", "user_list", "cookie"):
            self.assertNotIn(private, serialized)

    def test_rejects_authentication_schema_and_invalid_scores(self):
        for status in (401, 403, 500):
            with self.subTest(status=status), self.assertRaises(RankingError):
                parse_ranking_response(payload(), status)
        for value in (None, {}, {"total": 3}, payload([row(1, "A", True)]),
                      payload([row(0, "A", 1)]), payload(refreshed="yesterday")):
            with self.subTest(value=value), self.assertRaises(RankingError):
                parse_ranking_response(value)

    def test_complete_board_gaps_and_zero_scores(self):
        board = snapshot()
        self.assertEqual(board["total"], 3)
        self.assertTrue(board["complete"])
        self.assertEqual(board["gap_to_leader"], 20268)
        self.assertEqual(board["gap_to_next_higher_score"], 20268)
        self.assertEqual(board["entries"][-1]["score"], 0)

    def test_first_page_may_be_partial_but_must_contain_top_rank(self):
        first = parse_ranking_response(payload())
        board = first_page_snapshot(first)
        self.assertFalse(board["complete"])
        self.assertEqual(board["total"], 3)
        self.assertEqual(board["row_count"], 1)
        self.assertIsNone(board["gap_to_next_higher_score"])
        for entries in ([], [row(2, "B", 199291)], [row(1, "A", 219559)]*2):
            with self.subTest(entries=entries), self.assertRaises(RankingError):
                first_page_snapshot(parse_ranking_response(payload(entries)))

    def test_tied_ranks_are_not_mistaken_for_duplicate_teams(self):
        board = first_page_snapshot(parse_ranking_response(payload(
            [row(1, "A", 20), row(1, "B", 20), row(3, "C", 10)], current=[])))
        self.assertEqual(board["total"], 3)
        self.assertIsNone(board["current_team"])

    def test_reads_only_first_page_without_any_pagination(self):
        entries = [row(i, "team" + str(i), 1000-i) for i in range(1, 51)]
        frames = [payload(entries[i:i+10], total=50, current=[]) for i in range(0, 50, 10)]
        page = Page(frames)
        board = collect_first_page(page, 1000)
        self.assertEqual(board["total"], 50)
        self.assertFalse(board["complete"])
        self.assertEqual(board["scope"], "first_page")
        self.assertEqual(board["page_count"], 1)
        self.assertEqual(board["row_count"], 10)
        self.assertEqual(board["entries"][-1]["rank"], 10)
        self.assertEqual(page.index, 0)
        self.assertEqual(page.visited, [RANKING_URL])

    def test_missing_top_rows_is_an_error_without_trying_other_pages(self):
        with self.assertRaises(RankingError):
            collect_first_page(Page([payload([], total=3)]), 1000)

    def test_saves_whole_json_and_csv_and_latest(self):
        board = snapshot()
        board["entries"][0]["team_name"] = "=UNTRUSTED()"
        with tempfile.TemporaryDirectory(dir=self.scratch_root) as scratch:
            saved = save_ranking(board, Path(scratch))
            self.assertEqual(json.loads(Path(saved["snapshot_path"]).read_text(encoding="utf-8")), board)
            self.assertEqual(json.loads((Path(scratch)/"latest.json").read_text(encoding="utf-8")), board)
            csv_text = Path(saved["csv_path"]).read_text(encoding="utf-8-sig")
            self.assertIn("'=UNTRUSTED()", csv_text)
            self.assertEqual(len(csv_text.splitlines()), 4)

    def test_capture_failure_does_not_change_confirmed_score_or_identity(self):
        job = {"job_id": "test-job", "state": "completed", "score": 199291,
               "bound_submission_id": "known-work"}
        config = {"capture_ranking_on_completion": True}
        store = mock.Mock()
        with mock.patch.object(judge, "get_ranking", side_effect=RuntimeError("private response")):
            judge.capture_job_ranking(config, store, job)
        self.assertEqual(job["state"], "completed")
        self.assertEqual(job["score"], 199291)
        self.assertEqual(job["bound_submission_id"], "known-work")
        self.assertNotIn("private response", job["ranking_error"])
        store.save.assert_called_once_with(job)

    def test_capture_preserves_browser_context_and_does_not_repeat(self):
        job = {"state": "completed", "score": 199291}
        store, context = mock.Mock(), object()
        with tempfile.TemporaryDirectory(dir=self.scratch_root) as scratch:
            config = {"capture_ranking_on_completion": True, "runs_directory": scratch}
            with mock.patch.object(judge, "get_ranking", return_value=(snapshot(), {})) as collect:
                judge.capture_job_ranking(config, store, job, context=context)
                judge.capture_job_ranking(config, store, job, context=context)
                collect.assert_called_once_with(config, context=context)
            self.assertEqual(job["ranking_after"]["gap_from_submission_to_leader"], 20268)

    def test_many_submissions_share_one_check_for_at_least_two_hours(self):
        cfg = self.cache_config()
        start = datetime(2026, 10, 25, 8, tzinfo=CHINA_TIME)
        board = snapshot() | {"captured_at": start.isoformat()}
        with mock.patch.object(ranking, "datetime", wraps=datetime) as clock, \
                mock.patch.object(ranking, "collect_ranking", return_value=board) as fetch:
            clock.now.return_value = start
            _, first = get_ranking(cfg)
            self.assertFalse(first["cache_hit"])
            for _ in range(30):
                _, cached = get_ranking(cfg)
                self.assertTrue(cached["cache_hit"])
            clock.now.return_value = start + timedelta(hours=2, seconds=-1)
            get_ranking(cfg)
            self.assertEqual(fetch.call_count, 1)
            clock.now.return_value = start + timedelta(hours=2, seconds=1)
            fetch.return_value = board | {"captured_at": clock.now.return_value.isoformat()}
            _, refreshed = get_ranking(cfg)
            self.assertFalse(refreshed["cache_hit"])
            self.assertEqual(fetch.call_count, 2)

    def test_failed_check_also_throttles_retries_for_two_hours(self):
        cfg = self.cache_config()
        start = datetime(2026, 10, 25, 8, tzinfo=CHINA_TIME)
        with mock.patch.object(ranking, "datetime", wraps=datetime) as clock, \
                mock.patch.object(ranking, "collect_ranking", side_effect=RankingError("offline")) as fetch:
            clock.now.return_value = start
            for _ in range(10):
                with self.assertRaises(RankingError):
                    get_ranking(cfg)
            self.assertEqual(fetch.call_count, 1)
            clock.now.return_value = start + timedelta(hours=2, seconds=1)
            with self.assertRaises(RankingError):
                get_ranking(cfg)
            self.assertEqual(fetch.call_count, 2)

    def test_failed_refresh_reuses_previous_score_and_marks_it_stale(self):
        cfg = self.cache_config()
        start = datetime(2026, 10, 25, 8, tzinfo=CHINA_TIME)
        board = snapshot() | {"captured_at": start.isoformat()}
        with mock.patch.object(ranking, "datetime", wraps=datetime) as clock, \
                mock.patch.object(ranking, "collect_ranking", return_value=board) as fetch:
            clock.now.return_value = start
            get_ranking(cfg)
            clock.now.return_value = start + timedelta(hours=2, seconds=1)
            fetch.side_effect = RankingError("offline")
            old, files = get_ranking(cfg)
            self.assertEqual(old["leader"]["score"], 219559)
            self.assertTrue(files["cache_hit"])
            self.assertTrue(files["stale"])
            get_ranking(cfg)
            self.assertEqual(fetch.call_count, 2)

    def test_old_full_board_migrates_locally_without_a_new_request(self):
        cfg = self.cache_config()
        start = datetime(2026, 10, 25, 8, tzinfo=CHINA_TIME)
        entries = [row(i, "team"+str(i), 10000-i) for i in range(1, 51)]
        old = first_page_snapshot(parse_ranking_response(payload(entries, total=50, current=[])))
        old.update(captured_at=start.isoformat(), schema_version=1, page_count=5)
        old.pop("scope")
        directory = Path(cfg["runs_directory"])/"rankings"
        directory.mkdir()
        (directory/"latest.json").write_text(json.dumps(old), encoding="utf-8")
        with mock.patch.object(ranking, "datetime", wraps=datetime) as clock, \
                mock.patch.object(ranking, "collect_ranking") as fetch:
            clock.now.return_value = start + timedelta(minutes=10)
            board, files = get_ranking(cfg)
            fetch.assert_not_called()
        self.assertEqual(board["captured_at"], start.isoformat())
        self.assertEqual(board["row_count"], 10)
        self.assertFalse(board["complete"])
        self.assertTrue(files["cache_hit"])


if __name__ == "__main__":
    unittest.main()
