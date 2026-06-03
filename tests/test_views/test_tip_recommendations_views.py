from django.test import Client
from django.urls import reverse
from django.utils import timezone
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
    UserProfile,
)


@freeze_time("2050-01-15 10:00:00")
class TestTipRecommendationsView(BaseViewTest):
    def setUp(self):
        self.client = Client()
        self.org = Organisation.objects.get(name=self.organisation_name)
        self.system = System.objects.get(name=self.system_name, organisation=self.org)

        # Setup configuration
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

        # Create submitted assessment
        self.assessment = Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period=self.period,
            review_type="independent",
            caf_profile="baseline",
        )

        # Create review and populate it with recommendations
        self.review = Review.objects.create(assessment=self.assessment, status="in_progress")

        # Add assessor response data
        # We need to know some valid objective and outcome codes for caf32
        # A1.a and A1.b are common.
        assessor_response = self.review.get_assessor_response()

        # Populate all outcomes with default data to avoid KeyError
        for objective in self.assessment.get_all_caf_objectives():
            obj_data = assessor_response.setdefault(objective["code"], {})
            for principle in objective["principles"].values():
                for outcome in principle["outcomes"].values():
                    obj_data.setdefault(
                        outcome["code"], {"review_data": {"review_decision": "achieved"}, "recommendations": []}
                    )

        # Priority recommendation (not achieved)
        assessor_response["A"]["A1.a"] = {
            "review_data": {"review_decision": "not-achieved"},
            "recommendations": [{"title": "Risk A1.a", "text": "Fix A1.a"}],
        }

        # Normal recommendation (achieved but has recommendation)
        assessor_response["A"]["A1.b"] = {
            "review_data": {"review_decision": "achieved"},
            "recommendations": [{"title": "Risk A1.b", "text": "Improve A1.b"}],
        }

        # Finalize the review
        cyber_advisor_user = self.org_map[self.organisation_name]["users"]["cyber_advisor"]
        self.cyber_advisor_profile = UserProfile.objects.get(user=cyber_advisor_user, role="cyber_advisor")

        self.review.mark_review_complete(self.cyber_advisor_profile)
        self.review.finalise_review(self.cyber_advisor_profile)
        self.review.save()

        # Create Tip
        self.tip = Tip.objects.get(review=self.review, status=TipStatus.TO_DO)

    def _login_with_role(self, role_key: str, org_name: str | None = None) -> tuple[Client, UserProfile]:
        if org_name is None:
            org_name = self.organisation_name  # type: ignore[attr-defined]

        client = Client()
        user = self.org_map[org_name]["users"].get(role_key)
        if not user:
            from django.contrib.auth.models import User

            user, _ = User.objects.get_or_create(username=self.email_from_username_and_org(role_key, org_name))
            org = Organisation.objects.get(name=org_name)
            UserProfile.objects.get_or_create(user=user, organisation=org, role=role_key)

        client.force_login(user)
        profile = UserProfile.objects.get(user=user, role=role_key)
        session = client.session
        session["current_profile_id"] = profile.id
        session.save()
        return client, profile

    def test_access_control(self):
        # Allowed roles: cyber_advisor, organisation_lead
        for role in ["cyber_advisor", "organisation_lead"]:
            client, _ = self._login_with_role(role)
            url = reverse("tip:recommendations", kwargs={"pk": self.tip.pk, "recommendation_type": "priority"})
            resp = client.get(url)
            self.assertEqual(resp.status_code, 200, f"Role {role} should have access")

        # Disallowed roles: assessor, reviewer
        for role in ["assessor", "reviewer"]:
            client, _ = self._login_with_role(role)
            url = reverse("tip:recommendations", kwargs={"pk": self.tip.pk, "recommendation_type": "priority"})
            resp = client.get(url)
            self.assertEqual(resp.status_code, 403, f"Role {role} should not have access")

        # Different organisation
        other_org_name = "Large organisation"
        if other_org_name == self.organisation_name:
            other_org_name = "Medium organisation"

        client, _ = self._login_with_role("cyber_advisor", org_name=other_org_name)
        url = reverse("tip:recommendations", kwargs={"pk": self.tip.pk, "recommendation_type": "priority"})
        resp = client.get(url)
        # Should be 404 because get_queryset filters by organisation
        self.assertEqual(resp.status_code, 404, "Cyber advisor from other org should not see this tip")

    def test_recommendation_types_display(self):
        client, _ = self._login_with_role("cyber_advisor")

        # Priority recommendations
        url = reverse("tip:recommendations", kwargs={"pk": self.tip.pk, "recommendation_type": "priority"})
        resp = client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["recommendation_type"], "priority")
        recommendations = resp.context["all_recommendations"]
        # Should have A1.a
        rec_titles = [r.title for r, group, _ in recommendations]
        self.assertIn("Risk A1.a", rec_titles)
        self.assertNotIn("Risk A1.b", rec_titles)

        # Normal (other) recommendations
        url = reverse("tip:recommendations", kwargs={"pk": self.tip.pk, "recommendation_type": "other"})
        resp = client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["recommendation_type"], "other")
        recommendations = resp.context["all_recommendations"]
        # Should have A1.b
        rec_titles = [r.title for r, group, _ in recommendations]
        self.assertIn("Risk A1.b", rec_titles)
        self.assertNotIn("Risk A1.a", rec_titles)

    def test_filtering_by_objective(self):
        # Add another recommendation in a different objective
        self.review.rollback_to_in_progress()
        self.review.save()
        assessor_response = self.review.get_assessor_response()
        assessor_response.setdefault("B", {})["B1.a"] = {
            "review_data": {"review_decision": "not-achieved"},
            "recommendations": [{"title": "Risk B1.a", "text": "Fix B1.a"}],
        }
        self.review.mark_review_complete(self.cyber_advisor_profile)
        self.review.finalise_review(self.cyber_advisor_profile)
        self.review.save()

        client, _ = self._login_with_role("cyber_advisor")
        url = reverse("tip:recommendations", kwargs={"pk": self.tip.pk, "recommendation_type": "priority"})

        # Filter by objective A
        resp = client.get(url, {"objective": "A"})
        self.assertEqual(resp.status_code, 200)
        rec_objectives = {r.objective for r, group, _ in resp.context["all_recommendations"]}
        self.assertIn("A", rec_objectives)
        self.assertNotIn("B", rec_objectives)

        # Filter by objective B
        resp = client.get(url, {"objective": "B"})
        self.assertEqual(resp.status_code, 200)
        rec_objectives = {r.objective for r, group, _ in resp.context["all_recommendations"]}
        self.assertIn("B", rec_objectives)
        self.assertNotIn("A", rec_objectives)

    def test_filtering_by_status(self):
        client, _ = self._login_with_role("cyber_advisor")
        url = reverse("tip:recommendations", kwargs={"pk": self.tip.pk, "recommendation_type": "priority"})

        # Initial status: all not reviewed
        resp = client.get(url, {"status": "not_reviewed"})
        self.assertEqual(len(resp.context["all_recommendations"]), 1)  # A1.a is priority

        resp = client.get(url, {"status": "action_added"})
        self.assertEqual(len(resp.context["all_recommendations"]), 0)

        # Add an action to A1.a
        # We need to find the recommendation ID first
        from webcaf.webcaf.utils.review import get_review_recommendations

        recs = list(get_review_recommendations(self.review, "priority"))
        rec_to_action = recs[0].recommendations[0]

        actions = self.tip.tip_data.get("actions", {})
        actions[rec_to_action.id] = {
            "action_type": "action_planned",
            "action_details": {"detail": "Doing it"},
            "recommendation_category": "priority",
            "recommendation_id": rec_to_action.id,
            "recommendation_reviewed": True,
            "actioned_time": timezone.now().isoformat(),
            "actioned_by": 1,
        }
        self.tip.tip_data["recommendation_actions"] = actions
        self.tip.save()

        # Now filter by action_planned
        resp = client.get(url, {"status": "action_planned"})
        self.assertEqual(len(resp.context["all_recommendations"]), 1)
        self.assertEqual(resp.context["all_recommendations"][0][0].id, rec_to_action.id)

        # Filter by not_reviewed should now be empty for priority
        resp = client.get(url, {"status": "not_reviewed"})
        self.assertEqual(len(resp.context["all_recommendations"]), 0)
