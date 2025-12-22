from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.views.generic import UpdateView

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import Assessment, Review
from webcaf.webcaf.views.assessor.util import BaseReviewMixin, YesNoForm


class DummyView(BaseReviewMixin, UpdateView):
    """Minimal concrete to exercise mixin methods that don't hit the DB."""

    model = Review

    def __init__(self):
        # simulate attributes the mixin might rely on
        super().__init__()
        self.request = None


class TestYesNoForm(TestCase):
    """
    Test the utility form used to confirm a yes/no action.
    """

    def test_initial_is_no_and_label_overridden(self):
        form = YesNoForm(yes_no_label="Proceed?")
        self.assertEqual(form.fields["yes_no"].initial, "no")
        self.assertEqual(form.fields["yes_no"].label, "Proceed?")

    def test_required_validation(self):
        form = YesNoForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("yes_no", form.errors)

        form_yes = YesNoForm(data={"yes_no": "yes"})
        self.assertTrue(form_yes.is_valid())


class TestBaseReviewMixinRoles(TestCase):
    """
    Test to ensure the mixin correctly returns the correct roles.
    """

    def test_allowed_and_read_only_roles(self):
        """
        Only assessor and cyber advisor roles should be able to edit the review.
        :return:
        """
        view = DummyView()
        self.assertEqual(
            view.get_allowed_roles(),
            ["cyber_advisor", "organisation_lead", "reviewer", "assessor"],
        )
        self.assertEqual(view.get_read_only_roles(), ["organisation_lead"])


class TestBaseReviewMixinFormValid(BaseViewTest):
    """
    Comprehensive tests for BaseReviewMixin.form_valid() method.

    Tests all ValidationError scenarios that can be raised by Review.save():
    1. Completed review modification
    2. Permission denied (can_edit=False)
    3. Optimistic locking failure (stale data)
    4. Successful save (no ValidationError)
    """

    @classmethod
    def setUpTestData(cls):
        BaseViewTest.setUpTestData()

        cls.assessment = Assessment.objects.create(
            system=cls.test_system,
            assessment_period="2024/25",
            framework="caf32",
            caf_profile="baseline",
            review_type="independent",
        )

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.view = DummyView()
        self.view.request = self.factory.get("/")

    def _patch_super_form_valid(self, return_value=None, side_effect=None):
        """Helper to patch super().form_valid() in the BaseReviewMixin."""
        if side_effect:
            return patch("django.views.generic.edit.UpdateView.form_valid", side_effect=side_effect)
        return patch(
            "django.views.generic.edit.UpdateView.form_valid", return_value=return_value or HttpResponse("Success")
        )

    def test_form_valid_successful_save(self):
        """Test that form_valid works normally when no ValidationError is raised."""
        mock_form = Mock()

        with self._patch_super_form_valid(HttpResponse("Success")):
            response = self.view.form_valid(mock_form)

        self.assertEqual(response.content, b"Success")
        mock_form.add_error.assert_not_called()

    def test_form_valid_catches_completed_review_error(self):
        """Test that form_valid catches ValidationError for completed review modification."""
        mock_form = Mock()
        error_message = "Review data cannot be changed after it has been marked as completed."
        validation_error = ValidationError(error_message)

        self.view.form_invalid = Mock(return_value=HttpResponse("Invalid"))

        with self._patch_super_form_valid(side_effect=validation_error):
            response = self.view.form_valid(mock_form)

        mock_form.add_error.assert_called_once_with(None, error_message)
        self.view.form_invalid.assert_called_once_with(mock_form)
        self.assertEqual(response.content, b"Invalid")

    def test_form_valid_catches_permission_denied_error(self):
        """Test that form_valid catches ValidationError for can_edit=False."""
        mock_form = Mock()
        error_message = "You do not have permission to edit this report."
        validation_error = ValidationError(error_message)

        self.view.form_invalid = Mock(return_value=HttpResponse("Invalid"))

        with self._patch_super_form_valid(side_effect=validation_error):
            response = self.view.form_valid(mock_form)

        mock_form.add_error.assert_called_once_with(None, error_message)
        self.view.form_invalid.assert_called_once_with(mock_form)
        self.assertEqual(response.content, b"Invalid")

    def test_form_valid_catches_optimistic_locking_error(self):
        """Test that form_valid catches ValidationError for stale data."""
        mock_form = Mock()
        error_message = "Your copy of data has been updated since you last saved it."
        validation_error = ValidationError(error_message)

        self.view.form_invalid = Mock(return_value=HttpResponse("Invalid"))

        with self._patch_super_form_valid(side_effect=validation_error):
            response = self.view.form_valid(mock_form)

        mock_form.add_error.assert_called_once_with(None, error_message)
        self.view.form_invalid.assert_called_once_with(mock_form)
        self.assertEqual(response.content, b"Invalid")

    def test_form_valid_preserves_other_exceptions(self):
        """Test that form_valid doesn't catch non-ValidationError exceptions."""
        mock_form = Mock()

        with self._patch_super_form_valid(side_effect=ValueError("Some other error")):
            with self.assertRaises(ValueError) as context:
                self.view.form_valid(mock_form)

        mock_form.add_error.assert_not_called()
        self.assertEqual(str(context.exception), "Some other error")

    def test_form_valid_multiple_error_messages(self):
        """Test that form_valid handles ValidationError with multiple messages."""
        mock_form = Mock()
        validation_error = ValidationError(["Error 1", "Error 2"])

        self.view.form_invalid = Mock(return_value=HttpResponse("Invalid"))

        with self._patch_super_form_valid(side_effect=validation_error):
            self.view.form_valid(mock_form)

        # Should call add_error twice - once for each error message
        self.assertEqual(mock_form.add_error.call_count, 2)
        # Check that both messages were added
        calls = mock_form.add_error.call_args_list
        self.assertEqual(calls[0][0], (None, "Error 1"))
        self.assertEqual(calls[1][0], (None, "Error 2"))
        self.view.form_invalid.assert_called_once_with(mock_form)
