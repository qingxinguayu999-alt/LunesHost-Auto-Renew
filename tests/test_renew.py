import unittest

from renew import redact


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


if __name__ == "__main__":
    unittest.main()
