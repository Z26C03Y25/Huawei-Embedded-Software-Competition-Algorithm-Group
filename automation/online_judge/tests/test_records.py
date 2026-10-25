"""Pure parsing and new-submission correlation tests; no browser access."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from online_judge.records import (RecordBaseline, find_record, first_new_record, first_record,
                                  new_records, normalize_record, parse_score,
                                  parse_submission_html, parse_submitted_at)


def row(filename="main.cpp", submitted_at="2026-10-24 18:22:20", score="145904",
        status="success", row_id="row_1", submission_type="赛事"):
    return f"""<tr data-rowid="{row_id}">
      <td data-colid="col_1"><a><span>{filename}</span></a></td>
      <td data-colid="col_2">{submission_type}</td>
      <td data-colid="col_3"><div>{submitted_at}</div></td>
      <td data-colid="col_6"><div class="statusBox {status}">{status}</div></td>
      <td data-colid="col_7"><span class="scoringBox"><b>{score}</b></span><span>999999</span></td>
    </tr>"""


def grid(*rows):
    return '<table class="tiny-grid__body striped"><tbody>' + "".join(rows) + "</tbody></table>"


def record(**overrides):
    value = {"filename": "main.cpp", "submission_type": "赛事", "submitted_at": "2026-10-24 18:22:20",
             "score": "145904", "status": "success", **overrides}
    return normalize_record(value)


class ParseTests(unittest.TestCase):
    def test_first_row_is_latest_even_when_second_score_is_higher(self):
        records = parse_submission_html(grid(row(), row(submitted_at="2026-10-24 18:01:00",
                                                        score="154353", row_id="row_2")))
        latest = first_record(records)
        self.assertEqual(latest.filename, "main.cpp")
        self.assertEqual(latest.submission_type, "赛事")
        self.assertEqual(latest.submitted_at, "2026-10-24 18:22:20")
        self.assertEqual(latest.score, 145904)
        self.assertEqual(records[1].score, 154353)
        self.assertTrue(latest.succeeded)

    def test_zero_and_comma_scores_are_numeric_pending_is_not_zero(self):
        self.assertEqual(parse_score("0"), 0)
        self.assertEqual(parse_score(" 145,904 "), 145904)
        self.assertEqual(parse_score("1,234,567"), 1234567)
        for invalid in ("--", "评测中", "pending", "", "14,59,04", "1.5", -1, True, None):
            with self.subTest(invalid=invalid):
                self.assertIsNone(parse_score(invalid))
        pending, zero = parse_submission_html(grid(row(score="评分中", status="pending"),
                                                   row(score="0", row_id="row_2")))
        self.assertIsNone(pending.score)
        self.assertFalse(pending.is_terminal)
        self.assertEqual(zero.score, 0)
        self.assertTrue(zero.is_terminal)

    def test_failed_status_is_terminal_without_fabricating_score(self):
        failed = parse_submission_html(grid(row(score="--", status="failed")))[0]
        self.assertEqual(failed.status, "failed")
        self.assertTrue(failed.is_terminal)
        self.assertFalse(failed.succeeded)
        self.assertIsNone(failed.score)
        self.assertEqual(record(status="编译错误", score="--").status, "failed")
        self.assertEqual(record(status="评测中", score="--").status, "pending")

    def test_empty_placeholders_other_tables_and_headers_are_ignored(self):
        html = '<table><tbody>' + row() + '</tbody></table>'
        html += grid('<tr class="tiny-grid__empty"><td colspan="9">暂无数据</td></tr>')
        html += '<table class="tiny-grid__body"><thead>' + row() + '</thead><tbody></tbody></table>'
        self.assertEqual(parse_submission_html(html), [])
        self.assertIsNone(first_record([]))

    def test_status_class_hint_entities_and_score_selector(self):
        html = grid(row(filename="a&amp;b.cpp", score="145,904"))
        html = html.replace('class="statusBox success">success', 'class="statusBox success">已完成')
        parsed = parse_submission_html(html)[0]
        self.assertEqual(parsed.filename, "a&b.cpp")
        self.assertEqual(parsed.status, "success")
        self.assertEqual(parsed.score, 145904)  # Ignore the sibling 999999 text.
        without_selector = html.replace('class="scoringBox"', 'class="unrelated"')
        self.assertIsNone(parse_submission_html(without_selector)[0].score)

    def test_invalid_timestamps_are_rejected_and_optionally_skipped(self):
        for timestamp in ("2026-02-30 18:22:20", "2026-10-24", "2026-10-24T18:22:20",
                          "2026-1-1 01:02:03", "2026-10-24 25:00:00"):
            with self.subTest(timestamp=timestamp):
                with self.assertRaises(ValueError):
                    parse_submitted_at(timestamp)
                with self.assertRaises(ValueError):
                    parse_submission_html(grid(row(submitted_at=timestamp)))
                self.assertEqual(parse_submission_html(grid(row(submitted_at=timestamp)), strict=False), [])

    def test_mapping_aliases_and_json_round_trip(self):
        value = normalize_record({"col_1": " main.cpp ", "col_2": "赛事", "col_3": "2026-10-24 18:22:20",
                                  "col_6": "success", "col_7": "145,904", "data-rowid": "row_23"})
        restored = normalize_record(json.loads(json.dumps(value.to_dict(), ensure_ascii=False)))
        self.assertEqual(value, restored)
        self.assertEqual(json.loads(value.identity_key), ["main.cpp", "2026-10-24 18:22:20"])


class DetectionTests(unittest.TestCase):
    def test_old_rows_are_not_new_even_when_snapshot_mtime_changes(self):
        old = record()
        baseline = RecordBaseline.from_records([old], source_mtime_ns=100)
        self.assertEqual(new_records([old], baseline, source_mtime_ns=200), [])
        self.assertIsNone(first_new_record([old], baseline, source_mtime_ns=200))

    def test_stale_snapshot_guard_and_filename_time_filters(self):
        baseline = RecordBaseline.from_records([record()], source_mtime_ns=100)
        fresh = record(submitted_at="2026-10-24 18:23:10", status="pending", score="--")
        self.assertEqual(new_records([fresh], baseline, source_mtime_ns=100), [])
        self.assertEqual(new_records([fresh], baseline, source_mtime_ns=99), [])
        self.assertEqual(first_new_record([fresh], baseline, source_mtime_ns=101), fresh)
        self.assertEqual(new_records([fresh], baseline, expected_filename="other.cpp"), [])
        self.assertEqual(new_records([fresh], baseline, submitted_not_before="2026-10-24 18:24:00"), [])
        self.assertEqual(new_records([fresh], baseline, submitted_not_before="2026-10-24 18:23:10"), [fresh])

    def test_pending_to_success_and_rowid_changes_do_not_create_identity(self):
        pending = record(status="pending", score="--", row_id="row_1")
        completed = record(status="success", score="145904", row_id="row_4")
        baseline = RecordBaseline.from_records([pending], source_mtime_ns=10)
        self.assertEqual(pending.identity, completed.identity)
        self.assertEqual(pending.identity_key, completed.identity_key)
        self.assertEqual(new_records([completed], baseline, source_mtime_ns=20), [])
        self.assertEqual(find_record([completed], pending.identity), completed)
        self.assertEqual(find_record([completed], pending.identity_key), completed)

    def test_new_identity_keeps_dom_order_and_deduplicates(self):
        old = record()
        latest = record(submitted_at="2026-10-24 18:30:00", score="0")
        second = record(submitted_at="2026-10-24 18:29:00", score="200000")
        baseline = RecordBaseline.from_records([old])
        self.assertEqual(new_records([latest, second, latest, old], baseline), [latest, second])
        self.assertEqual(first_new_record([latest, second, old], baseline), latest)

    def test_cutoff_accepts_aware_datetimes_in_china_local_time(self):
        fresh = record(submitted_at="2026-10-24 18:23:10")
        cutoff = datetime(2026, 10, 24, 10, 23, 10, tzinfo=timezone.utc)
        self.assertEqual(new_records([fresh], [], submitted_not_before=cutoff), [fresh])
        self.assertEqual(new_records([fresh], [], submitted_not_before=cutoff.replace(second=11)), [])

    def test_baseline_json_round_trip_and_same_second_ambiguity(self):
        old = record()
        baseline = RecordBaseline.from_records([old], source_mtime_ns=12345)
        restored = RecordBaseline.from_dict(json.loads(json.dumps(baseline.to_dict())))
        self.assertEqual(restored, baseline)
        same_second = record(score="999999", row_id="row_99")
        self.assertEqual(new_records([same_second], restored, source_mtime_ns=20000), [])


if __name__ == "__main__":
    unittest.main()
