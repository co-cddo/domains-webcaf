from unittest.mock import patch

from django.test import Client
from django.urls import reverse
from freezegun import freeze_time

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import Assessment, Configuration


@freeze_time("2050-01-15 10:00:00")
class ConfirmationStatusRenderingTests(BaseViewTest):
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

        # Create a draft assessment for an organisation user to access the confirmation view
        cls.assessment = Assessment.objects.create(
            system=cls.test_system,
            status="draft",
            assessment_period="49/50",
            framework="caf32",
            caf_profile="baseline",
            created_by=cls.test_user,
        )

        cls.assessment.assessments_data = {
            "A1.a": {
                "confirmation": {"outcome_status": "Achieved", "confirm_outcome_confirm_comment": "Summary comment"},
                "indicators": {},
            }
        }
        cls.assessment.save()

        # The URL name for OutcomeConfirmationView for framework caf32, outcome A1.a
        cls.url = reverse("caf32_confirmation_A1.a")

    def setUp(self):
        self.client = Client()
        # Use an organisation user for the self-assessment confirmation view
        self.org_user = self.org_map[self.organisation_name]["users"]["organisation_user"]
        self.org_user_profile = self.org_user.profiles.filter(role="organisation_user").first()
        self.client.force_login(self.org_user)
        session = self.client.session
        session["current_profile_id"] = self.org_user_profile.id
        session["draft_assessment"] = {"assessment_id": self.assessment.id}
        session.save()

    @patch("webcaf.webcaf.caf.util.IndicatorStatusChecker.indicator_min_profile_requirement_met")
    def test_confirmation_met_status(self, mock_met):
        # Setup mock to return ("Yes", "Achieved") for profile_met
        # If profile_met.0 != "Not met", it renders "Met"
        mock_met.return_value = ("Yes", "Achieved")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        # Check for line 40: <strong class="govuk-tag govuk-tag--green">Met</strong>
        self.assertContains(response, '<strong class="govuk-tag govuk-tag--green">Met</strong>', html=True)

    @patch("webcaf.webcaf.caf.util.IndicatorStatusChecker.indicator_min_profile_requirement_met")
    def test_confirmation_not_met_status(self, mock_met):
        # Setup mock to return ("Not met", "Achieved") for profile_met
        mock_met.return_value = ("Not met", "Achieved")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        # Check for line 38: <strong class="outcome_profile_status govuk-tag govuk-tag--red">{{ profile_met.0 }}</strong>
        self.assertContains(
            response, '<strong class="outcome_profile_status govuk-tag govuk-tag--red">Not met</strong>', html=True
        )
