"""
Integration tests for TipDetailView, TipRecommendationsView and TipRecommendationActionView.

These cover:
  * TipDetailView - correct priority/other recommendation counts under the "1. Create TIP
    actions" section of ``tip/summary.html``.
  * TipRecommendationsView - the recommendations table renders the right category, the
    bulk-update prompt only appears for "other" recommendations that still have
    un-actioned items, and the bulk POST only marks the currently-filtered un-actioned
    items as reviewed (with no action planned).
  * TipRecommendationActionView - the form saves JSON action data correctly, supports the
    range of action paths (planned / not-planned / not-reviewed) and reloads previously
    saved data when the page is revisited.
"""
from datetime import datetime

from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from freezegun import freeze_time

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import (
    Assessment,
    Configuration,
    Organisation,
    RecommendationAction,
    Review,
    System,
    Tip,
    TipStatus,
    UserProfile,
)
from webcaf.webcaf.utils.review import get_review_recommendations


def _login_with_role(test_case, role_key: str, org_name: str | None = None) -> tuple[Client, UserProfile]:
    """Force-login a client as a user with the given role for the given organisation."""
    if org_name is None:
        org_name = test_case.organisation_name

    client = Client()
    user = test_case.org_map[org_name]["users"].get(role_key)
    if not user:
        user, _ = User.objects.get_or_create(username=test_case.email_from_username_and_org(role_key, org_name))
        org = Organisation.objects.get(name=org_name)
        UserProfile.objects.get_or_create(user=user, organisation=org, role=role_key)

    client.force_login(user)
    profile = UserProfile.objects.get(user=user, role=role_key)
    session = client.session
    session["current_profile_id"] = profile.id
    session.save()
    return client, profile


class TipViewsSetupMixin:
    """
    Builds an Assessment, Review, finalises the review (which auto-creates a Tip) and
    seeds the review's assessor response with one priority recommendation (A1.a) and
    two "other" recommendations (A1.b, A1.c).
    """

    def _seed_review(self):
        self.org = Organisation.objects.get(name=self.organisation_name)
        self.system = System.objects.get(name=self.system_name, organisation=self.org)

        Configuration.objects.create(
            name="2050 Assessment Period",
            config_data={
                "current_assessment_period": "49/50",
                "assessment_period_end": "31 March 2050 11:59pm",
                "default_framework": "caf32",
            },
        )

        self.assessment = Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period="49/50",
            review_type="independent",
            caf_profile="baseline",
        )

        self.review = Review.objects.create(assessment=self.assessment, status="in_progress")

        assessor_response = self.review.get_assessor_response()
        # Default every outcome to "achieved" with no recommendations so the recommendation
        # generator does not blow up on missing keys.
        for objective in self.assessment.get_all_caf_objectives():
            obj_data = assessor_response.setdefault(objective["code"], {})
            for principle in objective["principles"].values():
                for outcome in principle["outcomes"].values():
                    obj_data.setdefault(
                        outcome["code"],
                        {"review_data": {"review_decision": "achieved"}, "recommendations": []},
                    )

        # One priority recommendation (not achieved => priority).
        assessor_response["A"]["A1.a"] = {
            "review_data": {"review_decision": "not-achieved"},
            "recommendations": [{"title": "Risk A1.a", "text": "Fix A1.a"}],
        }
        # Two "other" recommendations (achieved, but reviewer added recommendations).
        assessor_response["A"]["A1.b"] = {
            "review_data": {"review_decision": "achieved"},
            "recommendations": [
                {"title": "Risk A1.b - One", "text": "Improve A1.b one"},
                {"title": "Risk A1.b - Two", "text": "Improve A1.b two"},
            ],
        }

        cyber_advisor_user = self.org_map[self.organisation_name]["users"]["cyber_advisor"]
        self.cyber_advisor_profile = UserProfile.objects.get(user=cyber_advisor_user, role="cyber_advisor")
        self.review.mark_review_complete(self.cyber_advisor_profile)
        self.review.finalise_review(self.cyber_advisor_profile)
        self.review.save()

        # finalise_review auto-creates the Tip. Grab the existing instance.
        self.tip = Tip.objects.get(review=self.review)
        self.tip.status = TipStatus.TO_DO
        self.tip.save()

        self._priority_recs = self._flatten("priority")
        self._other_recs = self._flatten("normal")

    def _flatten(self, mode):
        return [r for group in get_review_recommendations(self.review, mode) for r in group.recommendations]


@freeze_time("2050-01-15 10:00:00")
class TestTipDetailView(TipViewsSetupMixin, BaseViewTest):
    """Verify summary.html shows the correct counts under "1. Create TIP actions"."""

    def setUp(self):
        self._seed_review()

    def test_priority_and_other_counts_rendered_under_create_tip_actions(self):
        client, _ = _login_with_role(self, "organisation_lead")
        resp = client.get(reverse("tip:edit", kwargs={"pk": self.tip.pk}))
        self.assertEqual(resp.status_code, 200)

        # Sanity: context exposes the right numbers (1 priority A1.a, 2 other A1.b items).
        self.assertEqual(resp.context["priority_recommendations_count"], 1)
        self.assertEqual(resp.context["other_recommendations_count"], 2)

        body = resp.content.decode()
        # Section heading must be present.
        self.assertIn("1. Record TIP actions", body)
        # Priority link uses the count.
        self.assertIn("Read priority recommendations (1)", body)
        # Other link uses the count.
        self.assertIn("Read other recommendations (2)", body)

    def test_counts_update_when_review_has_no_recommendations(self):
        # Wipe the assessor response so neither priority nor normal recommendations exist.
        self.review.rollback_to_in_progress()
        self.review.save()
        assessor_response = self.review.get_assessor_response()
        assessor_response["A"]["A1.a"] = {
            "review_data": {"review_decision": "achieved"},
            "recommendations": [],
        }
        assessor_response["A"]["A1.b"] = {
            "review_data": {"review_decision": "achieved"},
            "recommendations": [],
        }
        self.review.mark_review_complete(self.cyber_advisor_profile)
        self.review.finalise_review(self.cyber_advisor_profile)
        self.review.save()

        client, _ = _login_with_role(self, "organisation_lead")
        resp = client.get(reverse("tip:edit", kwargs={"pk": self.tip.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["priority_recommendations_count"], 0)
        self.assertEqual(resp.context["other_recommendations_count"], 0)
        self.assertIn("Read priority recommendations (0)", resp.content.decode())
        self.assertIn("Read other recommendations (0)", resp.content.decode())

    def test_counts_increase_when_more_recommendations_added(self):
        # Add a second priority recommendation in objective B.
        self.review.rollback_to_in_progress()
        self.review.save()
        assessor_response = self.review.get_assessor_response()
        assessor_response.setdefault("B", {})["B1.a"] = {
            "review_data": {"review_decision": "not-achieved"},
            "recommendations": [
                {"title": "Risk B1.a One", "text": "Fix B1.a One"},
                {"title": "Risk B1.a Two", "text": "Fix B1.a Two"},
            ],
        }
        self.review.mark_review_complete(self.cyber_advisor_profile)
        self.review.finalise_review(self.cyber_advisor_profile)
        self.review.save()

        client, _ = _login_with_role(self, "organisation_lead")
        resp = client.get(reverse("tip:edit", kwargs={"pk": self.tip.pk}))
        self.assertEqual(resp.status_code, 200)
        # A1.a (1) + B1.a (2) priority items.
        self.assertEqual(resp.context["priority_recommendations_count"], 3)
        self.assertEqual(resp.context["other_recommendations_count"], 2)
        self.assertIn("Read priority recommendations (3)", resp.content.decode())
        self.assertIn("Read other recommendations (2)", resp.content.decode())


@freeze_time("2050-01-15 10:00:00")
class TestTipRecommendationsView(TipViewsSetupMixin, BaseViewTest):
    """Render of tip/recommendations.html and behaviour of the bulk-update flow."""

    def setUp(self):
        self._seed_review()

    def test_priority_category_renders_only_priority_rows(self):
        client, _ = _login_with_role(self, "organisation_lead")
        resp = client.get(reverse("tip:recommendations", kwargs={"pk": self.tip.pk, "recommendation_type": "priority"}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["recommendation_type"], "priority")
        titles = [r.title for r, _, _ in resp.context["all_recommendations"]]
        self.assertEqual(titles, ["Risk A1.a"])
        body = resp.content.decode()
        self.assertIn("Risk A1.a", body)
        # The h1 has line breaks - check pieces of it and the trailing "(1)" count.
        self.assertIn("Priority recommendations (1)", body)
        # Priority recommendations don't get a bulk-update form.
        self.assertNotIn(
            "Do you want to mark all remaining other recommendations as reviewed",
            body,
        )

    def test_other_category_renders_only_other_rows(self):
        client, _ = _login_with_role(self, "organisation_lead")
        resp = client.get(reverse("tip:recommendations", kwargs={"pk": self.tip.pk, "recommendation_type": "other"}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["recommendation_type"], "other")
        titles = sorted(r.title for r, _, _ in resp.context["all_recommendations"])
        self.assertEqual(titles, ["Risk A1.b - One", "Risk A1.b - Two"])
        body = resp.content.decode()
        self.assertIn("Risk A1.b - One", body)
        self.assertIn("Risk A1.b - Two", body)
        self.assertIn("Other recommendations (2)", body)

    def test_bulk_update_prompt_visible_when_other_recommendations_unreviewed(self):
        client, _ = _login_with_role(self, "organisation_lead")
        resp = client.get(reverse("tip:recommendations", kwargs={"pk": self.tip.pk, "recommendation_type": "other"}))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context.get("show_bulk_update"))
        self.assertIn(
            "Mark all recommendations as read",
            resp.content.decode(),
        )

    def test_bulk_update_prompt_hidden_when_all_other_recommendations_reviewed(self):
        # Mark every "other" recommendation as reviewed.
        for rec in self._other_recs:
            self.tip.set_recommendation_action(
                RecommendationAction(
                    recommendation_reviewed="yes",
                    action_type="action_not_planned",
                    recommendation_id=rec.id,
                    recommendation_category="other",
                    action_details={"action_not_planned_reason": "n/a"},
                    actioned_by=1,
                    actioned_time=datetime.now().isoformat(),
                )
            )
        self.tip.save()

        client, _ = _login_with_role(self, "organisation_lead")
        resp = client.get(reverse("tip:recommendations", kwargs={"pk": self.tip.pk, "recommendation_type": "other"}))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context.get("show_bulk_update", False))
        self.assertNotIn(
            "Do you want to mark all remaining other recommendations as reviewed",
            resp.content.decode(),
        )

    def test_bulk_update_prompt_not_shown_on_priority_view(self):
        # Priority category never offers the bulk-update prompt - even when items are
        # un-actioned.
        client, _ = _login_with_role(self, "organisation_lead")
        resp = client.get(reverse("tip:recommendations", kwargs={"pk": self.tip.pk, "recommendation_type": "priority"}))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context.get("show_bulk_update", False))

    def test_bulk_update_only_actions_currently_displayed_unreviewed_items(self):
        # Pre-action one of the two "other" recommendations as action_planned.
        already_actioned = self._other_recs[0]
        self.tip.set_recommendation_action(
            RecommendationAction(
                recommendation_reviewed="yes",
                action_type="action_planned",
                recommendation_id=already_actioned.id,
                recommendation_category="other",
                action_details={"action_taken_description": "Already done"},
                actioned_by=1,
                actioned_time=datetime.now().isoformat(),
            )
        )
        self.tip.save()

        client, _ = _login_with_role(self, "organisation_lead")
        url = reverse("tip:recommendations", kwargs={"pk": self.tip.pk, "recommendation_type": "other"})

        resp = client.post(
            url,
            {
                "confirm_bulk_review": "yes",
                "bulk_review_reason": "Cannot action right now",
            },
        )
        self.assertEqual(resp.status_code, 302)

        self.tip.refresh_from_db()
        # The already-actioned one is untouched.
        preserved = self.tip.get_action(already_actioned.id)
        self.assertIsNotNone(preserved)
        self.assertEqual(preserved.action_type, "action_planned")
        self.assertEqual(preserved.action_details.get("action_taken_description"), "Already done")

        # The other "other" recommendation is now bulk-actioned.
        target = self._other_recs[1]
        bulk_action = self.tip.get_action(target.id)
        self.assertIsNotNone(bulk_action)
        self.assertEqual(bulk_action.action_type, "action_not_planned")
        self.assertEqual(bulk_action.recommendation_category, "other")
        self.assertEqual(bulk_action.recommendation_reviewed, "yes")
        self.assertEqual(bulk_action.action_details.get("action_not_planned_reason"), "Updated through bulk review")

        # And no priority recommendations were touched by the bulk action.
        for rec in self._priority_recs:
            self.assertIsNone(self.tip.get_action(rec.id))

    def test_bulk_update_respects_filter_on_currently_displayed_items(self):
        # Add a third "other" recommendation in objective B so we can filter and confirm
        # that the bulk action only updates the rows in the filtered view.
        self.review.rollback_to_in_progress()
        self.review.save()
        assessor_response = self.review.get_assessor_response()
        assessor_response.setdefault("B", {})["B1.a"] = {
            "review_data": {"review_decision": "achieved"},
            "recommendations": [{"title": "Risk B1.a", "text": "Improve B1.a"}],
        }
        self.review.mark_review_complete(self.cyber_advisor_profile)
        self.review.finalise_review(self.cyber_advisor_profile)
        self.review.save()
        self._other_recs = self._flatten("normal")

        client, _ = _login_with_role(self, "organisation_lead")
        url = reverse("tip:recommendations", kwargs={"pk": self.tip.pk, "recommendation_type": "other"})

        # Filter by objective A only.
        resp = client.post(
            url + "?objective=A",
            {
                "confirm_bulk_review": "yes",
                "bulk_review_reason": "Filtered bulk action",
            },
        )
        self.assertEqual(resp.status_code, 302)

        self.tip.refresh_from_db()
        # A-side "other" recommendations should be marked.
        for rec in self._other_recs:
            action = self.tip.get_action(rec.id)
            if rec.objective == "A":
                self.assertIsNotNone(action, f"A-side recommendation {rec.id} should have been bulk-actioned")
                self.assertEqual(action.action_type, "action_not_planned")
                self.assertEqual(action.action_details.get("action_not_planned_reason"), "Updated through bulk review")
            else:
                self.assertIsNone(action, f"B-side recommendation {rec.id} must not have been touched")

    def test_bulk_update_no_does_not_create_actions(self):
        client, _ = _login_with_role(self, "organisation_lead")
        url = reverse("tip:recommendations", kwargs={"pk": self.tip.pk, "recommendation_type": "other"})

        resp = client.post(
            url,
            {
                "confirm_bulk_review": "no",
                "bulk_review_reason": "",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.tip.refresh_from_db()
        for rec in self._other_recs:
            self.assertIsNone(self.tip.get_action(rec.id))

    def test_bulk_update_on_priority_view_is_rejected(self):
        # Even if the bulk update form were submitted against the priority view, the
        # view should refuse to apply changes (priority cannot be bulk-actioned).
        client, _ = _login_with_role(self, "organisation_lead")
        url = reverse("tip:recommendations", kwargs={"pk": self.tip.pk, "recommendation_type": "priority"})

        resp = client.post(
            url,
            {
                "confirm_bulk_review": "yes",
                "bulk_review_reason": "Should not apply",
            },
        )
        # Returns 200 because form_invalid re-renders the form.
        self.assertEqual(resp.status_code, 200)
        self.tip.refresh_from_db()
        for rec in self._priority_recs:
            self.assertIsNone(self.tip.get_action(rec.id))


@freeze_time("2050-01-15 10:00:00")
class TestTipRecommendationActionView(TipViewsSetupMixin, BaseViewTest):
    """Verifies JSON action data is stored and reloaded correctly."""

    def setUp(self):
        self._seed_review()
        self.priority_rec = self._priority_recs[0]
        self.other_recs = self._other_recs

    def _action_url(self, recommendation, recommendation_type="priority", query_string=""):
        url = reverse(
            "tip:recommendation-action",
            kwargs={
                "pk": self.tip.pk,
                "recommendation_id": recommendation.id,
                "recommendation_type": recommendation_type,
            },
        )
        return f"{url}?{query_string}" if query_string else url

    def _post_planned_action(self, client, recommendation, recommendation_type="priority", overrides=None):
        """Submit a fully-populated action_planned form. ``overrides`` may patch fields."""
        payload = {
            "recommendation_id": recommendation.id,
            "recommendation_category": recommendation_type,
            "recommendation_reviewed": "yes",
            "recommendation_actioned": "action_planned",
            "action_owner": "Alice Owner",
            "resources_available": "yes",
            "budget_available": "no",
            "action_taken_description": "Patch the system and review logs",
            "target_date_provided": "yes",
            "target_day_day": "15",
            "target_day_month": "6",
            "target_day_year": "2027",
            "target_date_unavailable_reason": "",
            "action_not_planned_reason": "",
            "submit_action": "back_to_summary",
        }
        if overrides:
            payload.update(overrides)
        return client.post(self._action_url(recommendation, recommendation_type), payload)

    def test_get_initial_empty_when_no_existing_action(self):
        client, _ = _login_with_role(self, "organisation_lead")
        resp = client.get(self._action_url(self.priority_rec))
        self.assertEqual(resp.status_code, 200)
        # No saved action yet - the form should be unbound to existing data.
        form = resp.context["form"]
        self.assertIsNone(form["recommendation_actioned"].value())
        self.assertEqual(resp.context["current_recommendation"].id, self.priority_rec.id)
        self.assertEqual(resp.context["mode"], "view")

    def test_action_planned_is_persisted_in_json(self):
        client, _ = _login_with_role(self, "organisation_lead")
        resp = self._post_planned_action(client, self.priority_rec)
        self.assertEqual(resp.status_code, 302)
        # Redirect goes back to the recommendations summary view.
        self.assertIn(
            reverse("tip:recommendations", kwargs={"pk": self.tip.pk, "recommendation_type": "priority"}),
            resp.url,
        )

        # Verify raw JSON shape stored on the Tip.
        self.tip.refresh_from_db()
        stored = self.tip.tip_data["recommendation_actions"][self.priority_rec.id]
        self.assertEqual(stored["action_type"], "action_planned")
        self.assertEqual(stored["recommendation_id"], self.priority_rec.id)
        self.assertEqual(stored["recommendation_category"], "priority")
        self.assertEqual(stored["recommendation_reviewed"], "yes")
        details = stored["action_details"]
        self.assertEqual(details["action_owner"], "Alice Owner")
        self.assertEqual(details["resources_available"], "yes")
        self.assertEqual(details["budget_available"], "no")
        self.assertEqual(details["action_taken_description"], "Patch the system and review logs")
        self.assertEqual(details["target_date_provided"], "yes")
        self.assertEqual(details["target_day_day"], 15)
        self.assertEqual(details["target_day_month"], 6)
        self.assertEqual(details["target_day_year"], 2027)

    def test_action_not_planned_is_persisted(self):
        client, _ = _login_with_role(self, "organisation_lead")
        resp = client.post(
            self._action_url(self.priority_rec),
            {
                "recommendation_id": self.priority_rec.id,
                "recommendation_category": "priority",
                "recommendation_reviewed": "yes",
                "recommendation_actioned": "action_not_planned",
                "action_not_planned_reason": "Mitigating control already in place",
                "submit_action": "back_to_summary",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.tip.refresh_from_db()
        stored = self.tip.tip_data["recommendation_actions"][self.priority_rec.id]
        self.assertEqual(stored["action_type"], "action_not_planned")
        self.assertEqual(stored["action_details"], {"action_not_planned_reason": "Mitigating control already in place"})

    def test_reviewed_no_clears_any_existing_action(self):
        # Seed an existing action so we can verify it gets reset.
        self.tip.set_recommendation_action(
            RecommendationAction(
                recommendation_reviewed="yes",
                action_type="action_planned",
                recommendation_id=self.priority_rec.id,
                recommendation_category="priority",
                action_details={"action_taken_description": "old action"},
                actioned_by=1,
                actioned_time=datetime.now().isoformat(),
            )
        )
        self.tip.save()

        client, _ = _login_with_role(self, "organisation_lead")
        resp = client.post(
            self._action_url(self.priority_rec),
            {
                "recommendation_id": self.priority_rec.id,
                "recommendation_category": "priority",
                "recommendation_reviewed": "no",
                "submit_action": "back_to_summary",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.tip.refresh_from_db()
        self.assertIsNone(self.tip.get_action(self.priority_rec.id))

    def test_existing_action_is_reloaded_when_editing(self):
        # Seed a fully-formed planned action.
        self.tip.set_recommendation_action(
            RecommendationAction(
                recommendation_reviewed="yes",
                action_type="action_planned",
                recommendation_id=self.priority_rec.id,
                recommendation_category="priority",
                action_details={
                    "action_owner": "Bob Owner",
                    "resources_available": "no",
                    "budget_available": "yes",
                    "action_taken_description": "Apply patches",
                    "target_date_provided": "no",
                    "target_day_day": None,
                    "target_day_month": None,
                    "target_day_year": None,
                    "target_date_unavailable_reason": "Vendor timeline unclear",
                },
                actioned_by=1,
                actioned_time=datetime.now().isoformat(),
            )
        )
        self.tip.save()

        client, _ = _login_with_role(self, "organisation_lead")
        resp = client.get(self._action_url(self.priority_rec))
        self.assertEqual(resp.status_code, 200)
        form = resp.context["form"]

        # Top-level fields restore.
        self.assertEqual(form["recommendation_reviewed"].value(), "yes")
        self.assertEqual(form["recommendation_actioned"].value(), "action_planned")
        self.assertEqual(form["recommendation_category"].value(), "priority")
        self.assertEqual(form["recommendation_id"].value(), self.priority_rec.id)
        # Action details restore.
        self.assertEqual(form["action_owner"].value(), "Bob Owner")
        self.assertEqual(form["resources_available"].value(), "no")
        self.assertEqual(form["budget_available"].value(), "yes")
        self.assertEqual(form["action_taken_description"].value(), "Apply patches")
        self.assertEqual(form["target_date_provided"].value(), "no")
        self.assertEqual(form["target_date_unavailable_reason"].value(), "Vendor timeline unclear")
        # Rendered HTML reflects the persisted values too.
        self.assertIn("Bob Owner", resp.content.decode())
        self.assertIn("Apply patches", resp.content.decode())

    def test_edit_then_save_overwrites_existing_action(self):
        # Seed an existing planned action.
        self.tip.set_recommendation_action(
            RecommendationAction(
                recommendation_reviewed="yes",
                action_type="action_planned",
                recommendation_id=self.priority_rec.id,
                recommendation_category="priority",
                action_details={
                    "action_owner": "Old Owner",
                    "resources_available": "yes",
                    "budget_available": "yes",
                    "action_taken_description": "Initial plan",
                    "target_date_provided": "yes",
                    "target_day_day": 10,
                    "target_day_month": 6,
                    "target_day_year": 2027,
                    "target_date_unavailable_reason": "",
                },
                actioned_by=1,
                actioned_time=datetime.now().isoformat(),
            )
        )
        self.tip.save()

        client, _ = _login_with_role(self, "organisation_lead")
        resp = self._post_planned_action(
            client,
            self.priority_rec,
            overrides={
                "action_owner": "Updated Owner",
                "action_taken_description": "Updated plan",
                "target_day_day": "1",
                "target_day_month": "12",
                "target_day_year": "2028",
            },
        )
        self.assertEqual(resp.status_code, 302)

        self.tip.refresh_from_db()
        stored = self.tip.tip_data["recommendation_actions"][self.priority_rec.id]
        details = stored["action_details"]
        self.assertEqual(details["action_owner"], "Updated Owner")
        self.assertEqual(details["action_taken_description"], "Updated plan")
        self.assertEqual(details["target_day_day"], 1)
        self.assertEqual(details["target_day_month"], 12)
        self.assertEqual(details["target_day_year"], 2028)

    def test_required_fields_validation_when_planning_action(self):
        client, _ = _login_with_role(self, "organisation_lead")
        # action_planned but missing all detail fields.
        resp = client.post(
            self._action_url(self.priority_rec),
            {
                "recommendation_id": self.priority_rec.id,
                "recommendation_category": "priority",
                "recommendation_reviewed": "yes",
                "recommendation_actioned": "action_planned",
                "submit_action": "back_to_summary",
            },
        )
        self.assertEqual(resp.status_code, 200)
        form = resp.context["form"]
        # The expected required fields should be flagged on the form.
        for field in (
            "action_owner",
            "resources_available",
            "action_taken_description",
            "target_date_provided",
            "budget_available",
        ):
            self.assertIn(field, form.errors, f"Expected '{field}' to be a required field error")
        self.tip.refresh_from_db()
        self.assertIsNone(self.tip.get_action(self.priority_rec.id))

    def test_required_action_not_planned_reason(self):
        client, _ = _login_with_role(self, "organisation_lead")
        resp = client.post(
            self._action_url(self.priority_rec),
            {
                "recommendation_id": self.priority_rec.id,
                "recommendation_category": "priority",
                "recommendation_reviewed": "yes",
                "recommendation_actioned": "action_not_planned",
                "action_not_planned_reason": "",
                "submit_action": "back_to_summary",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("action_not_planned_reason", resp.context["form"].errors)

    def test_target_date_required_fields_when_target_date_provided_yes(self):
        client, _ = _login_with_role(self, "organisation_lead")
        resp = self._post_planned_action(
            client,
            self.priority_rec,
            overrides={
                "target_date_provided": "yes",
                "target_day_day": "",
                "target_day_month": "",
                "target_day_year": "",
            },
        )
        self.assertEqual(resp.status_code, 200)
        for field in ("target_day_day", "target_day_month", "target_day_year"):
            self.assertIn(
                field, resp.context["form"].errors, f"{field} should be required when target_date_provided=yes"
            )

    def test_target_date_unavailable_reason_required_when_no_target_date(self):
        client, _ = _login_with_role(self, "organisation_lead")
        resp = self._post_planned_action(
            client,
            self.priority_rec,
            overrides={
                "target_date_provided": "no",
                "target_day_day": "",
                "target_day_month": "",
                "target_day_year": "",
                "target_date_unavailable_reason": "",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("target_date_unavailable_reason", resp.context["form"].errors)

    def test_save_and_continue_to_next_recommendation(self):
        # Use the two "other" recs so there is a next.
        client, _ = _login_with_role(self, "organisation_lead")
        first, second = self.other_recs[0], self.other_recs[1]

        resp = client.post(
            self._action_url(first, recommendation_type="other"),
            {
                "recommendation_id": first.id,
                "recommendation_category": "other",
                "recommendation_reviewed": "yes",
                "recommendation_actioned": "action_not_planned",
                "action_not_planned_reason": "Low risk",
                "submit_action": "next_recommendation",
                "next_recommendation": second.id,
            },
        )
        self.assertEqual(resp.status_code, 302)
        # Redirects to the next recommendation's URL.
        self.assertIn(
            reverse(
                "tip:recommendation-action",
                kwargs={"pk": self.tip.pk, "recommendation_id": second.id, "recommendation_type": "other"},
            ),
            resp.url,
        )

    def test_back_to_answers_submit_action(self):
        client, _ = _login_with_role(self, "organisation_lead")
        resp = client.post(
            self._action_url(self.priority_rec),
            {
                "recommendation_id": self.priority_rec.id,
                "recommendation_category": "priority",
                "recommendation_reviewed": "yes",
                "recommendation_actioned": "action_not_planned",
                "action_not_planned_reason": "Not applicable",
                "submit_action": "back_to_answers",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("tip:review-answers", kwargs={"pk": self.tip.pk}), resp.url)

    def test_query_string_preserved_on_redirect(self):
        client, _ = _login_with_role(self, "organisation_lead")
        resp = client.post(
            self._action_url(self.priority_rec, query_string="objective=A&status=not_reviewed"),
            {
                "recommendation_id": self.priority_rec.id,
                "recommendation_category": "priority",
                "recommendation_reviewed": "yes",
                "recommendation_actioned": "action_not_planned",
                "action_not_planned_reason": "Documented elsewhere",
                "submit_action": "back_to_summary",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("objective=A", resp.url)
        self.assertIn("status=not_reviewed", resp.url)

    def test_change_answer_mode_in_context(self):
        client, _ = _login_with_role(self, "organisation_lead")
        resp = client.get(self._action_url(self.priority_rec, query_string="mode=change_answer"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["mode"], "change_answer")
        # Template shows the "Save and return to answers" button in change-answer mode.
        self.assertIn("Save and return to answers", resp.content.decode())
