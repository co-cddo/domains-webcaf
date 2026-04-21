from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.urls import reverse

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import Assessment, UserProfile


@override_settings(
    NOTIFY_CONFIRMATION_TEMPLATE_ID="test-confirm-template",
    NOTIFY_ASSESSMENT_READY_TEMPLATE_ID="test-ready-template",
)
class TestSubmissionEmails(BaseViewTest):
    """
    Integration tests for email dispatch when an assessment is submitted via
    SectionConfirmationView (POST to 'objective-confirmation').

    Setup:
      - 1 submitter with organisation_lead role
      - 2 assessors with assessor role
      - 2 reviewers with reviewer role
      - A draft assessment with review_type="independent"

    Note: send_notify_email is patched to avoid real GOV.UK Notify API calls.
    Assessment.is_complete is patched so tests are not coupled to framework data.
    """

    @classmethod
    def setUpTestData(cls):
        BaseViewTest.setUpTestData()

        org = cls.org_map[cls.organisation_name]["organisation"]

        # Submitter: reuse the existing organisation_lead, but ensure email is set
        cls.submitter = cls.org_map[cls.organisation_name]["users"]["organisation_lead"]
        cls.submitter.email = "submitter@bigorganisation.gov.uk"
        cls.submitter.first_name = "Alex"
        cls.submitter.last_name = "Smith"
        cls.submitter.save()
        cls.submitter_profile = UserProfile.objects.get(
            user=cls.submitter,
            role="organisation_lead",
            organisation=org,
        )

        # Create assessors and reviewers
        for user_type in ["assessor", "reviewer"]:
            for i in range(1, 3):
                email = f"{user_type}{i}@bigorganisation.gov.uk"
                user, created = User.objects.get_or_create(
                    username=email,
                    defaults={"email": email, "first_name": f"{user_type.capitalize()}{i}", "last_name": "User"},
                )
                # Make sure we set an email
                if not created:
                    user.email = email
                    user.save()

    def setUp(self):
        self.assessment = Assessment.objects.create(
            system=self.test_system,
            status="draft",
            assessment_period="25/26",
            review_type="independent",
            framework="caf32",
            caf_profile="baseline",
            created_by=self.submitter,
        )

        self.client = Client()
        self.client.force_login(self.submitter)
        session = self.client.session
        session["current_profile_id"] = self.submitter_profile.id
        session["draft_assessment"] = {"assessment_id": self.assessment.id}
        session.save()

    def _submit(self):
        return self.client.post(reverse("objective-confirmation"), data={}, follow=False)

    # ---------------------------------------------------------------------------
    # Confirmation email
    # ---------------------------------------------------------------------------

    @patch("webcaf.webcaf.views.sections.send_notify_email")
    def test_confirmation_email_sent_to_submitter(self, mock_send):
        """Confirmation email is sent exactly once, addressed to the submitting user."""
        with patch.object(Assessment, "is_complete", return_value=True):
            response = self._submit()

        self.assertRedirects(
            response,
            reverse("show-submission-confirmation"),
            fetch_redirect_response=False,
        )

        confirm_calls = [c for c in mock_send.call_args_list if c.args[2] == "test-confirm-template"]
        self.assertEqual(len(confirm_calls), 1, "Expected exactly one confirmation email")
        self.assertEqual(
            confirm_calls[0].args[0],
            [self.submitter.email],
            "Confirmation email must be addressed to the submitter",
        )

    @patch("webcaf.webcaf.views.sections.send_notify_email")
    def test_confirmation_email_personalisation(self, mock_send):
        """Confirmation email carries the expected personalisation fields."""
        with patch.object(Assessment, "is_complete", return_value=True):
            self._submit()

        confirm_calls = [c for c in mock_send.call_args_list if c.args[2] == "test-confirm-template"]
        self.assertEqual(len(confirm_calls), 1)

        personalisation = confirm_calls[0].args[1]
        self.assertEqual(personalisation["first_name"], self.submitter.first_name)
        self.assertEqual(personalisation["last_name"], self.submitter.last_name)
        self.assertEqual(personalisation["submitted_by"], self.submitter.email)
        self.assertEqual(personalisation["system_name"], self.test_system.name)
        self.assertEqual(personalisation["organisation_name"], self.test_system.organisation.name)
        self.assertEqual(personalisation["caf_version"], "caf32")

    @patch("webcaf.webcaf.views.sections.send_notify_email")
    def test_ready_email_personalisation(self, mock_send):
        """Confirmation email carries the expected personalisation fields."""
        with patch.object(Assessment, "is_complete", return_value=True):
            self._submit()

        ready_calls = [c for c in mock_send.call_args_list if c.args[2] == "test-ready-template"]
        self.assertEqual(len(ready_calls), 1)

        personalisation = ready_calls[0].args[1]
        self.assertEqual(
            list(personalisation.keys()),
            ["submitted_by", "submitted_on", "reference", "system_name", "organisation_name", "caf_version"],
        )
        self.assertEqual(personalisation["submitted_by"], self.submitter.email)
        self.assertEqual(personalisation["system_name"], self.test_system.name)
        self.assertEqual(personalisation["organisation_name"], self.test_system.organisation.name)
        self.assertEqual(personalisation["caf_version"], "caf32")

    # ---------------------------------------------------------------------------
    # Assessment-ready emails
    # ---------------------------------------------------------------------------

    @patch("webcaf.webcaf.views.sections.send_notify_email")
    def test_assessment_ready_email_sent_to_all_assessors(self, mock_send):
        """
        For independent review_type, assessment-ready emails are sent to every
        assessor in the organisation — one email per assessor.
        """
        org = self.org_map[self.organisation_name]["organisation"]
        assessor_emails = set(
            UserProfile.objects.filter(role="assessor", organisation=org)
            .distinct()
            .values_list("user__email", flat=True)
        )

        with patch.object(Assessment, "is_complete", return_value=True):
            self._submit()

        ready_calls = [c for c in mock_send.call_args_list if c.args[2] == "test-ready-template"]
        sent_to = {email for c in ready_calls for email in c.args[0]}

        self.assertEqual(
            sent_to,
            assessor_emails,
            "Assessment-ready emails must be sent to exactly the assessors in the organisation",
        )

    @patch("webcaf.webcaf.views.sections.send_notify_email")
    def test_assessment_ready_email_not_sent_to_reviewers_for_independent(self, mock_send):
        """Reviewer-role users must NOT receive the assessment-ready email for independent reviews."""
        reviewer_emails = {
            user.email
            for user in User.objects.filter(
                username__startswith="reviewer",
                username__endswith="bigorganisation.gov.uk",
            )
        }

        with patch.object(Assessment, "is_complete", return_value=True):
            self._submit()

        ready_calls = [c for c in mock_send.call_args_list if c.args[2] == "test-ready-template"]
        sent_to = {email for c in ready_calls for email in c.args[0]}

        for reviewer_email in reviewer_emails:
            self.assertNotIn(reviewer_email, sent_to)

    # ---------------------------------------------------------------------------
    # No-email paths
    # ---------------------------------------------------------------------------

    @patch("webcaf.webcaf.views.sections.send_notify_email")
    def test_no_emails_sent_when_assessment_is_incomplete(self, mock_send):
        """Submitting an incomplete assessment redirects to account page; no emails are sent."""
        with patch.object(Assessment, "is_complete", return_value=False):
            response = self._submit()

        mock_send.assert_not_called()
        self.assertRedirects(response, reverse("my-account"), fetch_redirect_response=False)

    @patch("webcaf.webcaf.views.sections.send_notify_email")
    def test_no_duplicate_emails_on_already_submitted_assessment(self, mock_send):
        """Re-submitting an already-submitted assessment must not trigger a second round of emails."""
        self.assessment.status = "submitted"
        self.assessment.save()

        with patch.object(Assessment, "is_complete", return_value=True):
            self._submit()

        mock_send.assert_not_called()
