from datetime import date

from django.test import TestCase

from webcaf.webcaf.forms.review import (
    CommentsForm,
    CompanyDetailsForm,
    PreviewForm,
    RecommendationForm,
    ReviewPeriodForm,
)


class TestRecommendationForm(TestCase):
    """
    Form validation tests for the RecommendationForm.
    Both the fields are optional, so we only test the valid case.
    """

    def test_valid_with_no_fields(self):
        form = RecommendationForm(data={})
        self.assertTrue(form.is_valid())

    def test_valid_with_fields(self):
        form = RecommendationForm(data={"title": "T", "text": "Some rationale"})
        self.assertTrue(form.is_valid())

    def test_delete_flag_bypasses_validation(self):
        # Fields are optional, but ensure DELETE does not cause issues
        form = RecommendationForm(data={"DELETE": True})
        self.assertTrue(form.is_valid())

    def test_text_accepts_750_words(self):
        """Test that text field accepts exactly 750 words (boundary condition)."""
        text_750_words = " ".join(["word"] * 750)
        form = RecommendationForm(data={"title": "Title", "text": text_750_words})
        self.assertTrue(form.is_valid())

    def test_text_accepts_under_750_words(self):
        """Test that text field accepts text under 750 words."""
        text_500_words = " ".join(["word"] * 500)
        form = RecommendationForm(data={"title": "Title", "text": text_500_words})
        self.assertTrue(form.is_valid())

    def test_text_rejects_over_750_words(self):
        """Test that text field rejects text over 750 words."""
        text_751_words = " ".join(["word"] * 751)
        form = RecommendationForm(data={"title": "Title", "text": text_751_words})
        self.assertFalse(form.is_valid())
        self.assertIn("text", form.errors)
        self.assertIn("750", str(form.errors["text"]))


class TestPreviewForm(TestCase):
    """
    Test state change of the preview form.
    """

    def test_initial_is_preview_and_hidden(self):
        form = PreviewForm()
        self.assertEqual(form.fields["preview_status"].initial, "preview")
        # HiddenInput widgets don't render a visible field; check class path name
        self.assertIn("HiddenInput", form.fields["preview_status"].widget.__class__.__name__)

    def test_accepts_valid_choices(self):
        for choice in ("preview", "confirm", "change"):
            form = PreviewForm(data={"preview_status": choice})
            self.assertTrue(form.is_valid())

    def test_rejects_invalid_choice(self):
        form = PreviewForm(data={"preview_status": "invalid"})
        self.assertFalse(form.is_valid())
        self.assertIn("preview_status", form.errors)


class TestCommentsForm(TestCase):
    """
    Simple form validation test for the CommentsForm.
    """

    def test_requires_text(self):
        form = CommentsForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("text", form.errors)

    def test_valid_with_text(self):
        form = CommentsForm(data={"text": "A comment"})
        self.assertTrue(form.is_valid())

    def test_text_accepts_750_words(self):
        """Test that text field accepts exactly 750 words (boundary condition)."""
        text_750_words = " ".join(["word"] * 750)
        form = CommentsForm(data={"text": text_750_words})
        self.assertTrue(form.is_valid())

    def test_text_accepts_under_750_words(self):
        """Test that text field accepts text under 750 words."""
        text_500_words = " ".join(["word"] * 500)
        form = CommentsForm(data={"text": text_500_words})
        self.assertTrue(form.is_valid())

    def test_text_rejects_over_750_words(self):
        """Test that text field rejects text over 750 words."""
        text_751_words = " ".join(["word"] * 751)
        form = CommentsForm(data={"text": text_751_words})
        self.assertFalse(form.is_valid())
        self.assertIn("text", form.errors)
        self.assertIn("750", str(form.errors["text"]))


class TestReviewPeriodForm(TestCase):
    """
    Test the ReviewPeriodForm. Test the basic log around the date fields.
    """

    def test_prefixes(self):
        form = ReviewPeriodForm()
        self.assertEqual(form.prefixes(), ["start", "end"])

    def test_initial_dict_is_parsed_into_components(self):
        """Test new dict-based initialization format."""
        form = ReviewPeriodForm(initial={"text": {"start_date": "01/02/2023", "end_date": "05/03/2024"}})
        # Check that __init__ split dict dates into day/month/year components
        self.assertEqual(form.initial.get("start_date_day"), 1)
        self.assertEqual(form.initial.get("start_date_month"), 2)
        self.assertEqual(form.initial.get("start_date_year"), 2023)
        self.assertEqual(form.initial.get("end_date_day"), 5)
        self.assertEqual(form.initial.get("end_date_month"), 3)
        self.assertEqual(form.initial.get("end_date_year"), 2024)

    def test_initial_empty_dict_handled(self):
        """Test that empty dict in initial text doesn't cause errors."""
        form = ReviewPeriodForm(initial={"text": {}})
        # Should not raise any errors and should initialize with empty fields
        self.assertIsNone(form.initial.get("start_date_day"))
        self.assertIsNone(form.initial.get("end_date_day"))

    def test_clean_components_valid_date(self):
        year_ = date.today().year - 1
        form = ReviewPeriodForm(
            data={
                "start_date_day": 2,
                "start_date_month": 8,
                "start_date_year": year_,
                "end_date_day": 3,
                "end_date_month": 8,
                "end_date_year": year_,
            }
        )
        self.assertTrue(form.is_valid())
        # `text` should be set during clean as a dict
        self.assertEqual(form.cleaned_data["text"], {"start_date": f"02/08/{year_}", "end_date": f"03/08/{year_}"})

    def test_invalid_date_combination_sets_field_errors(self):
        # 31st February is invalid
        year_ = date.today().year - 1

        form = ReviewPeriodForm(
            data={
                "start_date_day": 31,
                "start_date_month": 2,
                "start_date_year": year_,
                "end_date_day": 1,
                "end_date_month": 3,
                "end_date_year": year_,
            }
        )
        self.assertFalse(form.is_valid())
        for key in ("start_date_day", "start_date_month", "start_date_year"):
            self.assertIn(key, form.errors)

    def test_start_date_must_be_before_end_date(self):
        # Start after end triggers a non-field error via ValidationError in clean()
        year_ = date.today().year - 1
        form = ReviewPeriodForm(
            data={
                "start_date_day": 10,
                "start_date_month": 5,
                "start_date_year": year_,
                "end_date_day": 9,
                "end_date_month": 5,
                "end_date_year": year_,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)
        self.assertIn("The start date must be before the end date", form.errors["__all__"])

    def test_missing_start_date_components(self):
        """Test that missing start date components returns None."""
        form = ReviewPeriodForm(
            data={
                "start_date_day": 10,
                # Missing month and year
                "end_date_day": 15,
                "end_date_month": 5,
                "end_date_year": 2024,
            }
        )
        self.assertFalse(form.is_valid())

    def test_missing_end_date_components(self):
        """Test that missing end date components returns None."""
        form = ReviewPeriodForm(
            data={
                "start_date_day": 10,
                "start_date_month": 5,
                "start_date_year": 2024,
                "end_date_day": 15,
                # Missing month and year
            }
        )
        self.assertFalse(form.is_valid())

    def test_invalid_day_zero(self):
        """Test that day 0 is invalid."""
        form = ReviewPeriodForm(
            data={
                "start_date_day": 0,
                "start_date_month": 5,
                "start_date_year": 2024,
                "end_date_day": 1,
                "end_date_month": 6,
                "end_date_year": 2024,
            }
        )
        self.assertFalse(form.is_valid())

    def test_invalid_day_32(self):
        """Test that day 32 is invalid."""
        form = ReviewPeriodForm(
            data={
                "start_date_day": 32,
                "start_date_month": 5,
                "start_date_year": 2024,
                "end_date_day": 1,
                "end_date_month": 6,
                "end_date_year": 2024,
            }
        )
        self.assertFalse(form.is_valid())

    def test_invalid_month_zero(self):
        """Test that month 0 is invalid."""
        form = ReviewPeriodForm(
            data={
                "start_date_day": 10,
                "start_date_month": 0,
                "start_date_year": 2024,
                "end_date_day": 1,
                "end_date_month": 1,
                "end_date_year": 2024,
            }
        )
        self.assertFalse(form.is_valid())

    def test_invalid_month_13(self):
        """Test that month 13 is invalid."""
        form = ReviewPeriodForm(
            data={
                "start_date_day": 10,
                "start_date_month": 13,
                "start_date_year": 2024,
                "end_date_day": 1,
                "end_date_month": 1,
                "end_date_year": 2024,
            }
        )
        self.assertFalse(form.is_valid())


class TestCompanyDetailsForm(TestCase):
    """
    Test the CompanyDetailsForm used for capturing company/assessor details.

    Tests the form validation, initialization from existing data, and clean method output.
    """

    def test_company_name_is_required(self):
        """Test that company_name field is required."""
        form = CompanyDetailsForm(
            data={
                "lead_assessor_email": "test@example.com"
                # Missing company_name
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("company_name", form.errors)

    def test_lead_assessor_email_is_required(self):
        """Test that lead_assessor_email field is required."""
        form = CompanyDetailsForm(
            data={
                "company_name": "Test Company"
                # Missing lead_assessor_email
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("lead_assessor_email", form.errors)

    def test_valid_with_required_fields_only(self):
        """Test that form is valid with only required fields."""
        form = CompanyDetailsForm(
            data={
                "company_name": "Test Company",
                "lead_assessor_email": "test@example.com",
                "lead_assessor_name": "Test Assessor",
            }
        )
        self.assertTrue(form.is_valid())

    def test_valid_with_all_fields(self):
        """Test that form is valid with all fields including optional ones."""
        form = CompanyDetailsForm(
            data={
                "company_name": "Test Company",
                "lead_assessor_email": "test@example.com",
                "lead_assessor_name": "Test Assessor",
                "company_address": "123 Test Street",
                "company_phone": "01234567890",
            }
        )
        self.assertTrue(form.is_valid())

    def test_company_address_is_optional(self):
        """Test that company_address is optional."""
        form = CompanyDetailsForm(
            data={
                "company_name": "Test Company",
                "lead_assessor_email": "test@example.com",
                "lead_assessor_name": "Test Assessor",
                # company_address is optional
            }
        )
        self.assertTrue(form.is_valid())

    def test_company_phone_is_optional(self):
        """Test that company_phone is optional."""
        form = CompanyDetailsForm(
            data={
                "company_name": "Test Company",
                "lead_assessor_email": "test@example.com",
                "lead_assessor_name": "Test Assessor"
                # company_phone is optional
            }
        )
        self.assertTrue(form.is_valid())

    def test_email_validation(self):
        """Test that lead_assessor_email validates email format."""
        form = CompanyDetailsForm(data={"company_name": "Test Company", "lead_assessor_email": "not-an-email"})
        self.assertFalse(form.is_valid())
        self.assertIn("lead_assessor_email", form.errors)

    def test_valid_email_formats(self):
        """Test various valid email formats."""
        valid_emails = [
            "test@example.com",
            "test.name@example.co.uk",
            "test+tag@example.com",
            "test_name@example.com",
        ]
        for email in valid_emails:
            form = CompanyDetailsForm(
                data={
                    "company_name": "Test Company",
                    "lead_assessor_email": email,
                    "lead_assessor_name": "Test Assessor",
                }
            )
            self.assertTrue(form.is_valid(), f"Email {email} should be valid")

    def test_initialization_from_empty_text_dict(self):
        """Test that form initializes correctly with empty text dict."""
        form = CompanyDetailsForm(initial={"text": {}})
        # Should not raise errors
        self.assertIsNotNone(form)

    def test_initialization_from_text_dict_with_data(self):
        """Test that form initializes from existing text dict."""
        initial_data = {
            "text": {
                "company_name": "Existing Company",
                "lead_assessor_email": "existing@example.com",
                "company_address": "456 Old Street",
                "company_phone": "09876543210",
            }
        }
        form = CompanyDetailsForm(initial=initial_data)

        # Check that initial values are set
        self.assertEqual(form.initial.get("company_name"), "Existing Company")
        self.assertEqual(form.initial.get("lead_assessor_email"), "existing@example.com")
        self.assertEqual(form.initial.get("company_address"), "456 Old Street")
        self.assertEqual(form.initial.get("company_phone"), "09876543210")

    def test_initialization_without_text_key(self):
        """Test that form initializes correctly when text key is not in initial."""
        form = CompanyDetailsForm(initial={})
        # Should not raise errors
        self.assertIsNotNone(form)

    def test_clean_returns_dict_with_name_and_email(self):
        """Test that clean method outputs dict with company_name and lead_assessor_email."""
        form = CompanyDetailsForm(
            data={
                "company_name": "Test Company",
                "lead_assessor_email": "test@example.com",
                "lead_assessor_name": "Test Assessor",
                "company_address": "123 Test Street",
                "company_phone": "01234567890",
            }
        )
        self.assertTrue(form.is_valid())

        # Check cleaned_data["text"] structure
        self.assertIn("text", form.cleaned_data)
        self.assertEqual(form.cleaned_data["text"]["company_name"], "Test Company")
        self.assertEqual(form.cleaned_data["text"]["lead_assessor_email"], "test@example.com")

    def test_clean_output_only_includes_name_and_email(self):
        """Test that clean method only includes company_name and lead_assessor_email in text dict."""
        form = CompanyDetailsForm(
            data={
                "company_name": "Test Company",
                "lead_assessor_email": "test@example.com",
                "lead_assessor_name": "Test Assessor",
                "company_address": "123 Test Street",  # Should not be in text dict
                "company_phone": "01234567890",  # Should not be in text dict
            }
        )
        self.assertTrue(form.is_valid())

        # text dict should only have name and email
        text_dict = form.cleaned_data["text"]
        self.assertEqual(len(text_dict), 3)
        self.assertIn("company_name", text_dict)
        self.assertIn("lead_assessor_email", text_dict)
        self.assertIn("lead_assessor_name", text_dict)
        self.assertNotIn("company_address", text_dict)
        self.assertNotIn("company_phone", text_dict)

    def test_company_name_max_length(self):
        """Test that company_name enforces max_length of 255."""
        long_name = "A" * 256
        form = CompanyDetailsForm(data={"company_name": long_name, "lead_assessor_email": "test@example.com"})
        self.assertFalse(form.is_valid())
        self.assertIn("company_name", form.errors)

    def test_lead_assessor_email_max_length(self):
        """Test that lead_assessor_email enforces max_length of 255."""
        # Create an email that exceeds 255 characters
        long_email = "a" * 240 + "@example.com"  # 253 chars total
        form = CompanyDetailsForm(
            data={"company_name": "Test", "lead_assessor_email": long_email, "lead_assessor_name": "Test Assessor"}
        )
        self.assertTrue(form.is_valid())  # Should be valid (under 255)

        # Now test with truly long email
        too_long_email = "a" * 250 + "@example.com"  # 263 chars total
        form = CompanyDetailsForm(data={"company_name": "Test", "lead_assessor_email": too_long_email})
        self.assertFalse(form.is_valid())
        self.assertIn("lead_assessor_email", form.errors)

    def test_company_address_max_length(self):
        """Test that company_address enforces max_length of 500."""
        long_address = "A" * 501
        form = CompanyDetailsForm(
            data={"company_name": "Test", "lead_assessor_email": "test@example.com", "company_address": long_address}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("company_address", form.errors)

    def test_company_phone_max_length(self):
        """Test that company_phone enforces max_length of 15."""
        long_phone = "1" * 16
        form = CompanyDetailsForm(
            data={"company_name": "Test", "lead_assessor_email": "test@example.com", "company_phone": long_phone}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("company_phone", form.errors)
