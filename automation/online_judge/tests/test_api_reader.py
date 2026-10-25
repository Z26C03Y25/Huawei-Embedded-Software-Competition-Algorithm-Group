"""Offline API-first browser reader contracts; no browser or network is started."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from online_judge import browser
from online_judge.records import normalize_record


API_URL = ("https://devdata2.huaweicloud.com/rest/developer/fwdu/rest/developer/user/"
           "hdcompetitionservice/v1/works/get-competition-works")
DOM_HTML = '''<table class="tiny-grid__body"><tbody><tr>
<td data-colid="col_1">main.cpp</td><td data-colid="col_2">赛事</td>
<td data-colid="col_3">2026-10-24 18:22:20</td>
<td data-colid="col_6">success</td>
<td data-colid="col_7"><span class="scoringBox">145904</span></td>
</tr></tbody></table>'''


def record(score=145904, *, second=20, status="success"):
    return normalize_record({"filename": "main.cpp", "submission_type": "赛事",
                             "submitted_at": f"2026-10-24 18:22:{second:02d}",
                             "status": status, "score": score})


class FakeRequest:
    def __init__(self, method="POST"):
        self.method = method

    @property
    def headers(self):
        raise AssertionError("The score reader must not inspect credential headers")

    @property
    def post_data(self):
        raise AssertionError("The score reader must not inspect or replay request bodies")


class FakeResponse:
    def __init__(self, payload=None, *, url=API_URL, method="POST", status=200,
                 json_error=None):
        self.url = url
        self.request = FakeRequest(method)
        self.status = status
        self.payload = {"fixture": "opaque API response"} if payload is None else payload
        self.json_error = json_error
        self.json_reads = 0

    def json(self):
        self.json_reads += 1
        if self.json_error:
            raise self.json_error
        return self.payload

    @property
    def headers(self):
        raise AssertionError("The score reader must not inspect response headers")

    def body(self):
        raise AssertionError("Do not dump or persist raw response bytes")

    def text(self):
        raise AssertionError("Do not dump or persist raw response text")


class FakeExpectation:
    def __init__(self, page, predicate):
        self.page = page
        self.predicate = predicate
        self.response = None

    def __enter__(self):
        self.page.events.append("expect_enter")
        self.page.active_expectation = self
        return self

    def __exit__(self, kind, value, traceback):
        self.page.events.append("expect_exit")
        self.page.active_expectation = None
        if kind is None and self.response is None:
            raise TimeoutError("No matching response in the offline fixture")
        return False

    @property
    def value(self):
        if self.response is None:
            raise TimeoutError("No matching response in the offline fixture")
        return self.response


class FakePage:
    def __init__(self, responses=()):
        self.responses = list(responses)
        self.listeners = {}
        self.events = []
        self.reload_calls = []
        self.expectations = []
        self.active_expectation = None
        self.url = browser.DEFAULT_URL

    def set_default_timeout(self, milliseconds):
        self.default_timeout = milliseconds

    def on(self, event, callback):
        self.events.append("listen:" + event)
        self.listeners.setdefault(event, []).append(callback)

    def remove_listener(self, event, callback):
        self.events.append("remove:" + event)
        callbacks = self.listeners.get(event, [])
        if callback in callbacks:
            callbacks.remove(callback)

    def expect_response(self, predicate, **kwargs):
        self.events.append("expect_created")
        expectation = FakeExpectation(self, predicate)
        self.expectations.append(expectation)
        return expectation

    def emit(self, response):
        for listener in list(self.listeners.get("response", [])):
            listener(response)
        expectation = self.active_expectation
        if expectation is not None and expectation.predicate(response) and expectation.response is None:
            expectation.response = response

    def reload(self, **kwargs):
        self.events.append("reload")
        self.reload_calls.append(kwargs)
        for response in self.responses:
            self.emit(response)

    def wait_for_timeout(self, milliseconds):
        # Model Playwright's event-pump call without sleeping or networking.
        self.events.append("pump:" + str(milliseconds))


class ApiReaderTests(unittest.TestCase):
    def adapter(self, responses=(), *, source=None):
        page = FakePage(responses)
        settings = {"submission_url": browser.DEFAULT_URL, "action_timeout_ms": 250,
                    "table_selector": "table.tiny-grid__body", "upload_button_text": "上传作品"}
        if source is not None:
            settings["score_source"] = source
        adapter = browser.SubmissionPage(page, settings)
        adapter.ensure_ready = mock.Mock()
        adapter.table_html = mock.Mock(return_value=DOM_HTML)
        self.addCleanup(lambda: getattr(adapter, "close", lambda: None)())
        return page, adapter

    def parser(self, **kwargs):
        return mock.patch.object(browser, "parse_api_response", create=True, **kwargs)

    def test_api_observer_is_installed_before_reload_and_default_auto_prefers_api(self):
        response = FakeResponse()
        expected = [record(154353)]
        page, adapter = self.adapter([response])
        with self.parser(return_value=expected) as parse:
            result = adapter.records(refresh=True)
        self.assertEqual(result, expected)
        self.assertLess(page.events.index("expect_enter"), page.events.index("reload"))
        self.assertEqual(page.reload_calls, [{"wait_until": "domcontentloaded"}])
        self.assertEqual(response.json_reads, 1)
        self.assertIs(parse.call_args.args[0], response.payload)
        adapter.table_html.assert_not_called()

    def test_observer_matches_only_exact_api_url_and_post_method(self):
        wrong_get = FakeResponse(method="GET")
        wrong_path = FakeResponse(url=API_URL + "/other")
        wrong_query = FakeResponse(url=API_URL + "?other=1")
        wrong_host = FakeResponse(url=API_URL.replace("devdata2.huaweicloud.com", "example.invalid"))
        wanted = FakeResponse(payload={"fixture": "the matching POST"})
        page, adapter = self.adapter([wrong_get, wrong_path, wrong_query, wrong_host, wanted])
        expected = [record()]
        with self.parser(return_value=expected) as parse:
            self.assertEqual(adapter.records(refresh=True), expected)
        parse.assert_called_once()
        self.assertIs(parse.call_args.args[0], wanted.payload)
        self.assertEqual([response.json_reads for response in
                          (wrong_get, wrong_path, wrong_query, wrong_host)], [0, 0, 0, 0])
        adapter.table_html.assert_not_called()

    def test_auto_unknown_schema_falls_back_to_dom_without_second_reload(self):
        page, adapter = self.adapter([FakeResponse()])
        with self.parser(side_effect=browser.ApiResponseError("Unrecognized API response schema")):
            result = adapter.records(refresh=True)
        self.assertEqual([item.score for item in result], [145904])
        self.assertEqual(len(page.reload_calls), 1)
        adapter.table_html.assert_called_once_with(refresh=False)

    def test_auto_http_5xx_falls_back_to_dom_without_second_reload(self):
        page, adapter = self.adapter([FakeResponse(status=503)])
        with self.parser(side_effect=browser.ApiResponseError("API unavailable")):
            result = adapter.records(refresh=True)
        self.assertEqual([item.score for item in result], [145904])
        self.assertEqual(len(page.reload_calls), 1)
        adapter.table_html.assert_called_once_with(refresh=False)

    def test_auto_no_api_response_falls_back_after_only_one_reload(self):
        page, adapter = self.adapter([])
        with self.parser() as parse:
            result = adapter.records(refresh=True)
        self.assertEqual([item.score for item in result], [145904])
        self.assertEqual(len(page.reload_calls), 1)
        parse.assert_not_called()
        adapter.table_html.assert_called_once_with(refresh=False)

    def test_refresh_does_not_present_a_preexisting_response_as_a_new_result(self):
        page, adapter = self.adapter([])
        stale = FakeResponse()
        page.emit(stale)
        with self.parser(return_value=[record(154353)]) as parse:
            result = adapter.records(refresh=True)
        self.assertEqual([item.score for item in result], [145904])
        self.assertEqual(len(page.reload_calls), 1)
        self.assertEqual(stale.json_reads, 0)
        parse.assert_not_called()
        adapter.table_html.assert_called_once_with(refresh=False)

    def test_http_authentication_failures_require_login_and_never_fallback(self):
        for status in (401, 403):
            with self.subTest(status=status):
                page, adapter = self.adapter([FakeResponse(status=status)])
                with self.assertRaises(browser.BrowserError) as raised:
                    adapter.records(refresh=True)
                self.assertRegex(str(raised.exception).lower(), r"登录|login|认证")
                self.assertEqual(len(page.reload_calls), 1)
                adapter.table_html.assert_not_called()

    def test_refresh_false_without_observed_response_uses_dom_without_reload(self):
        page, adapter = self.adapter()
        with self.parser() as parse:
            result = adapter.records(refresh=False)
        self.assertEqual([item.score for item in result], [145904])
        self.assertEqual(page.reload_calls, [])
        self.assertEqual(page.expectations, [])
        parse.assert_not_called()
        adapter.table_html.assert_called_once_with(refresh=False)

    def test_refresh_false_consumes_passively_observed_response_without_reload(self):
        page, adapter = self.adapter()
        response = FakeResponse()
        page.emit(response)
        expected = [record(154353)]
        with self.parser(return_value=expected):
            result = adapter.records(refresh=False)
        self.assertEqual(result, expected)
        self.assertEqual(page.reload_calls, [])
        self.assertEqual(page.expectations, [])
        adapter.table_html.assert_not_called()

    def test_an_already_consumed_response_is_not_reused_as_a_new_observation(self):
        page, adapter = self.adapter()
        response = FakeResponse()
        page.emit(response)
        with self.parser(return_value=[record(154353)]) as parse:
            first = adapter.records(refresh=False)
            second = adapter.records(refresh=False)
        self.assertEqual([item.score for item in first], [154353])
        self.assertEqual([item.score for item in second], [145904])
        parse.assert_called_once()
        self.assertEqual(response.json_reads, 1)
        self.assertEqual(page.reload_calls, [])
        adapter.table_html.assert_called_once_with(refresh=False)

    def test_explicit_dom_mode_never_observes_api_or_reads_response_json(self):
        response = FakeResponse()
        page, adapter = self.adapter([response], source="dom")
        with self.parser() as parse:
            result = adapter.records(refresh=True)
        self.assertEqual([item.score for item in result], [145904])
        self.assertEqual(page.expectations, [])
        self.assertEqual(response.json_reads, 0)
        parse.assert_not_called()
        adapter.table_html.assert_called_once_with(refresh=True)

    def test_strict_api_mode_reports_schema_failure_without_dom_fallback(self):
        page, adapter = self.adapter([FakeResponse()], source="api")
        with self.parser(side_effect=browser.ApiResponseError("Unrecognized API response schema")), \
                self.assertRaises(browser.BrowserError):
            adapter.records(refresh=True)
        self.assertEqual(len(page.reload_calls), 1)
        adapter.table_html.assert_not_called()

    def test_strict_api_mode_without_a_new_response_does_not_reload_or_use_dom(self):
        page, adapter = self.adapter(source="api")
        with self.parser() as parse:
            self.assertEqual(adapter.records(refresh=False), [])
        self.assertEqual(page.reload_calls, [])
        parse.assert_not_called()
        adapter.table_html.assert_not_called()

    def test_valid_empty_api_list_is_not_replaced_by_old_dom_history(self):
        page, adapter = self.adapter([FakeResponse()])
        with self.parser(return_value=[]):
            self.assertEqual(adapter.records(refresh=True), [])
        self.assertEqual(len(page.reload_calls), 1)
        adapter.table_html.assert_not_called()

    def test_api_failure_does_not_print_payload_or_exception_sentinel(self):
        sentinel = "OFFLINE_SECRET_CANARY_DO_NOT_LOG_8871"
        response = FakeResponse(payload={"unrecognized": sentinel}, json_error=ValueError(sentinel))
        _, adapter = self.adapter([response])
        output, errors = StringIO(), StringIO()
        with self.parser(), redirect_stdout(output), redirect_stderr(errors):
            result = adapter.records(refresh=True)
        self.assertEqual([item.score for item in result], [145904])
        self.assertNotIn(sentinel, output.getvalue() + errors.getvalue())
        adapter.table_html.assert_called_once_with(refresh=False)

    def test_close_removes_response_listener(self):
        page, adapter = self.adapter()
        self.assertTrue(page.listeners.get("response"))
        adapter.close()
        self.assertEqual(page.listeners.get("response", []), [])


if __name__ == "__main__":
    unittest.main()
