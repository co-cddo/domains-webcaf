import time

from django.test import Client, override_settings
from django.urls import reverse

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import UserProfile
from webcaf.webcaf.views.account import AccountView


class SetupSessionTestData(BaseViewTest):
    @classmethod
    def setUpTestData(cls):
        BaseViewTest.setUpTestData()

    def setUp(self):
        self.client = Client()
        self.my_account_url = reverse("my-account")
        self.session_timeout_url = reverse("session-expired")
        self.user_profile = UserProfile.objects.get(user=self.test_user)
        session = self.client.session
        session["current_profile_id"] = self.user_profile.id
        session.save()


class SessionTimeoutTest(SetupSessionTestData):
    def setUp(self):
        super().setUp()

    @override_settings(USER_IDLE_TIMEOUT=0.5)
    def test_session_timeout(self):
        self.client.force_login(self.test_user)

        # session should be active on first call
        response = self.client.get(self.my_account_url)
        self.assertEqual(response.status_code, 200)

        # wait for the session to expire
        time.sleep(1)
        response = self.client.get(self.my_account_url, follow=True)
        self.assertTemplateUsed(response, "session-timeout.html")

        self.assertRedirects(response, self.session_timeout_url)
        self.assertEqual(self.client.session._session, {})

        # the user should now be redirected to the login page
        response = self.client.get(self.my_account_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, AccountView.login_url)
