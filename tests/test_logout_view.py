from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


class LogoutViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user", email="user@example.com")
        self.client.force_login(self.user)

    @override_settings(SSO_MODE="one-login")
    @patch("webcaf.webcaf.views.general.get_one_login_logout_url")
    def test_one_login_logout_uses_id_token_before_clearing_session(self, get_logout_url):
        session = self.client.session
        session["_one_login_token"] = {"id_token": "one-login-id-token"}
        session.save()

        def build_logout_url(request, post_logout_redirect_uri):
            self.assertEqual(request.session["_one_login_token"]["id_token"], "one-login-id-token")
            self.assertEqual(post_logout_redirect_uri, "http://testserver/")
            return "https://example.com/logout?token=one-login-id-token"

        get_logout_url.side_effect = build_logout_url

        response = self.client.post(reverse("logout"))

        self.assertRedirects(
            response,
            "https://example.com/logout?token=one-login-id-token",
            fetch_redirect_response=False,
        )
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(SSO_MODE="one-login")
    @patch("webcaf.webcaf.views.general.get_one_login_logout_url")
    def test_one_login_logout_uses_forwarded_https_for_redirect_uri(self, get_logout_url):
        session = self.client.session
        session["_one_login_token"] = {"id_token": "one-login-id-token"}
        session.save()
        get_logout_url.return_value = "https://example.com/logout"

        response = self.client.post(
            reverse("logout"),
            HTTP_HOST="webcaf.example.gov.uk",
            HTTP_X_FORWARDED_PROTO="https",
        )

        self.assertEqual(get_logout_url.call_args.args[1], "https://webcaf.example.gov.uk/")
        self.assertRedirects(response, "https://example.com/logout", fetch_redirect_response=False)

    @override_settings(
        SSO_MODE="internal-access",
        OIDC_OP_LOGOUT_ENDPOINT="https://example.test/sign-out",
        OIDC_RP_CLIENT_ID="internal-access-client",
        LOGOUT_REDIRECT_URL="https://webcaf.example.test/",
    )
    def test_internal_access_logout_clears_session_and_redirects_to_provider(self):
        session = self.client.session
        session["oidc_id_token"] = "test-id-token"
        session.save()

        response = self.client.post(reverse("logout"))

        self.assertEqual(urlparse(response.url).path, "/sign-out")
        self.assertEqual(
            parse_qs(urlparse(response.url).query),
            {"to_client": ["internal-access-client"]},
        )
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertNotIn("oidc_id_token", self.client.session)

    @override_settings(
        SSO_MODE="internal-access",
        OIDC_OP_LOGOUT_ENDPOINT="https://example.test/sign-out",
        OIDC_RP_CLIENT_ID="client/with spaces",
    )
    def test_internal_access_logout_without_id_token_still_signs_out_at_provider(self):
        response = self.client.post(reverse("logout"))

        parsed = urlparse(response.url)
        self.assertEqual((parsed.scheme, parsed.netloc, parsed.path), ("https", "example.test", "/sign-out"))
        self.assertEqual(parse_qs(parsed.query), {"to_client": ["client/with spaces"]})
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(
        SSO_MODE="local",
        OIDC_OP_LOGOUT_ENDPOINT="http://localhost:5556/auth/logout",
        OIDC_RP_CLIENT_ID="my-django-app",
        LOGOUT_REDIRECT_URL="http://localhost:8010/",
    )
    def test_unauthenticated_oidc_logout_parameters_are_encoded(self):
        self.client.logout()
        session = self.client.session
        session["oidc_id_token"] = "token/value+with spaces"
        session.save()

        response = self.client.post(reverse("logout"))

        parsed_url = urlparse(response.url)
        self.assertEqual(
            (parsed_url.scheme, parsed_url.netloc, parsed_url.path), ("http", "localhost:5556", "/auth/logout")
        )
        self.assertEqual(
            parse_qs(parsed_url.query),
            {
                "id_token_hint": ["token/value+with spaces"],
                "client_id": ["my-django-app"],
                "redirect_uri": ["http://localhost:8010/"],
            },
        )
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(SSO_MODE="dex", OIDC_OP_LOGOUT_ENDPOINT="")
    def test_oidc_logout_without_provider_endpoint_clears_local_session(self):
        session = self.client.session
        session["oidc_id_token"] = "dex-id-token"
        session.save()

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("index"))
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(SSO_MODE="one-login")
    @patch("webcaf.webcaf.views.general.get_one_login_logout_url", side_effect=KeyError("id_token"))
    def test_provider_logout_failure_still_clears_local_session(self, get_logout_url):
        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("index"))
        self.assertNotIn("_auth_user_id", self.client.session)
        get_logout_url.assert_called_once()

    def test_logout_requires_post(self):
        response = self.client.get(reverse("logout"))

        self.assertEqual(response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_content_security_policy_allows_default_provider(self):
        response = self.client.get(reverse("index"))
        provider_config = urlparse(settings.GOV_UK_ONE_LOGIN_OPENID_CONFIG_URL)
        provider_origin = f"{provider_config.scheme}://{provider_config.netloc}"

        self.assertIn(f"form-action 'self' {provider_origin}", response["Content-Security-Policy"])
