"""
Tests for mask_email utility function.

This module tests the email masking functionality used for privacy protection in logs.
"""

from django.test import TestCase

from webcaf.webcaf.utils import mask_email


class MaskEmailTest(TestCase):
    """Test suite for mask_email function."""

    def test_mask_single_email(self):
        """Test masking a single email address."""
        text = "user@example.com"
        result = mask_email(text)
        self.assertEqual(result, "us***@example.com")

    def test_mask_long_email_username(self):
        """Test masking email with long username."""
        text = "verylongusername@example.com"
        result = mask_email(text)
        self.assertEqual(result, "ve***@example.com")

    def test_mask_short_email_username(self):
        """Test masking email with short username."""
        text = "ab@example.com"
        result = mask_email(text)
        self.assertEqual(result, "ab***@example.com")

    def test_mask_single_character_username(self):
        """Test masking email with single character username."""
        text = "a@example.com"
        result = mask_email(text)
        self.assertEqual(result, "a***@example.com")

    def test_mask_email_in_sentence(self):
        """Test masking email within a sentence."""
        text = "Send email to user@example.com for verification"
        result = mask_email(text)
        self.assertEqual(result, "Send email to us***@example.com for verification")

    def test_mask_multiple_emails(self):
        """Test masking multiple email addresses in text."""
        text = "Contact user1@example.com or user2@domain.org"
        result = mask_email(text)
        self.assertEqual(result, "Contact us***@example.com or us***@domain.org")

    def test_mask_email_with_plus_sign(self):
        """Test masking email with plus sign in username."""
        text = "user+tag@example.com"
        result = mask_email(text)
        self.assertEqual(result, "us***@example.com")

    def test_mask_email_with_dots(self):
        """Test masking email with dots in username."""
        text = "first.last@example.com"
        result = mask_email(text)
        self.assertEqual(result, "fi***@example.com")

    def test_mask_email_with_numbers(self):
        """Test masking email with numbers in username."""
        text = "user123@example.com"
        result = mask_email(text)
        self.assertEqual(result, "us***@example.com")

    def test_mask_email_with_subdomain(self):
        """Test masking email with subdomain."""
        text = "user@mail.example.com"
        result = mask_email(text)
        self.assertEqual(result, "us***@mail.example.com")

    def test_mask_email_with_gov_uk_domain(self):
        """Test masking email with .gov.uk domain."""
        text = "user@department.gov.uk"
        result = mask_email(text)
        self.assertEqual(result, "us***@department.gov.uk")

    def test_mask_no_email_in_text(self):
        """Test that text without email remains unchanged."""
        text = "This is a regular text without any email"
        result = mask_email(text)
        self.assertEqual(result, text)

    def test_mask_empty_string(self):
        """Test masking empty string."""
        text = ""
        result = mask_email(text)
        self.assertEqual(result, "")

    def test_mask_email_preserves_surrounding_text(self):
        """Test that surrounding text is preserved exactly."""
        text = "User: user@example.com, Status: Active"
        result = mask_email(text)
        self.assertEqual(result, "User: us***@example.com, Status: Active")

    def test_mask_email_with_special_characters_in_username(self):
        """Test masking email with allowed special characters."""
        text = "user_name-test@example.com"
        result = mask_email(text)
        self.assertEqual(result, "us***@example.com")

    def test_mask_email_case_sensitive(self):
        """Test that masking preserves case in first two characters."""
        text = "User@example.com"
        result = mask_email(text)
        self.assertEqual(result, "Us***@example.com")

    def test_mask_multiple_emails_different_lengths(self):
        """Test masking multiple emails with different username lengths."""
        text = "a@test.com and verylongname@test.com"
        result = mask_email(text)
        self.assertEqual(result, "a***@test.com and ve***@test.com")

    def test_mask_email_in_log_message(self):
        """Test masking email in typical log message format."""
        text = "Successfully sent OTP to user@example.com"
        result = mask_email(text)
        self.assertEqual(result, "Successfully sent OTP to us***@example.com")

    def test_mask_email_in_error_message(self):
        """Test masking email in error message format."""
        text = "Failed to send email to admin@company.com: Connection timeout"
        result = mask_email(text)
        self.assertEqual(result, "Failed to send email to ad***@company.com: Connection timeout")
