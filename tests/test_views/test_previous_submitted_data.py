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
    Tip,
    TipStatus,
)


@freeze_time("2026-10-16 12:00:00")
class TestHistoricalAssessmentView(BaseViewTest):
    """
    Unit and integration tests for HistoricalAssessmentView.
    """

    def setUp(self):
        self.url = reverse("historical-assessments")
        self.org = Organisation.objects.get(name=self.organisation_name)
        self.system = System.objects.get(name=self.system_name, organisation=self.org)
        self.system2 = System.objects.get(
            name=self.org_map[self.organisation_name]["systems"]["Large system"], organisation=self.org
        )

        # Other organisation
        self.other_org, _ = Organisation.objects.get_or_create(name="Other Organisation")
        self.other_system, _ = System.objects.get_or_create(name="Other System", organisation=self.other_org)

        # Set up default configuration with current assessment period "26/27"
        Configuration.objects.all().delete()
        self.config = Configuration.objects.create(
            name="2026 Assessment Period",
            config_data={
                "current_assessment_period": "26/27",
                "assessment_period_end": "31 March 2027 11:59pm",
                "default_framework": "caf32",
            },
        )
        self.current_period = self.config.get_current_assessment_period()

    def test_unauthenticated_user_redirected_to_login(self):
        client = Client()
        response = client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/oidc/authenticate/", response.url)

    def test_allowed_roles_can_access_view(self):
        for role in ["organisation_lead", "organisation_user", "cyber_advisor"]:
            client, profile = self._login_with_role(role, self.org)
            response = client.get(self.url)
            self.assertEqual(response.status_code, 200, f"Role {role} should have access to historical assessments")
            self.assertTemplateUsed(response, "assessment/historical-assessments.html")

    def test_unauthorized_roles_receive_403(self):
        unauthorized_roles = ["assessor"]
        for role in unauthorized_roles:
            client, profile = self._login_with_role(role, self.org)
            response = client.get(self.url)
            self.assertEqual(response.status_code, 403, f"Role {role} should be forbidden from accessing the view")

    def test_breadcrumbs_in_context(self):
        client, profile = self._login_with_role("organisation_lead", self.org)
        response = client.get(self.url)
        self.assertEqual(response.status_code, 200)

        breadcrumbs = response.context["breadcrumbs"]
        expected_breadcrumbs = [
            {"url": reverse("my-account"), "text": "My account"},
            {"url": "#", "text": "Previous GovAssure submissions"},
        ]
        self.assertEqual(breadcrumbs, expected_breadcrumbs)

    def test_current_period_assessments_excluded(self):
        # Assessment in current period (26/27) should be excluded
        Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period=self.current_period,
            review_type="independent",
        )
        # Assessment in historical period (25/26) should be included
        historical_assessment = Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period="25/26",
            review_type="independent",
        )

        client, profile = self._login_with_role("organisation_lead", self.org)
        response = client.get(self.url)
        self.assertEqual(response.status_code, 200)

        systems_data = response.context["systems"]
        self.assertIn("2025 to 2026", systems_data)
        self.assertNotIn("2026 to 2027", systems_data)

        history_items = systems_data["2025 to 2026"]
        self.assertEqual(len(history_items), 1)
        self.assertEqual(history_items[0].assessment, historical_assessment)

    def test_non_submitted_assessments_excluded(self):
        # Draft assessment in historical period
        Assessment.objects.create(
            system=self.system,
            status="draft",
            assessment_period="25/26",
            review_type="independent",
        )
        # Submitted assessment in historical period
        submitted_assessment = Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period="25/26",
            review_type="independent",
        )

        client, profile = self._login_with_role("organisation_lead", self.org)
        response = client.get(self.url)
        self.assertEqual(response.status_code, 200)

        systems_data = response.context["systems"]
        self.assertIn("2025 to 2026", systems_data)
        history_items = systems_data["2025 to 2026"]
        self.assertEqual(len(history_items), 1)
        self.assertEqual(history_items[0].assessment, submitted_assessment)

    def test_other_organisation_assessments_excluded(self):
        # Historical submitted assessment for other org
        Assessment.objects.create(
            system=self.other_system,
            status="submitted",
            assessment_period="25/26",
            review_type="independent",
        )
        # Historical submitted assessment for current org
        own_assessment = Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period="25/26",
            review_type="independent",
        )

        client, profile = self._login_with_role("organisation_lead", self.org)
        response = client.get(self.url)
        self.assertEqual(response.status_code, 200)

        systems_data = response.context["systems"]
        self.assertIn("2025 to 2026", systems_data)
        history_items = systems_data["2025 to 2026"]
        self.assertEqual(len(history_items), 1)
        self.assertEqual(history_items[0].assessment, own_assessment)

    def test_multiple_years_grouping_and_ordering(self):
        assessment_23_24 = Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period="23/24",
            review_type="independent",
        )
        assessment_24_25 = Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period="24/25",
            review_type="independent",
        )
        assessment_25_26 = Assessment.objects.create(
            system=self.system2,
            status="submitted",
            assessment_period="25/26",
            review_type="peer_review",
        )

        client, profile = self._login_with_role("organisation_lead", self.org)
        response = client.get(self.url)
        self.assertEqual(response.status_code, 200)

        systems_data = response.context["systems"]
        self.assertIn("2023 to 2024", systems_data)
        self.assertIn("2024 to 2025", systems_data)
        self.assertIn("2025 to 2026", systems_data)

        self.assertEqual(systems_data["2023 to 2024"][0].assessment, assessment_23_24)
        self.assertEqual(systems_data["2024 to 2025"][0].assessment, assessment_24_25)
        self.assertEqual(systems_data["2025 to 2026"][0].assessment, assessment_25_26)

    def test_reviews_associated_only_when_completed(self):
        # Assessment with completed review
        assessment_completed = Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period="24/25",
            review_type="independent",
        )
        review_completed = Review.objects.create(
            assessment=assessment_completed,
            status="completed",
        )

        # Assessment with draft/in-progress review
        assessment_in_progress = Assessment.objects.create(
            system=self.system2,
            status="submitted",
            assessment_period="24/25",
            review_type="independent",
        )
        Review.objects.create(
            assessment=assessment_in_progress,
            status="draft",
        )

        client, profile = self._login_with_role("organisation_lead", self.org)
        response = client.get(self.url)
        self.assertEqual(response.status_code, 200)

        systems_data = response.context["systems"]
        history_items = systems_data["2024 to 2025"]

        history_map = {item.assessment.id: item for item in history_items}

        # Completed review should be present
        self.assertEqual(history_map[assessment_completed.id].review, review_completed)
        # Non-completed review should be None
        self.assertIsNone(history_map[assessment_in_progress.id].review)

    def test_tips_associated_only_when_review_finalised(self):
        # Assessment with finalised review and tip
        assessment_finalised = Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period="24/25",
            review_type="independent",
        )
        review_finalised = Review.objects.create(
            assessment=assessment_finalised,
            status="completed",
            review_data={"review_finalised": {"review_finalised_at": "2025-05-14T11:15:00"}},
        )
        tip_finalised = Tip.objects.create(review=review_finalised, reference="TIP-001")

        # Assessment with unfinalised review and tip
        assessment_unfinalised = Assessment.objects.create(
            system=self.system2,
            status="submitted",
            assessment_period="24/25",
            review_type="independent",
        )
        review_unfinalised = Review.objects.create(
            assessment=assessment_unfinalised,
            status="completed",
            review_data={},
        )
        Tip.objects.create(review=review_unfinalised, reference="TIP-002")

        client, profile = self._login_with_role("organisation_lead", self.org)
        response = client.get(self.url)
        self.assertEqual(response.status_code, 200)

        systems_data = response.context["systems"]
        history_items = systems_data["2024 to 2025"]
        history_map = {item.assessment.id: item for item in history_items}

        # Finalised tip should be attached
        self.assertEqual(history_map[assessment_finalised.id].tip, tip_finalised)
        # Unfinalised tip should be None
        self.assertIsNone(history_map[assessment_unfinalised.id].tip)

    def test_template_rendering_content_with_submitted_tip_and_iarr(self):
        assessment = Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period="24/25",
            review_type="independent",
        )
        review = Review.objects.create(
            assessment=assessment,
            status="completed",
            review_data={"review_finalised": {"review_finalised_at": "2025-05-14T11:15:00"}},
        )
        tip = Tip.objects.create(
            review=review,
            reference="TIP-001",
            status=TipStatus.REVIEW,
        )

        client, profile = self._login_with_role("organisation_lead", self.org)
        response = client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GovAssure 2024 to 2025")
        self.assertContains(response, self.system.name)
        self.assertContains(response, reverse("view-submitted-assessment", args=[assessment.id]))
        self.assertContains(response, reverse("show-report", args=[review.id, review.current_version_number]))
        self.assertContains(response, "IARR")
        self.assertContains(response, reverse("tip:view-report", args=[tip.id]))
        self.assertContains(response, ">TIP<")

    def test_template_rendering_content_with_unsubmitted_tip_and_peer_review(self):
        assessment = Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period="24/25",
            review_type="peer_review",
        )
        review = Review.objects.create(
            assessment=assessment,
            status="completed",
            review_data={"review_finalised": {"review_finalised_at": "2025-05-14T11:15:00"}},
        )
        tip = Tip.objects.create(
            review=review,
            reference="TIP-002",
            status=TipStatus.IN_PROGRESS,
        )

        client, profile = self._login_with_role("organisation_lead", self.org)
        response = client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GovAssure 2024 to 2025")
        self.assertContains(response, "Peer Review Report")
        self.assertContains(response, reverse("tip:edit", args=[tip.id]))
        self.assertContains(response, "Continue TIP")
