import unittest
from datetime import datetime, timezone

from renew import is_authenticated_dashboard_url, notification_text, redact


class RedactionTests(unittest.TestCase):
    def test_redacts_explicit_secrets(self) -> None:
        message = "account user@example.com used password secret-value"
        self.assertEqual(
            redact(message, ("user@example.com", "secret-value")),
            "account [REDACTED] used password [REDACTED]",
        )

    def test_redacts_other_email_addresses(self) -> None:
        self.assertEqual(
            redact("Contact other.user+tag@example.co.uk"),
            "Contact [REDACTED_EMAIL]",
        )


class NotificationTests(unittest.TestCase):
    def test_success_notification_contains_only_generic_status(self) -> None:
        message = notification_text(
            True, datetime(2026, 9, 15, 3, 17, tzinfo=timezone.utc)
        )
        self.assertIn("自动续期成功", message)
        self.assertIn("2026-09-15 03:17:00", message)
        self.assertNotIn("@", message)

    def test_failure_notification_is_generic(self) -> None:
        message = notification_text(
            False, datetime(2026, 9, 15, 3, 17, tzinfo=timezone.utc)
        )
        self.assertIn("自动续期失败", message)
        self.assertIn("脱敏日志", message)


class DashboardUrlTests(unittest.TestCase):
    def test_accepts_protected_dashboard_routes(self) -> None:
        self.assertTrue(is_authenticated_dashboard_url("https://betadash.lunes.host/"))
        self.assertTrue(
            is_authenticated_dashboard_url("https://betadash.lunes.host/server/example")
        )

    def test_rejects_login_and_external_routes(self) -> None:
        self.assertFalse(
            is_authenticated_dashboard_url("https://betadash.lunes.host/login")
        )
        self.assertFalse(is_authenticated_dashboard_url("https://example.com/"))

if __name__ == "__main__":
    unittest.main()
