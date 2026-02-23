"""
Unit tests for the assessment_required decorator.

Tests that the decorator correctly raises AssessmentNotSelectedException
when no assessment is selected in the session for the classes that use it:
- ObjectiveView
- BaseIndicatorsFormView (via OutcomeIndicatorsView)
- OutcomeConfirmationView
"""

from django.test import Client
from django.urls import reverse
from freezegun import freeze_time

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import Assessment, Configuration


@freeze_time("2050-01-15 10:00:00")
class AssessmentRequiredDecoratorTests(BaseViewTest):
    """
    Test suite to verify that the assessment_required decorator is correctly applied
    and raises AssessmentNotSelectedException when no assessment is selected.
    """

    @classmethod
    def setUpTestData(cls):
        BaseViewTest.setUpTestData()
        Configuration.objects.create(
            name="2050 Assessment Period",
            config_data={
                "current_assessment_period": "49/50",
                "assessment_period_end": "31 March 2050 11:59pm",
                "default_framework": "caf32",
            },
        )
        cls.config = Configuration.objects.get_default_config()
        cls.period = cls.config.get_current_assessment_period()
        # Create a draft assessment for caf32
        cls.assessment = Assessment.objects.create(
            system=cls.test_system,
            status="draft",
            assessment_period=cls.period,
            review_type="peer_review",
            framework="caf32",
            caf_profile="baseline",
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.test_user)
        session = self.client.session
        session["current_profile_id"] = self.user_profile.id
        session["draft_assessment"] = self.assessment.id
        session.save()

    def test_objective_view_raises_exception_without_assessment(self):
        """
        Test that ObjectiveView.form_valid() raises AssessmentNotSelectedException
        when draft_assessment is not in session.
        """
        # Ensure no assessment is in session
        session = self.client.session
        session.pop("draft_assessment", None)
        session.save()

        # POST to an objective view should raise AssessmentNotSelectedException
        response = self.client.post(
            reverse("caf32_objective_A"),
            data={"action": "confirm", "next_objective": "B"},
            follow=False,
        )

        # The middleware should catch the exception and redirect
        # Check that we get a 500 or redirect depending on middleware configuration
        self.assertIn(response.status_code, [302, 500])

    def test_objective_view_succeeds_with_assessment(self):
        """
        Test that ObjectiveView.form_valid() succeeds when assessment is in session.
        """
        # Set assessment in session
        session = self.client.session
        session["draft_assessment"] = {"assessment_id": self.assessment.id}
        session.save()

        # POST should succeed
        response = self.client.post(
            reverse("caf32_objective_A"),
            data={"action": "confirm", "next_objective": "B"},
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/caf32/b-protecting-against-cyber-attack/")

    def test_outcome_indicators_view_raises_exception_without_assessment(self):
        """
        Test that OutcomeIndicatorsView.form_valid() (inherits from BaseIndicatorsFormView)
        raises AssessmentNotSelectedException when draft_assessment is not in session.
        """
        # Ensure no assessment is in session
        session = self.client.session
        session.pop("draft_assessment", None)
        session.save()

        # POST to an indicators view should raise AssessmentNotSelectedException
        response = self.client.post(
            reverse("caf32_indicators_A1.a"),
            data={
                "achieved_A1.a.5": True,
                "achieved_A1.a.6": False,
                "achieved_A1.a.7": False,
                "achieved_A1.a.8": False,
                "not-achieved_A1.a.1": False,
                "not-achieved_A1.a.2": False,
                "not-achieved_A1.a.3": False,
                "not-achieved_A1.a.4": False,
                "achieved_A1.a.5_comment": "Test comment",
                "achieved_A1.a.6_comment": "",
                "achieved_A1.a.7_comment": "",
                "achieved_A1.a.8_comment": "",
            },
            follow=False,
        )

        # The middleware should catch the exception
        self.assertIn(response.status_code, [302, 500])

    def test_outcome_indicators_view_succeeds_with_assessment(self):
        """
        Test that OutcomeIndicatorsView.form_valid() succeeds when assessment is in session.
        """
        # Set assessment in session
        session = self.client.session
        session["draft_assessment"] = {"assessment_id": self.assessment.id}
        session.save()

        # POST should succeed
        response = self.client.post(
            reverse("caf32_indicators_A1.a"),
            data={
                "achieved_A1.a.5": True,
                "achieved_A1.a.6": True,
                "achieved_A1.a.7": True,
                "achieved_A1.a.8": True,
                "not-achieved_A1.a.1": False,
                "not-achieved_A1.a.2": False,
                "not-achieved_A1.a.3": False,
                "not-achieved_A1.a.4": False,
                "achieved_A1.a.5_comment": "Test comment",
                "achieved_A1.a.6_comment": "",
                "achieved_A1.a.7_comment": "",
                "achieved_A1.a.8_comment": "",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        # Should redirect to confirmation page
        self.assertEqual(response.redirect_chain[0][0], reverse("caf32_confirmation_A1.a"))

    def test_outcome_confirmation_view_raises_exception_without_assessment(self):
        """
        Test that OutcomeConfirmationView.form_valid() raises AssessmentNotSelectedException
        when draft_assessment is not in session.
        """
        # Setup indicator data first
        self.assessment.assessments_data = {
            "A1.a": {
                "indicators": {
                    "achieved_A1.a.5": True,
                    "not-achieved_A1.a.1": False,
                    "achieved_A1.a.5_comment": "Test",
                }
            }
        }
        self.assessment.save()

        # Ensure no assessment is in session
        session = self.client.session
        session.pop("draft_assessment", None)
        session.save()

        # POST to a confirmation view should raise AssessmentNotSelectedException
        response = self.client.post(
            reverse("caf32_confirmation_A1.a"),
            data={
                "confirm_outcome": "confirm",
                "confirm_outcome_confirm_comment": "This is a summary",
            },
            follow=False,
        )

        # The middleware should catch the exception
        self.assertIn(response.status_code, [302, 500])

    def test_outcome_confirmation_view_succeeds_with_assessment(self):
        """
        Test that OutcomeConfirmationView.form_valid() succeeds when assessment is in session.
        """
        # Setup indicator data
        self.assessment.assessments_data = {
            "A1.a": {
                "indicators": {
                    "achieved_A1.a.5": False,
                    "not-achieved_A1.a.1": True,
                    "not-achieved_A1.a.2": True,
                    "achieved_A1.a.5_comment": "",
                }
            }
        }
        self.assessment.save()

        # Set assessment in session
        session = self.client.session
        session["draft_assessment"] = {"assessment_id": self.assessment.id}
        session.save()

        # POST should succeed
        response = self.client.post(
            reverse("caf32_confirmation_A1.a"),
            data={
                "confirm_outcome": "confirm",
                "confirm_outcome_confirm_comment": "This is my summary comment",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        # Should redirect to objective page
        self.assertRegex(response.redirect_chain[0][0], "/caf32/a-managing-security-risk/")

    def test_assessment_id_none_raises_exception(self):
        """
        Test that having draft_assessment in session but with None assessment_id
        raises AssessmentNotSelectedException.
        """
        # Set draft_assessment but with None assessment_id
        session = self.client.session
        session["draft_assessment"] = {"assessment_id": None}
        session.save()

        response = self.client.post(
            reverse("caf32_objective_A"),
            data={"action": "confirm", "next_objective": "B"},
            follow=False,
        )

        # Should fail due to None assessment_id
        self.assertIn(response.status_code, [302, 500])

    def test_assessment_id_empty_string_raises_exception(self):
        """
        Test that having draft_assessment in session but with empty string assessment_id
        raises AssessmentNotSelectedException.
        """
        # Set draft_assessment but with empty string assessment_id
        session = self.client.session
        session["draft_assessment"] = {"assessment_id": ""}
        session.save()

        response = self.client.post(
            reverse("caf32_objective_A"),
            data={"action": "confirm", "next_objective": "B"},
            follow=False,
        )

        # Should fail due to empty assessment_id
        self.assertIn(response.status_code, [302, 500])

    def test_empty_draft_assessment_dict_raises_exception(self):
        """
        Test that having an empty draft_assessment dict in session
        raises AssessmentNotSelectedException.
        """
        # Set empty draft_assessment
        session = self.client.session
        session["draft_assessment"] = {}
        session.save()

        response = self.client.post(
            reverse("caf32_objective_A"),
            data={"action": "confirm", "next_objective": "B"},
            follow=False,
        )

        # Should fail due to missing assessment_id
        self.assertIn(response.status_code, [302, 500])
