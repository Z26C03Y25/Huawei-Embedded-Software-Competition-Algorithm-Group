"""Chrome connection and page adapter. Importing this module never opens Chrome."""

from __future__ import annotations

from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import time
from urllib.parse import urlsplit
from urllib.request import build_opener, ProxyHandler

from .api import API_URL, ApiAuthenticationError, ApiResponseError, parse_api_response
from .records import parse_submission_html


BASE = Path(__file__).resolve().parent
DEFAULT_URL = "https://developer.huaweicloud.com/competition/information/1300000312/submission"


class BrowserError(RuntimeError):
    pass


def load_config(path: Path | None = None) -> dict:
    config = json.loads((path or BASE / "config.json").read_text(encoding="utf-8"))
    endpoint = urlsplit(config["cdp_url"])
    if endpoint.scheme != "http" or endpoint.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("cdp_url must be an HTTP endpoint on this computer's loopback interface")
    if endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
        raise ValueError("cdp_url must not contain credentials, query parameters, or a fragment")
    if not endpoint.port or not 1 <= endpoint.port <= 65535:
        raise ValueError("cdp_url must specify a port between 1 and 65535")
    target = urlsplit(config["submission_url"])
    if target.scheme != "https" or target.hostname != "developer.huaweicloud.com":
        raise ValueError("submission_url must use HTTPS on developer.huaweicloud.com")
    if (target.path.rstrip("/") != urlsplit(DEFAULT_URL).path or target.username or
            target.password or target.query or target.fragment or target.port not in {None, 443}):
        raise ValueError("submission_url must identify competition 1300000312's submission page")
    if not 0 < float(config["poll_interval_seconds"]) <= 30:
        raise ValueError("poll_interval_seconds must be in (0, 30]")
    if float(config["timeout_seconds"]) <= 0 or int(config["action_timeout_ms"]) <= 0:
        raise ValueError("timeouts must be positive")
    if config.get("score_source", "auto") not in {"auto", "api", "dom"}:
        raise ValueError("score_source must be auto, api, or dom")
    if type(config.get("capture_ranking_on_completion", False)) is not bool:
        raise ValueError("capture_ranking_on_completion must be a boolean")
    for key in ("profile_directory", "runs_directory"):
        resolved = (BASE / config[key]).resolve()
        if not resolved.is_relative_to(BASE) or resolved == BASE:
            raise ValueError(f"{key} must be a dedicated subdirectory of online_judge")
        config[key] = str(resolved)
    return config


def chrome_executable(config: dict) -> Path:
    path = Path(config["chrome_path"])
    return path / "chrome.exe" if path.is_dir() or path.suffix.lower() != ".exe" else path


def is_submission_url(actual: str, expected: str) -> bool:
    lhs, rhs = urlsplit(actual), urlsplit(expected)
    return (lhs.scheme, lhs.hostname, lhs.port, lhs.path.rstrip("/")) == (
        rhs.scheme, rhs.hostname, rhs.port, rhs.path.rstrip("/"))


START_COMMAND = r"automation\online_judge\.venv\Scripts\python.exe automation\online_judge\judge.py browser"


def cdp_websocket(endpoint: str) -> str:
    """Discover Chrome directly, without sending loopback traffic to a proxy."""
    try:
        opener = build_opener(ProxyHandler({}))
        with opener.open(endpoint.rstrip("/") + "/json/version", timeout=2) as response:
            data = json.load(response)
    except OSError as exc:
        raise BrowserError(f"无法访问 Chrome 调试服务 {endpoint}。请先在仓库根目录的 CMD 中运行："
                           f"\n{START_COMMAND}\n在弹出的专用 Chrome 中手动登录并保持窗口开启。"
                           f"\n连接原因：{exc}") from exc
    except ValueError as exc:
        raise BrowserError(f"{endpoint} 未返回有效的 Chrome CDP JSON；请检查调试端口是否被其他程序占用。") from exc
    websocket = data.get("webSocketDebuggerUrl") if isinstance(data, dict) else None
    try:
        parsed = urlsplit(websocket) if isinstance(websocket, str) else None
        valid = parsed is not None and parsed.scheme in {"ws", "wss"} and \
            parsed.hostname in {"127.0.0.1", "localhost", "::1"} and \
            parsed.port == urlsplit(endpoint).port and \
            not (parsed.username or parsed.password or parsed.query or parsed.fragment) and \
            parsed.path.startswith("/devtools/browser/")
    except ValueError:
        valid = False
    if not valid:
        raise BrowserError(f"{endpoint} 未返回有效的本机 Chrome WebSocket 地址；请检查调试端口。")
    return websocket


def cdp_available(endpoint: str) -> bool:
    try:
        cdp_websocket(endpoint)
        return True
    except BrowserError:
        return False


def start_browser(config: dict) -> dict:
    """Start a dedicated, persistent Chrome profile; do not inspect other profiles."""
    executable = chrome_executable(config)
    if not executable.is_file():
        raise BrowserError(f"Chrome was not found: {executable}. Edit config.json chrome_path.")
    if cdp_available(config["cdp_url"]):
        return {"state": "browser_ready", "started": False, "cdp_url": config["cdp_url"]}
    profile = Path(config["profile_directory"])
    profile.mkdir(parents=True, exist_ok=True)
    port = urlsplit(config["cdp_url"]).port
    command = [str(executable), f"--remote-debugging-port={port}",
               "--remote-debugging-address=127.0.0.1", f"--user-data-dir={profile}",
               "--no-first-run", "--no-default-browser-check", config["submission_url"]]
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if cdp_available(config["cdp_url"]):
            return {"state": "browser_ready", "started": True, "pid": process.pid,
                    "cdp_url": config["cdp_url"], "profile_directory": str(profile),
                    "next": "Complete login manually in this Chrome window, then run latest."}
        time.sleep(0.25)
    raise BrowserError("Chrome did not expose its local debug port. Close only the dedicated "
                       "online_judge Chrome window if already open, then retry browser. "
                       "Do not delete Chrome lock files while Chrome is running.")


def doctor(config: dict) -> dict:
    """Filesystem/dependency checks only; no browser is started or contacted."""
    executable = chrome_executable(config)
    installed = importlib.util.find_spec("playwright") is not None
    return {"chrome_executable": str(executable), "chrome_exists": executable.is_file(),
            "playwright_installed": installed, "submission_url": config["submission_url"],
            "cdp_url": config["cdp_url"], "profile_directory": config["profile_directory"],
            "ready": executable.is_file() and installed}


class SubmissionPage:
    def __init__(self, page, config: dict):
        self.page, self.config = page, config
        self._api_response = None
        self._consumed_api_response = None
        self._listening = config.get("score_source", "auto") != "dom"
        page.set_default_timeout(int(config["action_timeout_ms"]))
        if self._listening:
            page.on("response", self._on_api_response)

    @staticmethod
    def _is_api_response(response) -> bool:
        return response.url == API_URL and response.request.method == "POST"

    def _on_api_response(self, response) -> None:
        if self._is_api_response(response):
            # Keep only an in-memory response handle. Never inspect request
            # headers, cookies, CSRF values or the request body.
            self._api_response = response

    def close(self) -> None:
        """Detach our listener, leaving the browser, page and login open."""
        if self._listening:
            self.page.remove_listener("response", self._on_api_response)
            self._listening = False

    def records(self, *, refresh: bool = False):
        """Read the site's own score response, with a bounded DOM fallback.

        The frontend sends its authenticated POST itself. We do not copy login
        credentials, guess a payload or issue an extra authenticated HTTP call.
        refresh=False must never reload an in-flight upload's page.
        """
        mode = self.config.get("score_source", "auto")
        if mode == "dom":
            return parse_submission_html(self.table_html(refresh=refresh))
        self.ensure_ready()
        failure = None
        if refresh:
            # Clear a response from an earlier observation before refreshing.
            self._api_response = None
            try:
                with self.page.expect_response(self._is_api_response,
                                               timeout=int(self.config["action_timeout_ms"])) as event:
                    self.page.reload(wait_until="domcontentloaded")
                self._api_response = event.value
            except Exception:
                failure = ApiResponseError("未观测到本次刷新对应的查分接口响应")
        else:
            # Sync Playwright dispatches response events while an API call is
            # running. Pump pending events without refreshing the upload page.
            self.page.wait_for_timeout(1)
        response = self._api_response
        if response is not None and response is not self._consumed_api_response:
            self._consumed_api_response = response
            try:
                if response.status in {401, 403}:
                    raise ApiAuthenticationError("查分接口登录失效，请在专用 Chrome 中重新登录")
                try:
                    payload = response.json()
                except Exception:
                    # Do not expose an HTML login page, raw body, or tokens in
                    # a JSON parsing exception or fallback log.
                    raise ApiResponseError("查分接口未返回有效 JSON") from None
                return parse_api_response(payload, http_status=response.status)
            except ApiAuthenticationError:
                raise BrowserError("查分接口登录失效，请在专用 Chrome 中手动重新登录") from None
            except ApiResponseError as exc:
                failure = exc
        if mode == "api":
            if not refresh and failure is None:
                # No fresh API observation yet. Do not treat a cached final
                # score as a second independent confirmation or reload here.
                return []
            raise BrowserError(str(failure or "没有新的查分接口响应")) from None
        # A valid API [] is returned above. Only an unavailable/unknown API
        # response falls back; this does not perform a second refresh.
        return parse_submission_html(self.table_html(refresh=False))

    def ensure_ready(self) -> None:
        if not is_submission_url(self.page.url, self.config["submission_url"]):
            raise BrowserError("The browser is on a different page or a login page. "
                               "Complete login manually in the dedicated Chrome window.")
        button = self.page.get_by_role("button", name=self.config["upload_button_text"], exact=True)
        button.wait_for(state="visible")
        if button.count() != 1:
            raise BrowserError("Expected exactly one Upload Work button; inspect the page before retrying.")

    def table_html(self, *, refresh: bool = False) -> str:
        if refresh:
            self.page.reload(wait_until="domcontentloaded")
        self.ensure_ready()
        selector = self.config["table_selector"]
        timeout = int(self.config["action_timeout_ms"])
        deadline = time.monotonic() + timeout / 1000
        try:
            self.page.locator(selector).first.wait_for(state="attached", timeout=timeout)
        except Exception as exc:
            raise BrowserError(f"未找到成绩表格 DOM，请检查 table_selector：{selector}") from exc
        idle_confirmed = False
        detail = "Waiting for the submission table to render"
        while True:
            # TinyGrid attaches an empty zero-height table before its history
            # request completes. Attached is not the same as readable. Re-query
            # after short waits, without reloading and restarting that request.
            matches = self.page.locator(selector).all()
            visible = [item for item in matches if item.is_visible()]
            if len(visible) > 1:
                raise BrowserError(f"Expected one visible submission table, found {len(visible)}. "
                                   "Check config.json table_selector.")
            table = visible[0] if visible else (matches[0] if len(matches) == 1 else None)
            html = table.evaluate("element => element.outerHTML") if table is not None else ""
            try:
                records = parse_submission_html(html)
            except ValueError as exc:
                records = []
                detail = f"Waiting for complete submission row fields: {exc}"
            if len(visible) == 1 and records:
                return html

            # A genuinely empty grid may keep its body table at zero height.
            # Accept it only with an explicit visible empty-state message and
            # settled network activity, then check the DOM again before return.
            empty_selector = self.config.get(
                "empty_selector", "div.tiny-grid__body-wrapper .tiny-grid__empty-block")
            empty = [item for item in self.page.locator(empty_selector).all() if item.is_visible()]
            unpopulated = table is not None and re.search(r"<tr(?:\s|>)", html, re.I) is None
            if len(matches) == 1 and unpopulated and len(empty) == 1:
                if idle_confirmed:
                    return html
                remaining = deadline - time.monotonic()
                if remaining > 0:
                    try:
                        self.page.wait_for_load_state("networkidle", timeout=max(1, min(500, int(remaining * 1000))))
                    except Exception as exc:
                        detail = f"Waiting for submission history to finish loading: {type(exc).__name__}"
                    else:
                        idle_confirmed = True
                        continue
            else:
                idle_confirmed = False
                detail = (f"matched tables={len(matches)}, visible tables={len(visible)}, "
                          f"valid rows={len(records)}; history is not ready yet")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise BrowserError(f"等待成绩表格加载超时（{timeout} ms）：{detail}。"
                                   "请确认已登录且提交记录区域加载完成，再重试 latest。")
            self.page.wait_for_timeout(max(1, min(100, int(remaining * 1000))))

    def upload(self, snapshot: Path) -> None:
        """Click once and choose the snapshot once. Never retry an uncertain upload."""
        self.ensure_ready()
        choosers = []

        def on_filechooser(chooser):
            choosers.append(chooser)

        self.page.on("filechooser", on_filechooser)
        try:
            self.page.get_by_role("button", name=self.config["upload_button_text"], exact=True).click()
            deadline = time.monotonic() + self.config["action_timeout_ms"] / 1000
            selected = False
            while time.monotonic() < deadline:
                if choosers:
                    if len(choosers) != 1:
                        raise BrowserError("Multiple file chooser events; upload outcome is uncertain.")
                    choosers[0].set_files(str(snapshot))
                    selected = True
                    break
                inputs = self.page.locator(self.config["file_input_selector"])
                if inputs.count() == 1:
                    inputs.set_input_files(str(snapshot))
                    selected = True
                    break
                if inputs.count() > 1:
                    raise BrowserError("Multiple file inputs; narrow file_input_selector in config.json.")
                self.page.wait_for_timeout(100)
            if not selected:
                raise BrowserError("No file chooser or unique file input appeared. "
                                   "Upload may be incomplete; use wait to inspect, not submit again.")
            # Some sites submit as soon as a file is selected. An additional
            # confirmation is used only when its exact label was configured.
            confirm = self.config.get("confirm_button_text")
            if confirm:
                button = self.page.get_by_role("button", name=confirm, exact=True)
                if button.count() != 1:
                    raise BrowserError("Configured upload confirmation button is not unique.")
                button.click()
        finally:
            self.page.remove_listener("filechooser", on_filechooser)


@contextmanager
def connect(config: dict):
    websocket = cdp_websocket(config["cdp_url"])
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise BrowserError("Playwright is missing. Run automation/online_judge/setup.ps1 first.") from exc
    with sync_playwright() as runtime:
        try:
            browser = runtime.chromium.connect_over_cdp(websocket, timeout=10000)
        except Exception as exc:
            raise BrowserError(f"Chrome 调试端口 {config['cdp_url']} 可访问，但 Playwright 连接失败。"
                               f"请检查本机代理或调试连接。原因：{type(exc).__name__}: {exc}") from exc
        matches = [page for context in browser.contexts for page in context.pages
                   if is_submission_url(page.url, config["submission_url"])]
        if len(matches) > 1:
            raise BrowserError("Multiple competition submission tabs are open. Keep one in this Chrome profile.")
        if matches:
            page = matches[0]
        else:
            if not browser.contexts:
                raise BrowserError("Chrome has no accessible browser context; restart the dedicated profile.")
            page = browser.contexts[0].new_page()
            page.goto(config["submission_url"], wait_until="domcontentloaded")
        adapter = SubmissionPage(page, config)
        adapter.ensure_ready()
        # Stop the Playwright transport on exit, but leave Chrome and its login
        # session open. Do not call browser.close() on the attached browser.
        try:
            yield adapter
        finally:
            adapter.close()
