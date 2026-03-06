from unittest.mock import patch

from django.test import Client
from django.urls import reverse
from freezegun import freeze_time

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import Assessment, Configuration, Review


@freeze_time("2050-01-15 10:00:00")
class OutcomeStatusRenderingTests(BaseViewTest):
    @classmethod
    def setUpTestData(cls):
        BaseViewTest.setUpTestData()

        # Ensure a default configuration exists
        Configuration.objects.create(
            name="2050 Assessment Period",
            config_data={
                "current_assessment_period": "49/50",
                "assessment_period_end": "31 March 2050 11:59pm",
                "default_framework": "caf32",
            },
        )

        # Create an assessment with status "submitted" so it's picked up by BaseReviewMixin
        cls.assessment = Assessment.objects.create(
            system=cls.test_system,
            status="submitted",
            assessment_period="49/50",
            review_type="independent_review",
            framework="caf32",
            caf_profile="baseline",
        )

        cls.assessment.assessments_data = {
            "A1.a": {
                "confirmation": {"outcome_status": "Achieved", "confirm_outcome_confirm_comment": "Summary comment"},
                "indicators": {},
            }
        }
        cls.assessment.save()

        # Create a review for this assessment
        cls.review = Review.objects.create(
            assessment=cls.assessment,
            last_updated_by=cls.test_user,
        )

        cls.url = reverse("review-outcome", kwargs={"pk": cls.review.pk, "objective_code": "A", "outcome_code": "A1.a"})

    def setUp(self):
        self.client = Client()
        # Use the cyber_advisor user from BaseViewTest's org_map
        self.assessor = self.org_map[self.organisation_name]["users"]["cyber_advisor"]
        self.assessor_profile = self.assessor.profiles.filter(role="cyber_advisor").first()
        self.client.force_login(self.assessor)
        session = self.client.session
        session["current_profile_id"] = self.assessor_profile.id
        session.save()

    @patch("webcaf.webcaf.caf.util.IndicatorStatusChecker.indicator_min_profile_requirement_met")
    def test_rendering_met_status(self, mock_met):
        # Setup mock to return ("Yes", "Achieved") for profile_met
        # Note: In the template, profile_met.0 is checked for "Not met"
        # If profile_met.0 != "Not met", it renders "Met"
        mock_met.return_value = ("Yes", "Achieved")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        # Check for line 78: <strong class="govuk-tag govuk-tag--green">Met</strong>
        self.assertContains(response, '<strong class="govuk-tag govuk-tag--green">Met</strong>', html=True)

    @patch("webcaf.webcaf.caf.util.IndicatorStatusChecker.indicator_min_profile_requirement_met")
    def test_rendering_not_met_status(self, mock_met):
        # Setup mock to return ("Not met", "Achieved") for profile_met
        mock_met.return_value = ("Not met", "Achieved")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        # Check for line 76: <strong class="govuk-tag govuk-tag--red">{{ profile_met.0 }}</strong>
        self.assertContains(response, '<strong class="govuk-tag govuk-tag--red">Not met</strong>', html=True)
