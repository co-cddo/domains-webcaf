from django.test import Client
from django.urls import reverse

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import (
    Assessment,
    Assessor,
    Organisation,
    Review,
    System,
    UserProfile,
)


class TestReviewIndexView(BaseViewTest):
    """
    Tests for ReviewIndexView (assessor dashboard).

    Current behaviour in the view:
    - Requires login only.
    - Shows reviews where the related assessment is in status 'submitted' and the
      assessment's system belongs to the current session organisation.

    """

    def setUp(self):
        self.client = Client()
        # Create an assessor-role user in the default organisation
        org = Organisation.objects.get(name=self.organisation_name)
        username = self.email_from_username_and_org("assessor", self.organisation_name)
        from django.contrib.auth.models import User

        self.assessor_user, _ = User.objects.get_or_create(username=username)
        self.assessor_profile, _ = UserProfile.objects.get_or_create(
            user=self.assessor_user, organisation=org, role="assessor"
        )
        self.client.force_login(self.assessor_user)
        # Set the current profile in session as required by SessionUtil
        session = self.client.session
        session["current_profile_id"] = self.assessor_profile.id
        session.save()

        # Create submitted assessment in same org and a review
        self.system = System.objects.get(name=self.system_name, organisation=org)
        self.submitted_assessment = Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period="2025",
        )
        # Create an Assessor entity for the organisation and assign a review to it
        self.org_assessor = Assessor.objects.create(
            organisation=org,
            name="Active Assessor",
            email="assessor@example.com",
            contact_name="Alice",
            address="1 Road",
            assessor_type="independent",
        )
        self.visible_review = Review.objects.create(
            assessment=self.submitted_assessment,
            assessed_by=self.org_assessor,
        )

        # Create another org with its own submitted assessment and review – must not be visible
        other_org, _ = Organisation.objects.get_or_create(name="Other Org")
        other_system, _ = System.objects.get_or_create(name="Other System", organisation=other_org)
        other_assessment = Assessment.objects.create(
            system=other_system,
            status="submitted",
            assessment_period="2025",
        )
        self.other_review = Review.objects.create(
            assessment=other_assessment,
            assessed_by=None,
        )

    def test_lists_only_reviews_for_current_org_and_submitted(self):
        resp = self.client.get(reverse("review-list"))
        self.assertEqual(resp.status_code, 200)
        reviews = list(resp.context["reviews"])  # provided by view's context
        # Should include the review in the same organisation
        self.assertIn(self.visible_review, reviews)
        # Should exclude the review from another organisation
        self.assertNotIn(self.other_review, reviews)

    def test_login_required_for_assessor_index(self):
        # New client without login should be redirected to login (OIDC init)
        anon = Client()
        resp = anon.get(reverse("review-list"))
        self.assertIn(resp.status_code, (302, 303))

    def test_only_reviews_assigned_to_active_assessor_in_same_org_are_listed(self):
        """
        Spec: User with assessor role should see only reviews that are assigned to an Assessor
        belonging to the same organisation and where that Assessor is active.
        """
        # Create another assessor in same org but inactive, and a review for it
        inactive = Assessor.objects.create(
            organisation=self.assessor_profile.organisation,
            name="Inactive",
            email="i@example.com",
            contact_name="I",
            address="2 Rd",
            assessor_type="independent",
            is_active=False,
        )
        r_inactive = Review.objects.create(assessment=self.submitted_assessment, assessed_by=inactive)

        # Create an assessor and review in a different org
        other_org = Organisation.objects.get(name="Other Org")
        foreign_assessor = Assessor.objects.create(
            organisation=other_org,
            name="Foreign",
            email="f@example.com",
            contact_name="F",
            address="3 Rd",
            assessor_type="independent",
        )
        Review.objects.create(assessment=self.other_review.assessment, assessed_by=foreign_assessor)

        resp = self.client.get(reverse("review-list"))
        self.assertEqual(resp.status_code, 200)
        reviews = list(resp.context["reviews"])
        # Should include review assigned to active assessor (self.visible_review)
        self.assertIn(self.visible_review, reviews)
        # Should exclude review assigned to inactive assessor
        self.assertNotIn(r_inactive, reviews)
        # Should exclude reviews assigned to assessors in other organisations
        self.assertTrue(all(rv.assessment.system.organisation == self.assessor_profile.organisation for rv in reviews))


class TestAssessorsView(BaseViewTest):
    """
    Tests for AssessorsView (listing assessors for current organisation).
    - Access allowed only to roles: cyber_advisor, organisation_lead
    - Queryset contains only active assessors of current organisation
    """

    def _login_with_role(self, role_key: str):
        client = Client()

        user = self.org_map[self.organisation_name]["users"][role_key]  # type: ignore
        client.force_login(user)
        profile = UserProfile.objects.get(user=user, role=role_key)
        session = client.session
        session["current_profile_id"] = profile.id
        session.save()
        return client, profile

    def test_access_control_disallowed_role_redirects(self):
        client, _ = self._login_with_role("organisation_user")
        resp = client.get(reverse("assessor-list"))
        # UserRoleCheckMixin.handle_no_permission returns redirect to login by default
        self.assertIn(resp.status_code, (403,))

    def test_access_control_allowed_roles(self):
        for role_key in ("cyber_advisor", "organisation_lead"):
            client, _ = self._login_with_role(role_key)
            resp = client.get(reverse("assessor-list"))
            self.assertEqual(resp.status_code, 200)

    def test_queryset_only_active_assessors_in_current_org(self):
        client, profile = self._login_with_role("cyber_advisor")
        # Create assessors in this org
        a1 = Assessor.objects.create(
            organisation=profile.organisation,
            name="Active 1",
            email="a1@example.com",
            contact_name="A1",
            address="1 St",
            assessor_type="independent",
            is_active=True,
        )
        a2 = Assessor.objects.create(
            organisation=profile.organisation,
            name="Inactive 2",
            email="a2@example.com",
            contact_name="A2",
            address="2 St",
            assessor_type="independent",
            is_active=False,
        )
        # And an active assessor in a different org
        other_org, _ = Organisation.objects.get_or_create(name="Another Org")
        Assessor.objects.create(
            organisation=other_org,
            name="Other Org Assessor",
            email="other@example.com",
            contact_name="OO",
            address="3 St",
            assessor_type="independent",
            is_active=True,
        )

        resp = client.get(reverse("assessor-list"))
        self.assertEqual(resp.status_code, 200)
        qs = list(resp.context["object_list"])  # ListView default context
        self.assertIn(a1, qs)
        self.assertNotIn(a2, qs)
        self.assertEqual(len(qs), 1)


class TestEditAssessorView(BaseViewTest):
    """
    Tests for EditAssessorView.

    Focus on:
    - The assessments field queryset contains only submitted assessments in the current organisation
    - Posting members and assessments associates UserProfiles and creates Review records
    - Success redirect to assessor list
    """

    def setUp(self):
        self.client = Client()
        # Use cyber_advisor as an allowed role
        self.cyber_user = self.org_map[self.organisation_name]["users"]["cyber_advisor"]
        self.client.force_login(self.cyber_user)
        self.cyber_profile = UserProfile.objects.get(user=self.cyber_user, role="cyber_advisor")
        session = self.client.session
        session["current_profile_id"] = self.cyber_profile.id
        session.save()

        # Existing assessor to edit (belongs to same org)
        self.assessor = Assessor.objects.create(
            organisation=self.cyber_profile.organisation,
            name="Edit Me",
            email="edit@example.com",
            contact_name="Ed It",
            address="10 High St",
            assessor_type="independent",
        )

        # Systems in current and other org
        self.system_current = self.test_system  # from BaseViewTest, belongs to the same org
        other_org, _ = Organisation.objects.get_or_create(name="Other Org For Edit")
        self.system_other, _ = System.objects.get_or_create(name="Other Sys", organisation=other_org)

        # Assessments: only submitted in current org should appear in form queryset
        self.assessment_submitted_current = Assessment.objects.create(
            system=self.system_current,
            status="submitted",
            assessment_period="2025",
        )
        self.assessment_draft_current = Assessment.objects.create(
            system=self.system_current,
            status="draft",
            assessment_period="2025",
        )
        self.assessment_submitted_other = Assessment.objects.create(
            system=self.system_other,
            status="submitted",
            assessment_period="2025",
        )

        # Members: create profiles with roles assessor and reviewer in same org
        from django.contrib.auth.models import User

        self.member_assessor_user, _ = User.objects.get_or_create(
            username=self.email_from_username_and_org("member_assessor", self.organisation_name)
        )
        self.member_assessor_profile, _ = UserProfile.objects.get_or_create(
            user=self.member_assessor_user, organisation=self.cyber_profile.organisation, role="assessor"
        )
        self.member_reviewer_user, _ = User.objects.get_or_create(
            username=self.email_from_username_and_org("member_reviewer", self.organisation_name)
        )
        self.member_reviewer_profile, _ = UserProfile.objects.get_or_create(
            user=self.member_reviewer_user, organisation=self.cyber_profile.organisation, role="reviewer"
        )

    def test_form_queryset_filters_assessments_to_submitted_in_org(self):
        resp = self.client.get(reverse("edit-assessor", kwargs={"pk": self.assessor.id}))
        self.assertEqual(resp.status_code, 200)
        form = resp.context["form"]
        qs = list(form.fields["assessments"].queryset)
        self.assertIn(self.assessment_submitted_current, qs)
        self.assertNotIn(self.assessment_draft_current, qs)
        self.assertNotIn(self.assessment_submitted_other, qs)

    def test_post_sets_members_and_creates_reviews_and_redirects(self):
        resp = self.client.post(
            reverse("edit-assessor", kwargs={"pk": self.assessor.id}),
            data={
                "name": "Updated Name",
                "email": "new@example.com",
                "contact_name": "New Contact",
                "phone_number": "01234",
                "address": "22 Baker St",
                "assessor_type": "peer",
                # assign both valid members
                "members": [self.member_assessor_profile.id, self.member_reviewer_profile.id],
                # assign the single allowed assessment
                "assessments": [self.assessment_submitted_current.id],
            },
            follow=False,
        )
        # Expect redirect to assessor list
        self.assertIn(resp.status_code, (302, 303))
        self.assertEqual(resp.url, reverse("assessor-list"))

        # Members should link back to the assessor through member_of
        self.member_assessor_profile.refresh_from_db()
        self.member_reviewer_profile.refresh_from_db()
        self.assertIn(self.assessor, self.member_assessor_profile.member_of.all())
        self.assertIn(self.assessor, self.member_reviewer_profile.member_of.all())

        # A Review should be created/associated for the selected assessment
        review = Review.objects.get(assessment=self.assessment_submitted_current, assessed_by=self.assessor)
        # And the assessor's reviews set should contain only the assigned review
        self.assertEqual(list(self.assessor.reviews.all()), [review])

    def test_members_must_be_assessor_or_peer_in_current_org(self):
        """
        Spec: Only user profiles with role 'assessor' or 'reviewer/peer' in the same org can be added as members.
        Include a profile from another role and from another organisation to assert they are rejected.
        """
        # Create a profile with a non-allowed role in same org and another organisation profile
        from django.contrib.auth.models import User

        other_role_user, _ = User.objects.get_or_create(
            username=self.email_from_username_and_org("org_user_member", self.organisation_name)
        )
        other_role_profile, _ = UserProfile.objects.get_or_create(
            user=other_role_user, organisation=self.cyber_profile.organisation, role="organisation_user"
        )

        foreign_org, _ = Organisation.objects.get_or_create(name="Foreign Org For Members")
        foreign_user, _ = User.objects.get_or_create(username="foreign@example.com")
        foreign_profile, _ = UserProfile.objects.get_or_create(
            user=foreign_user, organisation=foreign_org, role="assessor"
        )

        resp = self.client.post(
            reverse("edit-assessor", kwargs={"pk": self.assessor.id}),
            data={
                "name": "Updated Name",
                "email": "new@example.com",
                "contact_name": "New Contact",
                "address": "22 Baker St",
                "assessor_type": "peer",
                "members": [
                    self.member_assessor_profile.id,
                    self.member_reviewer_profile.id,
                    other_role_profile.id,  # should be rejected
                    foreign_profile.id,  # should be rejected (different org)
                ],
                "assessments": [self.assessment_submitted_current.id],
            },
        )
        self.assertIn(resp.status_code, (302, 303))
        # After save, only the allowed members should be linked
        allowed_member_ids = set(self.assessor.members.values_list("id", flat=True))
        self.assertIn(self.member_assessor_profile.id, allowed_member_ids)
        self.assertIn(self.member_reviewer_profile.id, allowed_member_ids)
        self.assertNotIn(other_role_profile.id, allowed_member_ids)
        self.assertNotIn(foreign_profile.id, allowed_member_ids)


class TestRemoveAssessorView(BaseViewTest):
    """
    Tests for RemoveAssessorView (soft delete by marking inactive).
    - Access allowed only to roles: cyber_advisor, organisation_lead
    - On confirmation (yes), assessor is marked inactive; on no, remains active
    - Assessor must belong to current organisation
    """

    def setUp(self):
        self.client = Client()
        # Use organisation_lead for variety
        self.lead_user = self.org_map[self.organisation_name]["users"]["organisation_lead"]
        self.client.force_login(self.lead_user)
        self.lead_profile = UserProfile.objects.get(user=self.lead_user, role="organisation_lead")
        session = self.client.session
        session["current_profile_id"] = self.lead_profile.id
        session.save()

        self.assessor = Assessor.objects.create(
            organisation=self.lead_profile.organisation,
            name="To Remove",
            email="remove@example.com",
            contact_name="Rem Ove",
            address="4 Road",
            assessor_type="independent",
            is_active=True,
        )

    def test_remove_yes_marks_inactive(self):
        resp = self.client.post(
            reverse("remove-assessor", kwargs={"pk": self.assessor.id}),
            data={"yes_no": "yes"},
            follow=False,
        )
        self.assertIn(resp.status_code, (302, 303))
        self.assertEqual(resp.url, reverse("assessor-list"))
        self.assessor.refresh_from_db()
        self.assertIs(self.assessor.is_active, False)

    def test_remove_no_leaves_active(self):
        resp = self.client.post(
            reverse("remove-assessor", kwargs={"pk": self.assessor.id}),
            data={"yes_no": "no"},
            follow=False,
        )
        self.assertIn(resp.status_code, (302, 303))
        self.assessor.refresh_from_db()
        self.assertIs(self.assessor.is_active, True)

    def test_cannot_remove_assessor_from_other_org(self):
        # Create an assessor for a different org
        other_org, _ = Organisation.objects.get_or_create(name="Remove Other Org")
        other_assessor = Assessor.objects.create(
            organisation=other_org,
            name="Other",
            email="other@example.com",
            contact_name="Other",
            address="5 Ave",
            assessor_type="independent",
        )
        # Attempt to GET confirmation page for the other_org assessor should 404 (object filter returns None)
        resp = self.client.get(reverse("remove-assessor", kwargs={"pk": other_assessor.id}))
        self.assertEqual(resp.status_code, 404)

    def test_remove_view_disallowed_role_redirects(self):
        # Login with a role that is not allowed, e.g., organisation_user
        client = Client()
        user = self.org_map[self.organisation_name]["users"]["organisation_user"]
        client.force_login(user)
        profile = UserProfile.objects.get(user=user, role="organisation_user")
        session = client.session
        session["current_profile_id"] = profile.id
        session.save()
        resp = client.get(reverse("remove-assessor", kwargs={"pk": self.assessor.id}))
        self.assertIn(resp.status_code, (403,))
