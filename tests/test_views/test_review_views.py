from django.test import Client
from django.urls import reverse
from freezegun import freeze_time

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import (
    Assessment,
    Assessor,
    Configuration,
    Organisation,
    Review,
    System,
    UserProfile,
)


# Fixing the time in future so the configuration does not conflict with any existing data in the database.
@freeze_time("2050-01-15 10:00:00")
class TestReviewIndexVisibility(BaseViewTest):
    """
    View tests for ReviewIndexView and related access rules defined in
    webcaf.webcaf.views.assessor.review.BaseReviewMixin.get_reviews_for_user.

    Expectations:
    - cyber_advisor and organisation_lead can see/modify all submitted reviews for the
      current organisation and current assessment period.
    - assessor and reviewer can only see reviews that are assigned to the Assessor
      they belong to (i.e. the Assessor has them in members M2M).
    """

    def setUp(self):
        self.client = Client()
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
        self.config = Configuration.objects.get_default_config()
        self.period = self.config.get_current_assessment_period()

        # Two assessors in the same org
        self.assessor_a = Assessor.objects.create(
            organisation=self.org,
            name="Assessor A",
            email="a@example.com",
            contact_name="A",
            address="1 St",
            assessor_type="independent",
            is_active=True,
        )
        self.assessor_b = Assessor.objects.create(
            organisation=self.org,
            name="Assessor B",
            email="b@example.com",
            contact_name="B",
            address="2 St",
            assessor_type="independent",
            is_active=True,
        )

        # Reviews in current org and current period
        self.assessment_ok = Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period=self.period,
        )
        self.review_ok = Review.objects.create(assessment=self.assessment_ok, assessed_by=self.assessor_a)

        # Same org but different period (should be hidden)
        self.assessment_other_period = Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period="1900",  # obviously not current
        )
        self.review_other_period = Review.objects.create(
            assessment=self.assessment_other_period, assessed_by=self.assessor_a
        )

        # Different org (should be hidden)
        self.foreign_org, _ = Organisation.objects.get_or_create(name="Foreign Org For ReviewIndex")
        self.foreign_system, _ = System.objects.get_or_create(name="Foreign Sys", organisation=self.foreign_org)
        self.assessment_foreign = Assessment.objects.create(
            system=self.foreign_system,
            status="submitted",
            assessment_period=self.period,
        )
        self.review_foreign = Review.objects.create(assessment=self.assessment_foreign, assessed_by=None)

    def _login_with_role(self, role_key: str) -> tuple[Client, UserProfile]:
        client = Client()

        user = self.org_map[self.organisation_name]["users"].get(role_key)  # type: ignore
        if not user:
            # Create the user and profile if this role was not part of base fixture
            from django.contrib.auth.models import User

            user, _ = User.objects.get_or_create(
                username=self.email_from_username_and_org(role_key, self.organisation_name)  # type: ignore
            )
            UserProfile.objects.get_or_create(user=user, organisation=self.org, role=role_key)

        client.force_login(user)
        profile = UserProfile.objects.get(user=user, role=role_key)
        session = client.session
        session["current_profile_id"] = profile.id
        session.save()
        return client, profile

    def test_admin_roles_see_only_current_org_and_period(self):
        for role in ("cyber_advisor", "organisation_lead"):
            client, _ = self._login_with_role(role)
            resp = client.get(reverse("review-list"))
            self.assertEqual(resp.status_code, 200)
            reviews = list(resp.context["reviews"])  # provided by ReviewIndexView
            self.assertIn(self.review_ok, reviews)
            self.assertNotIn(self.review_other_period, reviews)
            self.assertNotIn(self.review_foreign, reviews)

    def test_assessor_and_reviewer_only_see_reviews_for_their_assessor(self):
        # Create assessor and reviewer profiles and attach them as members to assessor_a
        from django.contrib.auth.models import User

        assessor_user, _ = User.objects.get_or_create(
            username=self.email_from_username_and_org("assessor", self.organisation_name)
        )
        assessor_profile, _ = UserProfile.objects.get_or_create(
            user=assessor_user, organisation=self.org, role="assessor"
        )
        reviewer_user, _ = User.objects.get_or_create(
            username=self.email_from_username_and_org("reviewer", self.organisation_name)
        )
        reviewer_profile, _ = UserProfile.objects.get_or_create(
            user=reviewer_user, organisation=self.org, role="reviewer"
        )
        self.assessor_a.members.add(assessor_profile, reviewer_profile)

        # Create another review under assessor_b (should not be visible to above users)
        assessment_hidden = Assessment.objects.create(
            system=self.org_map[self.organisation_name]["systems"]["Big system"],
            status="submitted",
            assessment_period=self.period,
        )
        hidden_review = Review.objects.create(assessment=assessment_hidden, assessed_by=self.assessor_b)

        # Check for assessor role
        client_a, _ = self._login_with_role("assessor")
        resp = client_a.get(reverse("review-list"))
        self.assertEqual(resp.status_code, 200)
        reviews = list(resp.context["reviews"])  # filtered by membership
        self.assertIn(self.review_ok, reviews)
        self.assertNotIn(hidden_review, reviews)

        # Check for reviewer role
        client_r, _ = self._login_with_role("reviewer")
        resp = client_r.get(reverse("review-list"))
        self.assertEqual(resp.status_code, 200)
        reviews = list(resp.context["reviews"])  # filtered by membership
        self.assertIn(self.review_ok, reviews)
        self.assertNotIn(hidden_review, reviews)


# Fixing the time in future so the configuration does not conflict with any existing data in the database.
@freeze_time("2050-01-15 10:00:00")
class TestReviewModifyLoggingAndAccess(BaseViewTest):
    """
    Cover modification flows in EditReviewSystemView and scope confirmation in SystemAndScopeView.
    - Admin roles should be able to modify allowed fields on the system via review endpoints.
    - All modifications are logged correctly in assessor_actions and completion is reset.
    - Non-member assessor/reviewer users must not be able to access reviews outside their membership.
    """

    def setUp(self):
        self.org = Organisation.objects.get(name=self.organisation_name)
        self.system = self.test_system

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

        self.assessor = Assessor.objects.create(
            organisation=self.org,
            name="Logger",
            email="log@example.com",
            contact_name="Log",
            address="10 St",
            assessor_type="independent",
            is_active=True,
        )

        self.assessment = Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period=self.period,
        )
        self.review = Review.objects.create(assessment=self.assessment, assessed_by=self.assessor)

        # Prime completion so we can assert it resets on change
        assessor_response = self.review.get_assessor_response()
        assessor_response.setdefault("system_and_scope", {})["completed"] = "yes"
        self.review.save()

        # Login as cyber advisor (allowed to modify)
        self.client = Client()
        user = self.org_map[self.organisation_name]["users"]["cyber_advisor"]
        self.client.force_login(user)
        self.profile = UserProfile.objects.get(user=user, role="cyber_advisor")
        session = self.client.session
        session["current_profile_id"] = self.profile.id
        session.save()

    def _post_change(self, label: str, value):
        url = reverse("edit-review-system", kwargs={"pk": self.review.id, "field_to_change": label})
        resp = self.client.post(url, data={self._map_to_field(label): value}, follow=False)
        self.assertIn(resp.status_code, (302, 303))

    def _map_to_field(self, key: str) -> str:
        mapping = {
            "System description": "system_type",
            "Previous GovAssure self-assessments": "last_assessed",
            "System ownership": "system_owner",
            "Hosting and connectivity": "hosting_type",
            "Corporate services": "corporate_services",
        }
        return mapping[key]

    def test_modify_allowed_fields_logs_and_resets_completion(self):
        # Change each allowed field once to generate records
        self._post_change("System description", "is_critical_for_day_to_day_operations")
        self._post_change("Previous GovAssure self-assessments", "assessed_in_2425")
        self._post_change("System ownership", ["owned_by_organisation_being_assessed"])  # MultiSelect
        self._post_change("Hosting and connectivity", ["hosted_on_premises"])  # MultiSelect
        self._post_change("Corporate services", ["hr", "other"])  # MultiSelect

        # Reload review and verify logging
        self.review.refresh_from_db()
        assessor_response = self.review.get_assessor_response()
        records = assessor_response.get("assessor_actions", {}).get("records", [])
        # We expect at least 5 change records appended
        self.assertGreaterEqual(len(records), 5)
        last_record = records[-1]
        self.assertEqual(last_record.get("type"), "modify")
        self.assertEqual(last_record.get("details", {}).get("what"), "system")
        self.assertEqual(last_record.get("details", {}).get("id"), self.system.id)
        self.assertIn("Updated the field", last_record.get("details", {}).get("description", ""))

        # last_updated_by is set
        self.assertIsNotNone(self.review.last_updated_by)

        # completion reset
        self.assertFalse(self.review.is_system_and_scope_completed)

    def test_non_member_assessor_cannot_access_foreign_review(self):
        # Create a different assessor and attach review there
        other_assessor = Assessor.objects.create(
            organisation=self.org,
            name="Other",
            email="o@example.com",
            contact_name="O",
            address="22 St",
            assessor_type="independent",
        )
        other_assessment = Assessment.objects.create(
            # Chose a different system for this assessment
            system=self.org_map[self.organisation_name]["systems"]["Big system"],
            status="submitted",
            assessment_period=self.period,
        )
        other_review = Review.objects.create(assessment=other_assessment, assessed_by=other_assessor)

        # Create assessor-profile user and set as member of self.assessor (not other_assessor)
        from django.contrib.auth.models import User

        auser, _ = User.objects.get_or_create(
            username=self.email_from_username_and_org("assessor_view", self.organisation_name)
        )
        aprofile, _ = UserProfile.objects.get_or_create(user=auser, organisation=self.org, role="assessor")
        self.assessor.members.add(aprofile)

        client = Client()
        client.force_login(auser)
        session = client.session
        session["current_profile_id"] = aprofile.id
        session.save()

        # Attempt to access details for other_review should 404 (queryset filter excludes it)
        resp = client.get(reverse("edit-review", kwargs={"pk": other_review.id}))
        self.assertEqual(resp.status_code, 404)

    def test_system_and_scope_confirm_marks_completed_and_moves_status(self):
        # Ensure initial status is to_do
        self.assertEqual(self.review.status, "to_do")

        # Post confirm action
        resp = self.client.post(
            reverse("system-and-scope", kwargs={"pk": self.review.id}), data={"action": "confirm"}, follow=False
        )
        self.assertIn(resp.status_code, (302, 303))

        # Reload and verify
        self.review.refresh_from_db()
        self.assertTrue(self.review.is_system_and_scope_completed)
        self.assertEqual(self.review.status, "in_progress")
