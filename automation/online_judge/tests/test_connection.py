"""Connection diagnostics without opening Chrome or any network connection."""

import io
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from online_judge import browser


ENDPOINT = "http://127.0.0.1:9222"
WEBSOCKET = "ws://127.0.0.1:9222/devtools/browser/test-session"


class ConnectionTests(unittest.TestCase):
    def opener(self, contents):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value = io.StringIO(contents)
        return opener

    def test_discovery_bypasses_proxy_without_changing_environment(self):
        opener = self.opener(json.dumps({"webSocketDebuggerUrl": WEBSOCKET}))
        with patch.dict(os.environ, {"HTTP_PROXY": "http://proxy.example:8080"}), \
             patch.object(browser, "build_opener", return_value=opener) as build:
            before = dict(os.environ)
            self.assertEqual(browser.cdp_websocket(ENDPOINT), WEBSOCKET)
            self.assertEqual(dict(os.environ), before)
            self.assertEqual(build.call_args.args[0].proxies, {})
        opener.open.assert_called_once_with(ENDPOINT + "/json/version", timeout=2)

    def test_unreachable_port_explains_the_cmd_browser_command(self):
        opener = MagicMock()
        opener.open.side_effect = URLError("connection refused")
        with patch.object(browser, "build_opener", return_value=opener):
            with self.assertRaises(browser.BrowserError) as caught:
                browser.cdp_websocket(ENDPOINT)
        self.assertIn(browser.START_COMMAND, str(caught.exception))
        self.assertIn(ENDPOINT, str(caught.exception))
        self.assertIn("connection refused", str(caught.exception))
        self.assertNotIn("judge.ps1", str(caught.exception))

    def test_non_chrome_and_remote_websocket_responses_are_rejected(self):
        invalid = ["not JSON", "[]", "{}"] + [
            json.dumps({"webSocketDebuggerUrl": address}) for address in (
                "ws://evil.example:9222/devtools/browser/test",
                "ws://127.0.0.1:9333/devtools/browser/test",
                "http://127.0.0.1:9222/devtools/browser/test",
                "ws://user:password@127.0.0.1:9222/devtools/browser/test",
                "ws://127.0.0.1:9222/devtools/page/test")]
        for contents in invalid:
            with self.subTest(contents=contents), \
                 patch.object(browser, "build_opener", return_value=self.opener(contents)), \
                 self.assertRaises(browser.BrowserError):
                browser.cdp_websocket(ENDPOINT)

    def test_availability_is_false_for_a_failed_discovery(self):
        with patch.object(browser, "cdp_websocket", side_effect=browser.BrowserError("offline")):
            self.assertFalse(browser.cdp_available(ENDPOINT))

    def test_handshake_failure_keeps_its_reason_and_does_not_claim_port_is_closed(self):
        manager = MagicMock()
        runtime = manager.__enter__.return_value
        runtime.chromium.connect_over_cdp.side_effect = RuntimeError("handshake failed")
        module = SimpleNamespace(sync_playwright=MagicMock(return_value=manager))
        with patch.dict(sys.modules, {"playwright.sync_api": module}), \
             patch.object(browser, "cdp_websocket", return_value=WEBSOCKET):
            with self.assertRaises(browser.BrowserError) as caught:
                with browser.connect({"cdp_url": ENDPOINT}):
                    self.fail("Connection must fail before yielding a page")
        runtime.chromium.connect_over_cdp.assert_called_once_with(WEBSOCKET, timeout=10000)
        self.assertIn("handshake failed", str(caught.exception))
        self.assertNotIn(browser.START_COMMAND, str(caught.exception))


if __name__ == "__main__":
    unittest.main()
