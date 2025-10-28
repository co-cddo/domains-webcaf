"""
We override the settings.ENABLED_2FA to be True in these test classes

This ensures we mimic a production like enviroment where both SSO and
2FA authentications are required.
"""

import logging

from django.test import Client, override_settings
from django.urls import get_resolver, reverse
from django_otp import DEVICE_ID_SESSION_KEY

from tests.test_views.base_view_test import BaseViewTest
from webcaf.auth import LoginRequiredMiddleware
from webcaf.webcaf.models import GovNotifyEmailDevice, UserProfile


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
        self.submit_a_review_url = reverse("objective-confirmation")
        session = self.client.session
        session["current_profile_id"] = self.user_profile.id

        # This mocks conditions required for a 2fa verified user
        device = GovNotifyEmailDevice.objects.create(user=self.test_user, email=self.test_user.email)
        session[DEVICE_ID_SESSION_KEY] = device.persistent_id

        session.save()
        self.req_logger = logging.getLogger("django.request")

        # store its original level to restore it later
        self.original_level = self.req_logger.level
        # set this to not pollute test logs with expected warning for these tests
        self.req_logger.setLevel(logging.ERROR)
        self.client.force_login(self.test_user)

        login = LoginRequiredMiddleware(None)

        self.non_auth_urls = login.exempt_url_prefixes + login.exempt_exact_urls
        # list of urls that should require authentication from both sso and 2fa to view
        self.url_names_requiring_auth = [
            url_pattern.pattern.name
            for url_pattern in get_resolver().url_patterns
            if not any(
                True if url_pattern.pattern._route in non_auth_url else False for non_auth_url in self.non_auth_urls
            )
            and not url_pattern.pattern._route.startswith("public")
            and "<int:" not in url_pattern.pattern._route
        ]

    def tearDown(self):
        # restore the original logging level after these tests run
        self.req_logger.setLevel(self.original_level)


@override_settings(ENABLED_2FA=True)
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

    def test_non_verified_org_user_cannot_access_private_pages(self):
        """
        Test an org users redirected to verify token if not a verified
        user (i.e. has not already supplied a valid OTP token)
        """
        # make the user not verified
        session = self.client.session
        device_id = session.pop(DEVICE_ID_SESSION_KEY)
        session.save()
        for url_name in self.url_names_requiring_auth:
            if url_name and not url_name == "verify-2fa-token":
                response = self.client.get(reverse(url_name))
                self.assertRedirects(response, reverse("verify-2fa-token"))

        # re-add verified user
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = device_id
        session.save()


@override_settings(ENABLED_2FA=True)
class OrgLeadPermssionsTests(SetupPermissionsData):
    """
    tests that assert the organisational lead cannot access pages they are not
    intended to access
    """

    def setUp(self):
        super().setUp()
        self.user_profile.role = "organisation_lead"
        self.user_profile.save()

    @override_settings(ENABLED_2FA=True)
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

    def test_non_verified_org_lead_cannot_access_private_pages(self):
        """
        Test an org lead is redirected to verify token if not a verified
        user (i.e. has not already supplied a valid OTP token)
        """
        # make the user not verified
        session = self.client.session
        device_id = session.pop(DEVICE_ID_SESSION_KEY)
        session.save()
        for url_name in self.url_names_requiring_auth:
            if url_name and not url_name == "verify-2fa-token":
                response = self.client.get(reverse(url_name))
                self.assertRedirects(response, reverse("verify-2fa-token"))

        # re-add verified user
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = device_id
        session.save()


@override_settings(ENABLED_2FA=True)
class CyberAdvisorPermssionsTests(SetupPermissionsData):
    def setUp(self):
        super().setUp()
        self.user_profile.role = "cyber_advisor"
        self.user_profile.save()

    def test_cyber_advisor_cannot_submit_a_review(self):
        """
        Test that a user with cyber advisor profile gets a 403 forbidden status
        """
        response = self.client.get(self.submit_a_review_url)
        self.assertEqual(response.status_code, 403)

    def test_non_verified_cyber_advisor_cannot_access_private_pages(self):
        """
        Test an cyber advisor is redirected to verify token if not a verified
        user (i.e. has not already supplied a valid OTP token)
        """
        # make the user not verified
        session = self.client.session
        device_id = session.pop(DEVICE_ID_SESSION_KEY)
        session.save()
        for url_name in self.url_names_requiring_auth:
            if url_name and not url_name == "verify-2fa-token":
                response = self.client.get(reverse(url_name))
                self.assertRedirects(response, reverse("verify-2fa-token"))

        # re-add verified user
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = device_id
        session.save()
