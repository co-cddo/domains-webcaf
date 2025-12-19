from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse
from freezegun import freeze_time

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import (
    Assessment,
    Configuration,
    Organisation,
    Review,
    System,
    UserProfile,
)


@freeze_time("2050-01-15 10:00:00")
@pytest.mark.django_db
class TestCreateReportView(BaseViewTest):
    """
    Hardcoding the date to make sure the config does not conflict with any existing data in the database.
    """

    def setUp(self):
        # Ensure we have a current assessment period far in the future
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

        # Use base fixtures for org/system
        self.org: Organisation = Organisation.objects.get(name=self.organisation_name)
        self.system: System = System.objects.get(name=self.system_name, organisation=self.org)

        # Submitted assessment within current period (required by BaseReviewMixin queryset)
        self.assessment = Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period=self.period,
        )
        self.review = Review.objects.create(assessment=self.assessment)

        # Login as cyber_advisor (has access to all org reviews)
        self.client = Client()
        self.user = self.org_map[self.organisation_name]["users"]["cyber_advisor"]
        self.assessor = self.org_map[self.organisation_name]["users"]["assessor"]
        self.client.force_login(self.user)
        profile = UserProfile.objects.get(user=self.user, organisation=self.org, role="cyber_advisor")
        session = self.client.session
        session["current_profile_id"] = profile.id
        session.save()

    def test_create_report_success_redirects_to_confirmation(self):
        url = reverse("create-report", kwargs={"pk": self.review.id})
        # Stub mark_review_complete to succeed
        with patch.object(Review, "mark_review_complete", return_value=None) as mocked:
            resp = self.client.post(url, data={"action": "create_report"}, follow=False)

        # Method was called with SessionUtil-provided profile (not asserted here)
        self.assertTrue(mocked.called)
        # Redirect to confirmation
        self.assertIn(resp.status_code, (302, 303))
        self.assertEqual(resp.url, reverse("show-report-confirmation", kwargs={"pk": self.review.id}))

    def test_create_report_validation_error_stays_on_page(self):
        url = reverse("create-report", kwargs={"pk": self.review.id})
        with patch.object(Review, "mark_review_complete", side_effect=ValidationError("Boom")):
            resp = self.client.post(url, data={"action": "create_report"}, follow=False)

        # Should render the same page with an error (no redirect)
        self.assertEqual(resp.status_code, 200)
        # The view prefixes the error with this message
        self.assertIn(b"Could not generate the report", resp.content)

    def test_show_report_confirmation_renders(self):
        # Smoke test the confirmation page renders

        # Make the review complete - this enables the versioning
        self.review.status = "completed"
        self.review.last_updated_by = self.assessor
        self.review.save()

        url = reverse("show-report-confirmation", kwargs={"pk": self.review.id})
        self.client.force_login(self.user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Reviewer name", resp.content)
        self.assertIn(b"(Independent assurance reviewer)", resp.content)
