from django.test import TestCase

from webcaf.webcaf.forms.review import (
    CommentsForm,
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


class TestReviewPeriodForm(TestCase):
    """
    Test the ReviewPeriodForm. Test the basic log around the date fields.
    """

    def test_prefixes(self):
        form = ReviewPeriodForm()
        self.assertEqual(form.prefixes(), ["start", "end"])

    def test_initial_text_is_parsed_into_components(self):
        form = ReviewPeriodForm(initial={"text": "01/02/2023 - 05/03/2024"})
        # Check that __init__ split text into day/month/year components
        self.assertEqual(form.initial.get("start_date_day"), 1)
        self.assertEqual(form.initial.get("start_date_month"), 2)
        self.assertEqual(form.initial.get("start_date_year"), 2023)
        self.assertEqual(form.initial.get("end_date_day"), 5)
        self.assertEqual(form.initial.get("end_date_month"), 3)
        self.assertEqual(form.initial.get("end_date_year"), 2024)

    def test_clean_components_valid_date(self):
        form = ReviewPeriodForm(
            data={
                "start_date_day": 2,
                "start_date_month": 8,
                "start_date_year": 2023,
                "end_date_day": 3,
                "end_date_month": 8,
                "end_date_year": 2023,
            }
        )
        self.assertTrue(form.is_valid())
        # `text` should be set during clean
        self.assertEqual(form.cleaned_data["text"], "02/08/2023 - 03/08/2023")

    def test_invalid_date_combination_sets_field_errors(self):
        # 31st February is invalid
        form = ReviewPeriodForm(
            data={
                "start_date_day": 31,
                "start_date_month": 2,
                "start_date_year": 2023,
                "end_date_day": 1,
                "end_date_month": 3,
                "end_date_year": 2023,
            }
        )
        self.assertFalse(form.is_valid())
        for key in ("start_date_day", "start_date_month", "start_date_year"):
            self.assertIn(key, form.errors)

    def test_start_date_must_be_before_end_date(self):
        # Start after end triggers a non-field error via ValidationError in clean()
        form = ReviewPeriodForm(
            data={
                "start_date_day": 10,
                "start_date_month": 5,
                "start_date_year": 2024,
                "end_date_day": 9,
                "end_date_month": 5,
                "end_date_year": 2024,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)
        self.assertIn("The start date must be before the end date", form.errors["__all__"])
