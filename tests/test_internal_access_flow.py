from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import include, path, reverse
from requests import ConnectionError

from webcaf.auth import EMAIL_DOMAIN_REJECTED_SESSION_KEY
from webcaf.webcaf.views.internal_access import InternalAccessCallbackView

urlpatterns = [
    path("oidc/callback/", InternalAccessCallbackView.as_view()),
    path("", include("webcaf.urls")),
]


@override_settings(
    ROOT_URLCONF=__name__,
    SSO_MODE="internal-access",
    LOGIN_URL="oidc_authentication_init",
    ENABLED_2FA=False,
    LOGIN_REDIRECT_URL="/my-account/",
    LOGIN_REDIRECT_URL_FAILURE="/authentication-error/",
    OIDC_RP_CLIENT_ID="test-client",
    OIDC_OP_AUTHORIZATION_ENDPOINT="https://example.test/authorize",
)
class InternalAccessFlowTest(TestCase):
    def callback_state(self):
        session = self.client.session
        session["oidc_states"] = {"test-state": {"nonce": "test-nonce"}}
        session.save()

    def test_protected_page_starts_internal_access_flow(self):
        response = self.client.get("/my-account/")
        self.assertRedirects(response, reverse("oidc_authentication_init"), fetch_redirect_response=False)
        response = self.client.get(response.url)
        self.assertTrue(response.url.startswith("https://example.test/authorize?"))

    def test_denial_clears_existing_session_and_logs_no_provider_details(self):
        user = get_user_model().objects.create_user(username="existing")
        self.client.force_login(user)
        with self.assertLogs("InternalAccessCallbackView", "WARNING") as logs:
            response = self.client.get("/oidc/callback/", {"error": "sensitive-provider-error"})
        self.assertRedirects(response, "/authentication-error/", fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertNotIn("sensitive-provider-error", " ".join(logs.output))

    @patch("mozilla_django_oidc.views.auth.authenticate", side_effect=ConnectionError("secret response"))
    def test_provider_connection_failure_shows_safe_error(self, authenticate):
        self.callback_state()
        with self.assertLogs("InternalAccessCallbackView", "WARNING") as logs:
            response = self.client.get("/oidc/callback/", {"code": "test-code", "state": "test-state"})
        self.assertRedirects(response, "/authentication-error/", fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertNotIn("secret response", " ".join(logs.output))

    @patch("mozilla_django_oidc.views.auth.authenticate")
    def test_success_creates_session_and_logs_user_id(self, authenticate):
        user = get_user_model().objects.create_user(username="existing", email="user@example.test")
        user.backend = "webcaf.auth.OIDCBackend"
        authenticate.return_value = user
        self.callback_state()
        with self.assertLogs("InternalAccessCallbackView", "INFO") as logs:
            response = self.client.get("/oidc/callback/", {"code": "test-code", "state": "test-state"})
        self.assertRedirects(response, "/my-account/", fetch_redirect_response=False)
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))
        self.assertIn(str(user.pk), " ".join(logs.output))
        self.assertNotIn(user.email, " ".join(logs.output))

    def test_invalid_state_remains_bad_request(self):
        self.callback_state()
        response = self.client.get("/oidc/callback/", {"code": "test-code", "state": "invalid"})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_incomplete_callback_shows_safe_error(self):
        response = self.client.get("/oidc/callback/")
        self.assertRedirects(response, "/authentication-error/", fetch_redirect_response=False)

    @patch("mozilla_django_oidc.views.auth.authenticate")
    def test_rejected_domain_message_survives_failed_session_cleanup(self, authenticate):
        def reject_domain(**kwargs):
            kwargs["request"].session[EMAIL_DOMAIN_REJECTED_SESSION_KEY] = True
            kwargs["request"].session["oidc_access_token"] = "discard-this-token"
            return None

        authenticate.side_effect = reject_domain
        self.callback_state()
        response = self.client.get("/oidc/callback/", {"code": "test-code", "state": "test-state"})
        self.assertNotIn("oidc_access_token", self.client.session)
        response = self.client.get(response.url)
        self.assertContains(response, "Your email domain is not approved")
