#!/usr/bin/env python3
"""Log in to the Lunes Host dashboard to keep an authorized free service active."""

from __future__ import annotations

import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from playwright.sync_api import Page


DASHBOARD_URL = "https://betadash.lunes.host/"
ALLOWED_HOST = "betadash.lunes.host"
LOGIN_PATH = "/login"
TIMEOUT_MS = 30_000
AUTHENTICATED_PATHS = {"", "/", "/dashboard", "/servers"}


class RenewalError(RuntimeError):
    """A safe, user-facing renewal failure."""


class NotificationError(RuntimeError):
    """A safe, user-facing Telegram notification failure."""


def required_secret(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RenewalError(f"Missing required GitHub Actions secret: {name}")
    return value


def mask_secret(value: str) -> None:
    # GitHub Actions masks later occurrences of this value in job logs.
    print(f"::add-mask::{value}")


def redact(text: str, secrets: tuple[str, ...] = ()) -> str:
    """Remove credentials and email-like strings before a message reaches logs."""
    safe = text
    for secret in secrets:
        if secret:
            safe = safe.replace(secret, "[REDACTED]")
    return re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", safe)


def notification_text(success: bool, now: datetime | None = None) -> str:
    """Build a notification containing no account or server identifiers."""
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    status = "成功" if success else "失败"
    icon = "✅" if success else "❌"
    guidance = "登录保活已验证。" if success else "请查看 GitHub Actions 的脱敏日志。"
    return (
        f"{icon} Lunes Host 自动续期{status}\n"
        f"{guidance}\n"
        f"UTC 时间：{timestamp:%Y-%m-%d %H:%M:%S}"
    )


def send_telegram(bot_token: str, chat_id: str, message: str) -> None:
    """Send a Telegram message without logging its URL, response, or secrets."""
    token_path = urllib.parse.quote(bot_token, safe=":")
    url = f"https://api.telegram.org/bot{token_path}/sendMessage"
    payload = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": message, "disable_web_page_preview": "true"}
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if not 200 <= response.status < 300:
                raise NotificationError("Telegram returned a non-success status.")
    except Exception as exc:
        raise NotificationError("Telegram notification could not be sent.") from exc


def on_login_page(page: "Page") -> bool:
    path = urlparse(page.url).path.rstrip("/")
    email = page.locator('input[name="email"]')
    password = page.locator('input[name="password"]')
    return path == LOGIN_PATH or (email.count() == 1 and password.count() == 1)


def is_authenticated_dashboard_url(url: str) -> bool:
    """Recognize protected Betadash routes without relying on translated UI text."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        return False
    path = parsed.path.rstrip("/")
    return path in AUTHENTICATED_PATHS or path.startswith("/server/")


def verify_dashboard(page: "Page") -> None:
    parsed = urlparse(page.url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        raise RenewalError("Refused an unexpected redirect outside the Lunes dashboard.")
    if on_login_page(page):
        raise RenewalError(
            "Login was not accepted. Check the LUNES_EMAIL and LUNES_PASSWORD secrets."
        )

    # Betadash protects its root route: unauthenticated visits are redirected to
    # /login. Reaching a protected route with no login form is positive evidence
    # even while the dashboard's client-side text is still loading.
    if is_authenticated_dashboard_url(page.url):
        return

    # Fallback for future authenticated routes. Include both English and current
    # Chinese labels because browsers or the site may localize the dashboard.
    body = page.locator("body").inner_text(timeout=TIMEOUT_MS)
    dashboard_signals = (
        "Open Panel",
        "Server Control",
        "Free Tier",
        "Betadash",
        "Transfer Node",
        "开放面板",
        "服务器控制",
        "免费等级",
        "传输节点",
        "删除服务器",
        "创建于",
    )
    if not any(signal.casefold() in body.casefold() for signal in dashboard_signals):
        raise RenewalError(
            "Login may have succeeded, but the expected dashboard could not be verified."
        )


def renew(email: str, password: str) -> None:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            locale="en-US",
            timezone_id="UTC",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        try:
            page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=TIMEOUT_MS)

            if on_login_page(page):
                page.locator('input[name="email"]').fill(email)
                page.locator('input[name="password"]').fill(password)
                page.locator('button[type="submit"]').click()

                try:
                    page.wait_for_url(
                        re.compile(
                            r"^https://betadash\.lunes\.host/(?!login(?:[/?#]|$)).*"
                        ),
                        timeout=TIMEOUT_MS,
                    )
                except PlaywrightTimeoutError:
                    # Verification below produces a stable, credential-free error.
                    pass

            page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_MS)
            page.wait_for_timeout(2_000)
            verify_dashboard(page)
        finally:
            # Never persist cookies, traces, HTML, or screenshots.
            context.close()
            browser.close()


def main() -> int:
    email = ""
    password = ""
    tg_bot_token = os.environ.get("TG_BOT_TOKEN", "").strip()
    tg_chat_id = os.environ.get("TG_CHAT_ID", "").strip()
    telegram_enabled = bool(tg_bot_token and tg_chat_id)
    success = False
    exit_code = 1

    for value in (tg_bot_token, tg_chat_id):
        if value:
            mask_secret(value)
    if bool(tg_bot_token) != bool(tg_chat_id):
        print(
            "Warning: Telegram notifications require both TG_BOT_TOKEN and TG_CHAT_ID; "
            "notifications are disabled.",
            file=sys.stderr,
        )

    try:
        email = required_secret("LUNES_EMAIL")
        password = required_secret("LUNES_PASSWORD")
        mask_secret(email)
        mask_secret(password)
        print("Starting authorized Lunes dashboard sign-in.")
        renew(email, password)
        print("Success: Lunes dashboard login was verified.")
        success = True
        exit_code = 0
    except RenewalError as exc:
        print(f"Error: {redact(str(exc), (email, password))}", file=sys.stderr)
    except Exception:
        # Avoid printing raw browser exceptions because they can include page data.
        print("Error: unexpected browser failure; no page data was logged.", file=sys.stderr)
    finally:
        if telegram_enabled:
            try:
                send_telegram(
                    tg_bot_token,
                    tg_chat_id,
                    notification_text(success),
                )
                print("Telegram notification sent.")
            except NotificationError:
                # Renewal status remains authoritative when Telegram is unavailable.
                print(
                    "Warning: Telegram notification failed; no response data was logged.",
                    file=sys.stderr,
                )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
