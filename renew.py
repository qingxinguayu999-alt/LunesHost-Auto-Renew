#!/usr/bin/env python3
"""Log in to the Lunes Host dashboard to keep an authorized free service active."""

from __future__ import annotations

import os
import re
import sys
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from playwright.sync_api import Page


DASHBOARD_URL = "https://betadash.lunes.host/"
ALLOWED_HOST = "betadash.lunes.host"
LOGIN_PATH = "/login"
TIMEOUT_MS = 30_000


class RenewalError(RuntimeError):
    """A safe, user-facing renewal failure."""


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


def on_login_page(page: "Page") -> bool:
    path = urlparse(page.url).path.rstrip("/")
    email = page.locator('input[name="email"]')
    password = page.locator('input[name="password"]')
    return path == LOGIN_PATH or (email.count() == 1 and password.count() == 1)


def verify_dashboard(page: "Page") -> None:
    parsed = urlparse(page.url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        raise RenewalError("Refused an unexpected redirect outside the Lunes dashboard.")
    if on_login_page(page):
        raise RenewalError(
            "Login was not accepted. Check the LUNES_EMAIL and LUNES_PASSWORD secrets."
        )

    # The dashboard UI may change, so verify multiple stable, non-personal signals.
    body = page.locator("body").inner_text(timeout=TIMEOUT_MS)
    dashboard_signals = (
        "Open Panel",
        "Server Control",
        "Free Tier",
        "Betadash",
        "Transfer Node",
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
            verify_dashboard(page)
        finally:
            # Never persist cookies, traces, HTML, or screenshots.
            context.close()
            browser.close()


def main() -> int:
    email = ""
    password = ""
    try:
        email = required_secret("LUNES_EMAIL")
        password = required_secret("LUNES_PASSWORD")
        mask_secret(email)
        mask_secret(password)
        print("Starting authorized Lunes dashboard sign-in.")
        renew(email, password)
        print("Success: Lunes dashboard login was verified.")
        return 0
    except RenewalError as exc:
        print(f"Error: {redact(str(exc), (email, password))}", file=sys.stderr)
        return 1
    except Exception:
        # Avoid printing raw browser exceptions because they can include page data.
        print("Error: unexpected browser failure; no page data was logged.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
