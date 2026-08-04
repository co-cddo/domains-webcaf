# tests/test_review_finalise.py
import logging
from unittest.mock import patch

from django.urls import reverse
from freezegun import freeze_time

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import Assessment, Configuration, Organisation, Review, System
from webcaf.webcaf.views.assessor.review import FinaliseReview


@freeze_time("2050-01-15 10:00:00")
class FinaliseReviewTests(BaseViewTest):
    def setUp(self):
        Configuration.objects.create(
            name="2050 Assessment Period",
            config_data={
                "current_assessment_period": "49/50",
                "assessment_period_end": "31 March 2050 11:59pm",
                "default_framework": "caf32",
            },
        )
        self.config = Configuration.objects.get_default_config()
        self.period = self.config.get_current_assessment_period()
        self.org = Organisation.objects.get(name=self.organisation_name)
        self.system = System.objects.get(name=self.system_name, organisation=self.org)
        # Reviews in current org and current period
        self.assessment_ok = Assessment.objects.create(
            system=self.system, status="submitted", assessment_period=self.period, review_type="independent"
        )

    def test_form_valid_finalises_completed_review(self):
        """Test that a completed review is finalised successfully."""
        with patch.object(FinaliseReview, "send_emails") as mock_send_emails:
            review = Review.objects.create(
                assessment=self.assessment_ok,
                status="completed",
                review_data={"review_completion": {"review_completed": "yes"}},
            )
            finalise_review_url = reverse("finalise-review", kwargs={"pk": review.id})
            client, _ = self._login_with_role("assessor", self.org)
            response = client.post(finalise_review_url, follow=True)

            # Check that finalisation succeeded
            review.refresh_from_db()
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Version 1 is now the final report.", response.content)
            self.assertTrue(review.is_review_finalised())

            # Ensure send_emails is called with the finalised review
            mock_send_emails.assert_called_once_with(review)

    def test_form_invalid_with_incomplete_review(self):
        """Test that an incomplete review cannot be finalised."""
        incomplete_review = Review.objects.create(assessment=self.assessment_ok, status="in_progress")
        url = reverse("finalise-review", kwargs={"pk": incomplete_review.id})
        client, _ = self._login_with_role("assessor", self.org)
        response = client.post(url, follow=True)

        # Validate response and error message
        self.assertEqual(response.status_code, 200)
        self.assertIn("You cannot finalise a review that has not been completed.", str(response.content))

        # Ensure the review status has not changed
        incomplete_review.refresh_from_db()
        self.assertFalse(incomplete_review.is_review_finalised())

    def test_no_email_sent_when_template_id_empty(self):
        """Test that no email is sent when NOTIFY_REVIEW_FINALISED_TEMPLATE_ID is empty."""
        with (
            patch("webcaf.settings.NOTIFY_REVIEW_FINALISED_TEMPLATE_ID", ""),
            patch("webcaf.webcaf.views.assessor.review.send_notify_email") as mock_send_email,
        ):
            review = Review.objects.create(
                assessment=self.assessment_ok,
                status="completed",
                review_data={"review_completion": {"review_completed": "yes"}},
            )
            finalise_review_url = reverse("finalise-review", kwargs={"pk": review.id})
            client, _ = self._login_with_role("assessor", self.org)
            client.post(finalise_review_url, follow=True)

            # Ensure send_notify_email was not called
            mock_send_email.assert_not_called()

    def test_email_only_sent_to_organisation_leads(self):
        """Test that emails are only sent to users with organisation_lead role in current organisation."""
        with (
            patch("webcaf.settings.NOTIFY_REVIEW_FINALISED_TEMPLATE_ID", "test-template-id"),
            patch("webcaf.webcaf.views.assessor.review.send_notify_email") as mock_send_email,
        ):
            # Create organisation leads in current org
            self._create_user_with_role(
                "organisation_lead",
                self.org,
                username="lead1",
            )
            self._create_user_with_role(
                "organisation_lead",
                self.org,
                username="lead2",
            )
            # Create organisation lead in different org (should not receive email)
            other_org = Organisation.objects.create(name="Other Org")
            self._create_user_with_role(
                "organisation_lead",
                other_org,
                username="other_lead",
            )

            # Create user with different role in current org (should not receive email)
            self._create_user_with_role(
                "assessor",
                self.org,
                username="assessor1",
            )
            review = Review.objects.create(
                assessment=self.assessment_ok,
                status="completed",
                review_data={"review_completion": {"review_completed": "yes"}},
            )
            finalise_review_url = reverse("finalise-review", kwargs={"pk": review.id})
            client, _ = self._login_with_role("assessor", self.org)
            client.post(finalise_review_url, follow=True)

            # Verify send_notify_email was called once
            mock_send_email.assert_called_once()

            # Verify it was called with only organisation_lead emails from current org
            call_args = mock_send_email.call_args[1]
            email_addresses = call_args["email_addresses"]
            self.assertEqual(
                set(email_addresses),
                {
                    "organisation_lead@bigorganisation.gov.uk",
                    "lead1@bigorganisation.gov.uk",
                    "lead2@bigorganisation.gov.uk",
                },
            )

    def test_email_sending_failure_does_not_raise_error(self):
        """Test that email sending failures do not raise errors."""
        with (
            patch("webcaf.settings.NOTIFY_REVIEW_FINALISED_TEMPLATE_ID", "test-template-id"),
            patch("webcaf.webcaf.views.assessor.review.send_notify_email") as mock_send_email,
        ):
            mock_send_email.side_effect = Exception("Email service unavailable")
            self._create_user_with_role("organisation_lead", self.org, username="lead1")
            review = Review.objects.create(
                assessment=self.assessment_ok,
                status="completed",
                review_data={"review_completion": {"review_completed": "yes"}},
            )
            finalise_review_url = reverse("finalise-review", kwargs={"pk": review.id})
            client, _ = self._login_with_role("assessor", self.org)

            # Should not raise an exception
            response = client.post(finalise_review_url, follow=True)

            # Verify the review is still finalised despite email failure
            review.refresh_from_db()
            self.assertEqual(response.status_code, 200)
            self.assertTrue(review.is_review_finalised())

    def test_form_valid_logger_message(self):
        """Test that the logger outputs the correct message during finalisation."""
        logger_name = "FinaliseReview"
        review = Review.objects.create(
            assessment=self.assessment_ok,
            status="completed",
            review_data={"review_completion": {"review_completed": "yes"}},
        )
        finalise_review_url = reverse("finalise-review", kwargs={"pk": review.id})
        with patch.object(logging.getLogger(logger_name), "info") as mock_logger:
            client, _ = self._login_with_role("assessor", self.org)
            client.post(finalise_review_url, follow=True)

            # Assert that the logger contains the finalisation message
            mock_logger.assert_any_call(f"Finalising report for {review.reference}")
