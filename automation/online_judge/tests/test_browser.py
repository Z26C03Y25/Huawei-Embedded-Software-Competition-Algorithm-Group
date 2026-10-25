"""Chrome adapter contracts, exercised entirely with local fakes and no network."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from online_judge import browser


EMPTY_SELECTOR = "div.tiny-grid__body-wrapper .tiny-grid__empty-block"
EMPTY_TABLE = '<table class="tiny-grid__body"><tbody></tbody></table>'
VALID_TABLE = '''<table class="tiny-grid__body"><tbody><tr data-rowid="row_1">
<td data-colid="col_1">main.cpp</td><td data-colid="col_2">赛事</td>
<td data-colid="col_3">2026-10-24 18:22:20</td>
<td data-colid="col_6">success</td>
<td data-colid="col_7"><span class="scoringBox">145904</span></td>
</tr></tbody></table>'''


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def advance(self, milliseconds):
        self.now += milliseconds / 1000


def config(**changes):
    return {"chrome_path": "Chrome/Application", "cdp_url": "http://127.0.0.1:9222",
            "submission_url": browser.DEFAULT_URL, "profile_directory": ".test-profile",
            "runs_directory": ".test-runs", "poll_interval_seconds": 5,
            "timeout_seconds": 60, "action_timeout_ms": 250,
            "upload_button_text": "上传作品", "confirm_button_text": None,
            "table_selector": "table.tiny-grid__body", "file_input_selector": "input[type=file]",
            **changes}


class FakeButton:
    def __init__(self, count=1, on_click=None):
        self.matches = count
        self.on_click = on_click
        self.clicks = 0

    def wait_for(self, **kwargs):
        pass

    def count(self):
        return self.matches

    def click(self):
        self.clicks += 1
        if self.on_click:
            self.on_click()


class FakeChooser:
    def __init__(self):
        self.files = []

    def set_files(self, filename):
        self.files.append(filename)


class FakeInputs:
    def __init__(self, count=1):
        self.matches = count
        self.files = []

    def count(self):
        return self.matches

    def set_input_files(self, filename):
        self.files.append(filename)


class FakeTable:
    def __init__(self, visible=True, html=VALID_TABLE):
        self.visible = visible
        self.html = html
        self.reads = 0

    def wait_for(self, **kwargs):
        pass

    def is_visible(self):
        return self.visible

    def evaluate(self, expression):
        self.reads += 1
        return self.html

    def locator(self, selector):
        if selector == "tbody tr":
            return FakeInputs(self.html.count("<tr"))
        raise AssertionError(f"unexpected table locator: {selector}")


class FakeTables:
    def __init__(self, tables):
        self.tables = tables

    @property
    def first(self):
        return self.tables[0] if self.tables else FakeTable(visible=False)

    def all(self):
        return self.tables

    def count(self):
        return len(self.tables)


class FakePage:
    def __init__(self, settings=None, *, inputs=1, choosers=(), tables=(), empty_blocks=(),
                 on_wait=None, on_idle=None, idle_error=False):
        self.settings = settings or config()
        self.url = self.settings["submission_url"]
        self.listeners = {}
        self.choosers = list(choosers)
        self.inputs = FakeInputs(inputs)
        self.tables = FakeTables(list(tables))
        self.empty_blocks = FakeTables(list(empty_blocks))
        self.upload_button = FakeButton(on_click=self.emit_choosers)
        self.confirm_button = FakeButton()
        self.role_requests = []
        self.reloads = 0
        self.clock = FakeClock()
        self.waits = []
        self.load_state_calls = []
        self.on_wait = on_wait
        self.on_idle = on_idle
        self.idle_error = idle_error

    def set_default_timeout(self, milliseconds):
        self.timeout_ms = milliseconds

    def get_by_role(self, role, *, name, exact):
        self.role_requests.append((role, name, exact))
        if name == self.settings["upload_button_text"]:
            return self.upload_button
        return self.confirm_button

    def locator(self, selector):
        if selector == self.settings["file_input_selector"]:
            return self.inputs
        if selector == self.settings["table_selector"]:
            return self.tables
        if selector == self.settings.get("empty_selector", EMPTY_SELECTOR):
            return self.empty_blocks
        raise AssertionError(f"unexpected locator: {selector}")

    def on(self, name, callback):
        self.listeners[name] = callback

    def remove_listener(self, name, callback):
        if self.listeners.get(name) == callback:
            del self.listeners[name]

    def emit_choosers(self):
        for chooser in self.choosers:
            self.listeners["filechooser"](chooser)

    def reload(self, **kwargs):
        self.reloads += 1

    def wait_for_timeout(self, milliseconds):
        if not 0 < milliseconds <= 100:
            raise AssertionError("polling must use positive waits of at most 100 ms")
        self.waits.append(milliseconds)
        self.clock.advance(milliseconds)
        if self.on_wait:
            self.on_wait(self)

    def wait_for_load_state(self, state, *, timeout):
        if state != "networkidle" or not 0 < timeout <= 500:
            raise AssertionError("empty-state confirmation must have a bounded networkidle wait")
        self.load_state_calls.append((state, timeout))
        if self.idle_error:
            self.clock.advance(timeout)
            raise TimeoutError("fake SPA is still loading")
        if self.on_idle:
            self.on_idle(self)


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="browser_test_", dir=Path(__file__).parent)
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.config_path = self.directory / "config.json"

    def load(self, **changes):
        self.config_path.write_text(json.dumps(config(**changes)), encoding="utf-8")
        return browser.load_config(self.config_path)

    def test_chrome_directory_resolves_to_chrome_exe_and_file_path_is_kept(self):
        directory = self.directory / "Application"
        directory.mkdir()
        self.assertEqual(browser.chrome_executable(config(chrome_path=str(directory))), directory / "chrome.exe")
        executable = directory / "chrome.exe"
        executable.write_bytes(b"fake executable; never launched")
        self.assertEqual(browser.chrome_executable(config(chrome_path=str(executable))), executable)

    def test_valid_config_and_explicit_loopback_addresses(self):
        for address in ("http://127.0.0.1:9222", "http://localhost:9222", "http://[::1]:9222"):
            with self.subTest(address=address):
                loaded = self.load(cdp_url=address)
                self.assertEqual(loaded["cdp_url"], address)
                self.assertTrue(Path(loaded["profile_directory"]).is_relative_to(browser.BASE))

    def test_config_rejects_nonloopback_or_ambiguous_cdp_endpoints(self):
        invalid = ("http://192.168.1.2:9222", "http://evil.com:9222", "http://localhost.evil.com:9222",
                   "https://127.0.0.1:9222", "http://127.0.0.1", "http://127.0.0.1:0",
                   "http://user@127.0.0.1:9222", "http://127.0.0.1:9222/?token=secret")
        for address in invalid:
            with self.subTest(address=address), self.assertRaises(ValueError):
                self.load(cdp_url=address)

    def test_config_rejects_wrong_host_or_different_competition(self):
        invalid = ("https://evil.com/competition/information/1300000312/submission",
                   "https://developer.huaweicloud.com.evil.com/competition/information/1300000312/submission",
                   "https://developer.huaweicloud.com/competition/information/999/submission",
                   "https://developer.huaweicloud.com/other/submission")
        for url in invalid:
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.load(submission_url=url)

    def test_profile_and_runs_cannot_escape_or_use_the_base_directory(self):
        for key in ("profile_directory", "runs_directory"):
            for destination in ("..", "../outside", ".", str(browser.BASE.parent)):
                with self.subTest(key=key, destination=destination), self.assertRaises(ValueError):
                    self.load(**{key: destination})

    def test_doctor_only_checks_files_and_dependencies(self):
        executable = self.directory / "chrome.exe"
        executable.write_bytes(b"fake executable; never launched")
        settings = config(chrome_path=str(executable))
        with patch.object(browser, "cdp_available", side_effect=AssertionError("no CDP connection")), \
             patch.object(browser, "start_browser", side_effect=AssertionError("no Chrome launch")), \
             patch.object(browser, "connect", side_effect=AssertionError("no browser connection")), \
             patch.object(browser, "build_opener", side_effect=AssertionError("no network")), \
             patch.object(browser.subprocess, "Popen", side_effect=AssertionError("no process")), \
             patch.object(browser.importlib.util, "find_spec", return_value=object()):
            result = browser.doctor(settings)
        self.assertTrue(result["chrome_exists"])
        self.assertTrue(result["playwright_installed"])
        self.assertTrue(result["ready"])


class PageTests(unittest.TestCase):
    snapshot = Path(__file__).resolve().parent / "not_opened_main.cpp"

    def adapter(self, **page_options):
        page = FakePage(**page_options)
        return page, browser.SubmissionPage(page, page.settings)

    def test_submission_url_matches_exact_host_and_competition_path(self):
        self.assertTrue(browser.is_submission_url(browser.DEFAULT_URL, browser.DEFAULT_URL))
        invalid = (browser.DEFAULT_URL.replace("developer.huaweicloud.com", "evil.com"),
                   browser.DEFAULT_URL.replace("developer.huaweicloud.com", "developer.huaweicloud.com.evil.com"),
                   browser.DEFAULT_URL.replace("1300000312", "999"),
                   browser.DEFAULT_URL + "-other", browser.DEFAULT_URL.replace("https:", "http:"))
        for url in invalid:
            with self.subTest(url=url):
                self.assertFalse(browser.is_submission_url(url, browser.DEFAULT_URL))

    def test_filechooser_path_clicks_and_selects_once_without_input_fallback(self):
        chooser = FakeChooser()
        page, adapter = self.adapter(choosers=[chooser], inputs=1)
        adapter.upload(self.snapshot)
        self.assertEqual(page.upload_button.clicks, 1)
        self.assertEqual(chooser.files, [str(self.snapshot)])
        self.assertEqual(page.inputs.files, [])
        self.assertNotIn("filechooser", page.listeners)

    def test_input_path_clicks_and_selects_once_without_guessing_confirmation(self):
        page, adapter = self.adapter(inputs=1)
        adapter.upload(self.snapshot)
        self.assertEqual(page.upload_button.clicks, 1)
        self.assertEqual(page.inputs.files, [str(self.snapshot)])
        self.assertEqual(page.confirm_button.clicks, 0)
        self.assertTrue(all(name == page.settings["upload_button_text"] and exact
                            for role, name, exact in page.role_requests))
        self.assertNotIn("filechooser", page.listeners)

    def test_multiple_file_inputs_are_rejected_without_retry_or_selection(self):
        page, adapter = self.adapter(inputs=2)
        with self.assertRaises(browser.BrowserError):
            adapter.upload(self.snapshot)
        self.assertEqual(page.upload_button.clicks, 1)
        self.assertEqual(page.inputs.files, [])
        self.assertNotIn("filechooser", page.listeners)

    def test_multiple_choosers_are_rejected_without_selecting_either(self):
        choosers = [FakeChooser(), FakeChooser()]
        page, adapter = self.adapter(choosers=choosers, inputs=1)
        with self.assertRaises(browser.BrowserError):
            adapter.upload(self.snapshot)
        self.assertEqual(page.upload_button.clicks, 1)
        self.assertTrue(all(not chooser.files for chooser in choosers))
        self.assertEqual(page.inputs.files, [])
        self.assertNotIn("filechooser", page.listeners)

    def test_configured_confirmation_is_exact_and_clicks_only_once(self):
        page, adapter = self.adapter(settings=config(confirm_button_text="确认提交"))
        adapter.upload(self.snapshot)
        self.assertEqual(page.upload_button.clicks, 1)
        self.assertEqual(page.inputs.files, [str(self.snapshot)])
        self.assertEqual(page.confirm_button.clicks, 1)
        self.assertIn(("button", "确认提交", True), page.role_requests)

    def test_nonunique_or_missing_configured_confirmation_never_clicks_it(self):
        for count in (0, 2):
            with self.subTest(count=count):
                page, adapter = self.adapter(settings=config(confirm_button_text="确认提交"))
                page.confirm_button.matches = count
                with self.assertRaises(browser.BrowserError):
                    adapter.upload(self.snapshot)
                self.assertEqual(page.upload_button.clicks, 1)
                self.assertEqual(page.inputs.files, [str(self.snapshot)])
                self.assertEqual(page.confirm_button.clicks, 0)
                self.assertNotIn("filechooser", page.listeners)

    def test_wrong_page_or_nonunique_upload_button_stops_before_clicking(self):
        page, adapter = self.adapter()
        page.url = "https://evil.com/competition/information/1300000312/submission"
        with self.assertRaises(browser.BrowserError):
            adapter.upload(self.snapshot)
        self.assertEqual(page.upload_button.clicks, 0)
        self.assertEqual(page.inputs.files, [])
        page, adapter = self.adapter()
        page.upload_button.matches = 2
        with self.assertRaises(browser.BrowserError):
            adapter.upload(self.snapshot)
        self.assertEqual(page.upload_button.clicks, 0)

    def test_table_html_returns_only_the_unique_visible_table(self):
        visible = FakeTable()
        page, adapter = self.adapter(tables=[FakeTable(visible=False), visible])
        with patch.object(browser.time, "monotonic", page.clock.monotonic):
            self.assertEqual(adapter.table_html(refresh=True), visible.html)
        self.assertEqual(page.reloads, 1)
        for tables in ([], [FakeTable(visible=False)], [FakeTable(), FakeTable()]):
            with self.subTest(count=len(tables)):
                page, adapter = self.adapter(tables=tables)
                with patch.object(browser.time, "monotonic", page.clock.monotonic), \
                     self.assertRaises(browser.BrowserError):
                    adapter.table_html()

    def test_hidden_attached_table_becomes_visible_without_reloading_again(self):
        table = FakeTable(visible=False)

        def reveal(page):
            table.visible = True

        page, adapter = self.adapter(tables=[table], on_wait=reveal)
        with patch.object(browser.time, "monotonic", page.clock.monotonic):
            self.assertEqual(adapter.table_html(refresh=True), VALID_TABLE)
        self.assertTrue(page.waits)
        self.assertEqual(page.reloads, 1)

    def test_visible_table_waits_for_delayed_valid_submission_rows(self):
        table = FakeTable(html=EMPTY_TABLE)

        def populate(page):
            if len(page.waits) >= 2:
                table.html = VALID_TABLE

        page, adapter = self.adapter(tables=[table], on_wait=populate)
        with patch.object(browser.time, "monotonic", page.clock.monotonic):
            self.assertEqual(adapter.table_html(), VALID_TABLE)
        self.assertGreaterEqual(len(page.waits), 2)
        self.assertEqual(page.reloads, 0)

    def test_zero_visible_table_times_out_using_bounded_fake_clock(self):
        page, adapter = self.adapter(tables=[FakeTable(visible=False)])
        with patch.object(browser.time, "monotonic", page.clock.monotonic), \
             self.assertRaises(browser.BrowserError):
            adapter.table_html(refresh=True)
        self.assertTrue(page.waits)
        self.assertGreaterEqual(page.clock.now, page.settings["action_timeout_ms"] / 1000)
        self.assertLessEqual(page.clock.now, 0.4)
        self.assertEqual(page.reloads, 1)

    def test_unique_explicit_empty_state_after_network_idle_allows_empty_html(self):
        table = FakeTable(html=EMPTY_TABLE)
        page, adapter = self.adapter(tables=[table], empty_blocks=[FakeTable()])
        with patch.object(browser.time, "monotonic", page.clock.monotonic):
            self.assertEqual(adapter.table_html(), EMPTY_TABLE)
        self.assertTrue(page.load_state_calls)
        self.assertGreaterEqual(table.reads, 2)  # Reobserve the table after idle.

    def test_empty_looking_table_without_explicit_empty_state_is_not_returned(self):
        page, adapter = self.adapter(tables=[FakeTable(html=EMPTY_TABLE)])
        with patch.object(browser.time, "monotonic", page.clock.monotonic), \
             self.assertRaises(browser.BrowserError):
            adapter.table_html()
        self.assertTrue(page.waits)

    def test_explicit_empty_state_while_network_is_loading_is_not_returned(self):
        page, adapter = self.adapter(tables=[FakeTable(html=EMPTY_TABLE)],
                                     empty_blocks=[FakeTable()], idle_error=True)
        with patch.object(browser.time, "monotonic", page.clock.monotonic), \
             self.assertRaises(browser.BrowserError):
            adapter.table_html()
        self.assertTrue(page.load_state_calls)

    def test_rows_arriving_during_idle_confirmation_are_read_instead_of_stale_empty_html(self):
        table = FakeTable(html=EMPTY_TABLE)

        def populate(page):
            table.html = VALID_TABLE
            page.empty_blocks.tables.clear()

        page, adapter = self.adapter(tables=[table], empty_blocks=[FakeTable()], on_idle=populate)
        with patch.object(browser.time, "monotonic", page.clock.monotonic):
            self.assertEqual(adapter.table_html(), VALID_TABLE)
        self.assertTrue(page.load_state_calls)
        self.assertGreaterEqual(table.reads, 2)

    def test_two_visible_tables_are_rejected_without_waiting(self):
        page, adapter = self.adapter(tables=[FakeTable(), FakeTable()])
        with patch.object(browser.time, "monotonic", page.clock.monotonic), \
             self.assertRaises(browser.BrowserError):
            adapter.table_html()
        self.assertEqual(page.waits, [])

    def test_empty_state_is_ambiguous_when_multiple_tables_are_attached(self):
        page, adapter = self.adapter(tables=[FakeTable(html=EMPTY_TABLE), FakeTable(visible=False)],
                                     empty_blocks=[FakeTable()])
        with patch.object(browser.time, "monotonic", page.clock.monotonic), \
             self.assertRaises(browser.BrowserError):
            adapter.table_html()
        self.assertTrue(page.waits)


if __name__ == "__main__":
    unittest.main()
