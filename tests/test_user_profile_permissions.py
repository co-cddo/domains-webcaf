# your_app/tests.py
import logging

from django.test import Client
from django.urls import reverse

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import UserProfile


class SetupPermissionsData(BaseViewTest):
    @classmethod
    def setUpTestData(cls):
        BaseViewTest.setUpTestData()

    def setUp(self):
        self.client = Client()
        self.view_profiles_url = reverse("view-profiles")
        self.view_systems_url = reverse("view-systems")

        self.user_profile = UserProfile.objects.get(user=self.test_user)
        self.edit_user_url = reverse("edit-profile", kwargs={"user_profile_id": self.user_profile.id})
        self.create_new_profile_url = reverse("create-new-profile")
        self.create_new_system_url = reverse("create-new-system")
        self.create_or_skip_new_system_url = reverse("create-or-skip-new-system")
        self.create_or_skip_new_profile_url = reverse("create-or-skip-new-profile")
        self.create_a_draft_assessment_utl = reverse("create-draft-assessment")
        session = self.client.session
        session["current_profile_id"] = self.user_profile.id
        session.save()
        self.req_logger = logging.getLogger("django.request")

        # store its original level to restore it later
        self.original_level = self.req_logger.level
        # set this to not pollute test logs with expected warning for these tests
        self.req_logger.setLevel(logging.ERROR)
        self.client.force_login(self.test_user)

    def tearDown(self):
        # restore the original logging level after these tests run
        self.req_logger.setLevel(self.original_level)


class OrgUserProfilePermissionTest(SetupPermissionsData):
    """
    tests that assert the organisational user cannot access pages they are not
    intended to access
    """

    def setUp(self):
        super().setUp()

    def test_org_user_cannot_access_manage_users(self):
        """
        Test that a user with organisation user profile gets a 403 forbidden status
        """
        response = self.client.get(self.view_profiles_url)
        self.assertEqual(response.status_code, 403)

    def test_org_user_cannot_access_edit_user(self):
        """
        Test that a user with organisation user profile gets a 403 forbidden status
        """
        response = self.client.get(self.edit_user_url)
        self.assertEqual(response.status_code, 403)

    def test_org_user_cannot_access_view_systems(self):
        """
        Test that a user with organisation user profile gets a 403 forbidden status
        """
        response = self.client.get(self.view_systems_url)
        self.assertEqual(response.status_code, 403)

    def test_org_user_cannot_access_create_system(self):
        """
        Test that a user with organisation user profile gets a 403 forbidden status
        """
        response = self.client.get(self.create_new_system_url)
        self.assertEqual(response.status_code, 403)

    def test_org_user_cannot_access_create_profile(self):
        """
        Test that a user with organisation user profile gets a 403 forbidden status
        """
        response = self.client.get(self.create_new_profile_url)
        self.assertEqual(response.status_code, 403)

    def test_org_user_cannot_access_create_or_skip_system(self):
        """
        Test that a user with organisation user profile gets a 403 forbidden status
        """
        response = self.client.get(self.create_or_skip_new_system_url)
        self.assertEqual(response.status_code, 403)


class OrgLeadPermssionsTests(SetupPermissionsData):
    """
    tests that assert the organisational lead cannot access pages they are not
    intended to access
    """

    def setUp(self):
        super().setUp()
        self.user_profile.role = "organisation_lead"
        self.user_profile.save()

    def test_org_lead_cannot_access_create_or_skip_system(self):
        """
        Test that a user with organisation lead profile gets a 403 forbidden status
        """

        response = self.client.get(self.create_or_skip_new_system_url)
        self.assertEqual(response.status_code, 403)

    def test_org_lead_cannot_access_create_system(self):
        """
        Test that a user with organisation lead profile gets a 403 forbidden status
        """
        response = self.client.get(self.create_new_system_url)
        self.assertEqual(response.status_code, 403)

    def test_org_lead_cannot_access_view_systems(self):
        """
        Test that a user with organisation lead profile gets a 403 forbidden status
        """
        response = self.client.get(self.view_systems_url)
        self.assertEqual(response.status_code, 403)


class CyberAdvisorPermssionsTests(SetupPermissionsData):
    def setUp(self):
        super().setUp()
        self.user_profile.role = "cyber_advisor"
        self.user_profile.save()

    def test_cyber_advisor_cannot_access_create_a_draft_assessment(self):
        """
        Test that a user with cyber advisor profile gets a 403 forbidden status
        """
        # TODO - need to confirm whether the cyber advisor has any restrcitions
        pass
