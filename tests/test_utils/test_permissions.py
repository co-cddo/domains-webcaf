from django.test import TestCase

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import Organisation, UserProfile
from webcaf.webcaf.utils.permission import PermissionUtil


class TestCurrentUserCanCreateReview(BaseViewTest):
    """
    Tests for PermissionUtil.current_user_can_create_review() method.

    Tests that the correct roles are allowed to create reviews.
    """

    @classmethod
    def setUpTestData(cls):
        BaseViewTest.setUpTestData()
        cls.org = Organisation.objects.get(name=cls.organisation_name)

    def test_cyber_advisor_can_create_review(self):
        """Test that cyber_advisor role can create reviews."""
        user = self.org_map[self.organisation_name]["users"]["cyber_advisor"]
        profile = UserProfile.objects.get(user=user, role="cyber_advisor")

        self.assertTrue(PermissionUtil.current_user_can_create_review(profile))

    def test_organisation_lead_can_create_review(self):
        """Test that organisation_lead role can create reviews."""
        user = self.org_map[self.organisation_name]["users"]["organisation_lead"]
        profile = UserProfile.objects.get(user=user, role="organisation_lead")

        self.assertTrue(PermissionUtil.current_user_can_create_review(profile))

    def test_assessor_can_create_review(self):
        """Test that assessor role can create reviews."""
        # Create assessor profile
        from django.contrib.auth.models import User

        assessor_user, _ = User.objects.get_or_create(
            username=self.email_from_username_and_org("assessor_perm_test", self.organisation_name)
        )
        profile, _ = UserProfile.objects.get_or_create(user=assessor_user, organisation=self.org, role="assessor")

        self.assertTrue(PermissionUtil.current_user_can_create_review(profile))

    def test_reviewer_can_create_review(self):
        """Test that reviewer role can create reviews."""
        # Create reviewer profile
        from django.contrib.auth.models import User

        reviewer_user, _ = User.objects.get_or_create(
            username=self.email_from_username_and_org("reviewer_perm_test", self.organisation_name)
        )
        profile, _ = UserProfile.objects.get_or_create(user=reviewer_user, organisation=self.org, role="reviewer")

        self.assertTrue(PermissionUtil.current_user_can_create_review(profile))

    def test_organisation_user_cannot_create_review(self):
        """Test that organisation_user role cannot create reviews."""
        user = self.org_map[self.organisation_name]["users"]["organisation_user"]
        profile = UserProfile.objects.get(user=user, role="organisation_user")

        self.assertFalse(PermissionUtil.current_user_can_create_review(profile))

    def test_none_user_profile_cannot_create_review(self):
        """Test that None user_profile returns False."""
        self.assertFalse(PermissionUtil.current_user_can_create_review(None))


class TestOtherPermissions(TestCase):
    """
    Tests for other permission methods in PermissionUtil.

    These tests verify that other permission methods work correctly with None values.
    """

    def test_current_user_can_create_system_with_none(self):
        """Test that current_user_can_create_system returns False for None."""
        self.assertFalse(PermissionUtil.current_user_can_create_system(None))

    def test_current_user_can_view_systems_with_none(self):
        """Test that current_user_can_view_systems returns False for None."""
        self.assertFalse(PermissionUtil.current_user_can_view_systems(None))

    def test_current_user_can_create_user_with_none(self):
        """Test that current_user_can_create_user returns False for None."""
        self.assertFalse(PermissionUtil.current_user_can_create_user(None))

    def test_current_user_can_delete_user_with_none(self):
        """Test that current_user_can_delete_user returns False for None."""
        self.assertFalse(PermissionUtil.current_user_can_delete_user(None))

    def test_current_user_can_view_users_with_none(self):
        """Test that current_user_can_view_users returns False for None."""
        self.assertFalse(PermissionUtil.current_user_can_view_users(None))

    def test_current_user_can_start_assessment_with_none(self):
        """Test that current_user_can_start_assessment returns False for None."""
        self.assertFalse(PermissionUtil.current_user_can_start_assessment(None))

    def test_current_user_can_view_assessments_with_none(self):
        """Test that current_user_can_view_assessments returns False for None."""
        self.assertFalse(PermissionUtil.current_user_can_view_assessments(None))

    def test_current_user_can_submit_assessment_with_none(self):
        """Test that current_user_can_submit_assessment returns False for None."""
        self.assertFalse(PermissionUtil.current_user_can_submit_assessment(None))

    def test_current_user_can_view_submitted_assessment_with_none(self):
        """Test that current_user_can_view_submitted_assessment returns False for None."""
        self.assertFalse(PermissionUtil.current_user_can_view_submitted_assessment(None))
