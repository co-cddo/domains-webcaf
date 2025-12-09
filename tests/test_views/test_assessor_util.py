from django.test import TestCase

from webcaf.webcaf.views.assessor.util import BaseReviewMixin, YesNoForm


class DummyView(BaseReviewMixin):
    """Minimal concrete to exercise mixin methods that don't hit the DB."""

    def __init__(self):
        # simulate attributes the mixin might rely on
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
