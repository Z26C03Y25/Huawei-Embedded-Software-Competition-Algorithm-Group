"""Confirmed submission API schema, UTC conversion and sensitive-data exclusion."""

import json
from pathlib import Path
import sys
import traceback
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from online_judge.api import API_URL, ApiAuthenticationError, ApiResponseError, parse_api_response
from online_judge.records import first_record, normalize_record


SECRET = "SENSITIVE_SENTINEL_COOKIE_CSRF_USER_3819"


def api_row(**changes):
    return {"id": "opaque-server-id-1", "name": "main.cpp",
            "created_time": "2026-10-24 10:22:20.808000", "score": "145904",
            "status": "completed", "stage_name": "赛事", "message": "Success",
            "is_invalid": True, **changes}


class ApiParsingTests(unittest.TestCase):
    def test_confirmed_endpoint_and_latest_order_match_the_dom(self):
        self.assertEqual(API_URL, "https://devdata2.huaweicloud.com/rest/developer/fwdu/rest/developer/user/hdcompetitionservice/v1/works/get-competition-works")
        records = parse_api_response({"results": [api_row(), api_row(id="older-id", score="154353",
                                               created_time="2026-10-24 10:01:00.000000")], "total": 9})
        latest = first_record(records)
        self.assertEqual(latest.score, 145904)
        self.assertEqual(records[1].score, 154353)
        self.assertEqual(latest.submitted_at, "2026-10-24 18:22:20")
        self.assertEqual(latest.submission_type, "赛事")
        self.assertEqual(latest.submission_id, "opaque-server-id-1")
        self.assertEqual(latest.source, "api")
        self.assertEqual(latest.status, "success")
        self.assertEqual(latest.identity, ("main.cpp", "2026-10-24 18:22:20"))

    def test_utc_naive_iso_z_and_explicit_offsets_convert_to_china_time(self):
        timestamps = ("2026-10-24 10:22:20.808000", "2026-10-24T10:22:20.808Z",
                      "2026-10-24T10:22:20+00:00", "2026-10-24T10:22:20+00",
                      "2026-10-24T18:22:20+08:00")
        for timestamp in timestamps:
            with self.subTest(timestamp=timestamp):
                record = parse_api_response({"results": [api_row(created_time=timestamp)]})[0]
                self.assertEqual(record.submitted_at, "2026-10-24 18:22:20")
        record = parse_api_response({"results": [api_row(created_time="2026-10-24 20:00:00.999999")]})[0]
        self.assertEqual(record.submitted_at, "2026-10-25 04:00:00")

    def test_pending_numeric_zero_is_not_a_completed_zero(self):
        pending = parse_api_response({"results": [api_row(status="pending", score="0")]})[0]
        self.assertEqual(pending.score, 0)
        self.assertEqual(pending.status, "pending")
        self.assertFalse(pending.is_terminal)
        completed = parse_api_response({"results": [api_row(score="0")]})[0]
        self.assertEqual(completed.score, 0)
        self.assertEqual(completed.status, "success")
        self.assertTrue(completed.is_terminal)

    def test_nonnumeric_pending_or_missing_score_is_none(self):
        for score in ("pending", "--", "", None):
            with self.subTest(score=score):
                record = parse_api_response({"results": [api_row(status="pending", score=score)]})[0]
                self.assertIsNone(record.score)
                self.assertEqual(record.status, "pending")

    def test_message_failed_is_failure_and_is_invalid_does_not_override_success(self):
        success = parse_api_response({"results": [api_row(is_invalid=True)]})[0]
        self.assertEqual(success.status, "success")
        self.assertEqual(success.score, 145904)
        failure = parse_api_response({"results": [api_row(message="Failed", score="--")]})[0]
        self.assertEqual(failure.status, "failed")
        self.assertTrue(failure.is_terminal)
        self.assertIsNone(failure.score)

    def test_unknown_status_and_positive_score_do_not_imply_success(self):
        for changes in ({"status": "mystery"}, {"message": "mystery"},
                        {"status": "success", "message": "Success"}):
            with self.subTest(changes=changes):
                record = parse_api_response({"results": [api_row(**changes)]})[0]
                self.assertEqual(record.status, "unknown")
                self.assertEqual(record.score, 145904)

    def test_only_explicit_results_array_is_accepted_without_recursive_score_search(self):
        self.assertEqual(parse_api_response({"results": [], "total": 0}), [])
        invalid = (None, [], {"data": {"results": [api_row()]}}, {"score": 145904},
                   {"results": None}, {"results": {}}, {"results": "[]"},
                   {"results": [None]}, {"results": ["145904"]})
        for payload in invalid:
            with self.subTest(payload_type=type(payload).__name__), self.assertRaises(ApiResponseError):
                parse_api_response(payload)

    def test_missing_required_id_name_and_invalid_timestamps_fail(self):
        invalid_changes = ({"id": None}, {"id": 123}, {"id": ""}, {"name": None},
                           {"created_time": "2026-02-30 10:00:00"}, {"created_time": "2026-10-24"},
                           {"created_time": 1792837340}, {"created_time": "1792837340"},
                           {"created_time": None}, {"stage_name": []})
        for changes in invalid_changes:
            with self.subTest(changes=changes), self.assertRaises(ApiResponseError):
                parse_api_response({"results": [api_row(**changes)]})

    def test_authentication_errors_and_other_http_errors_ignore_payload(self):
        for status in (401, 403):
            with self.subTest(status=status), self.assertRaises(ApiAuthenticationError) as caught:
                parse_api_response({"token": SECRET, "results": [api_row()]}, status)
            self.assertNotIn(SECRET, str(caught.exception))
        for status in (400, 404, 429, 500):
            with self.subTest(status=status), self.assertRaises(ApiResponseError) as caught:
                parse_api_response({"token": SECRET, "results": []}, status)
            self.assertNotIsInstance(caught.exception, ApiAuthenticationError)
            self.assertNotIn(SECRET, str(caught.exception))

    def test_pii_cookies_headers_and_arbitrary_raw_status_text_are_not_retained(self):
        payload = {"results": [api_row(phone=SECRET, user_name=SECRET, email=SECRET,
                                      status=SECRET, message=SECRET, score=SECRET)],
                   "cookies": SECRET, "headers": {"Cookie": SECRET, "X-CSRF-Token": SECRET},
                   "access_token": SECRET, "account": SECRET}
        record = parse_api_response(payload)[0]
        encoded = json.dumps(record.to_dict(), ensure_ascii=False)
        self.assertNotIn(SECRET, encoded)
        self.assertEqual(record.status, "unknown")
        self.assertIsNone(record.score)

    def test_malformed_responses_never_put_sensitive_values_in_exception_or_traceback(self):
        payloads = ({"results": SECRET}, {"results": [api_row(created_time=SECRET)]},
                    {"results": [api_row(stage_name={"token": SECRET})]})
        for payload in payloads:
            with self.subTest(payload_type=type(payload["results"]).__name__):
                try:
                    parse_api_response(payload)
                except ApiResponseError as exc:
                    self.assertNotIn(SECRET, str(exc))
                    self.assertNotIn(SECRET, traceback.format_exc())
                else:
                    self.fail("malformed response was accepted")

    def test_normalized_mapping_roundtrip_keeps_server_id_and_source(self):
        api_record = parse_api_response({"results": [api_row()]})[0]
        restored = normalize_record(json.loads(json.dumps(api_record.to_dict())))
        self.assertEqual(restored, api_record)
        dom_record = normalize_record({"filename": "main.cpp", "submission_type": "赛事",
                                       "submitted_at": api_record.submitted_at, "score": 145904,
                                       "status": "success"})
        self.assertIsNone(dom_record.submission_id)
        self.assertEqual(dom_record.source, "dom")
        self.assertEqual(dom_record.identity, api_record.identity)


if __name__ == "__main__":
    unittest.main()
