"""
Tests for LoginRequiredMiddleware.

This module tests the authentication middleware that enforces login requirements
for non-exempt URLs and handles 2FA verification.
"""

from unittest.mock import Mock, patch

from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpRequest, HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse

from webcaf.auth import LoginRequiredMiddleware


class LoginRequiredMiddlewareTest(TestCase):
    """Test suite for LoginRequiredMiddleware."""

    def setUp(self):
        """Set up test fixtures."""
        self.get_response = Mock(return_value=HttpResponse("OK"))
        self.middleware = LoginRequiredMiddleware(self.get_response)
        self.request = HttpRequest()
        self.user = User.objects.create_user(username="testuser", password="testpass")

    def test_middleware_initialization(self):
        """Test that middleware initializes with correct exempt URLs."""
        self.assertIn(reverse("oidc_authentication_init"), self.middleware.exempt_url_prefixes)
        self.assertIn(reverse("oidc_authentication_callback"), self.middleware.exempt_url_prefixes)
        self.assertIn(reverse("oidc_logout"), self.middleware.exempt_url_prefixes)
        self.assertIn("/admin/", self.middleware.exempt_url_prefixes)
        self.assertIn("/assets/", self.middleware.exempt_url_prefixes)
        self.assertIn("/static/", self.middleware.exempt_url_prefixes)
        self.assertIn("/media", self.middleware.exempt_url_prefixes)
        self.assertIn("/public/", self.middleware.exempt_url_prefixes)
        self.assertIn("/session-expired/", self.middleware.exempt_url_prefixes)
        self.assertIn("/logout/", self.middleware.exempt_url_prefixes)
        self.assertIn("/", self.middleware.exempt_exact_urls)

    def test_exempt_url_prefix_allows_access(self):
        """Test that URLs with exempt prefixes allow access without authentication."""
        exempt_paths = [
            "/admin/login/",
            "/assets/css/style.css",
            "/static/js/app.js",
            "/media/image.png",
            "/public/page",
            "/session-expired/",
            "/logout/",
        ]

        for path in exempt_paths:
            self.request.path = path
            self.request.user = AnonymousUser()
            response = self.middleware(self.request)
            self.assertEqual(response.status_code, 200)
            self.get_response.assert_called_with(self.request)

    def test_exempt_exact_url_allows_access(self):
        """Test that exact exempt URLs allow access without authentication."""
        self.request.path = "/"
        self.request.user = AnonymousUser()
        response = self.middleware(self.request)
        self.assertEqual(response.status_code, 200)
        self.get_response.assert_called_with(self.request)

    def test_oidc_urls_allow_access(self):
        """Test that OIDC authentication URLs allow access without authentication."""
        oidc_paths = [
            reverse("oidc_authentication_init"),
            reverse("oidc_authentication_callback"),
            reverse("oidc_logout"),
        ]

        for path in oidc_paths:
            self.request.path = path
            self.request.user = AnonymousUser()
            response = self.middleware(self.request)
            self.assertEqual(response.status_code, 200)
            self.get_response.assert_called_with(self.request)

    def test_unauthenticated_user_redirected_to_oidc(self):
        """Test that unauthenticated users are redirected to OIDC authentication."""
        self.request.path = "/some/protected/path"
        self.request.user = AnonymousUser()
        response = self.middleware(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("oidc_authentication_init"))

    @override_settings(ENABLED_2FA=False)
    def test_authenticated_user_allowed_when_2fa_disabled(self):
        """Test that authenticated users are allowed access when 2FA is disabled."""
        self.request.path = "/some/protected/path"
        self.request.user = self.user
        response = self.middleware(self.request)
        self.assertEqual(response.status_code, 200)
        self.get_response.assert_called_with(self.request)

    @override_settings(ENABLED_2FA=True)
    def test_authenticated_unverified_user_redirected_to_verification(self):
        """Test that unverified users are redirected to 2FA verification page."""
        self.request.path = "/some/protected/path"
        self.request.user = self.user
        self.request.user.is_verified = Mock(return_value=False)

        response = self.middleware(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("verify-2fa-token"))

    @override_settings(ENABLED_2FA=True)
    def test_unverified_user_allowed_access_to_verification_page(self):
        """Test that unverified users can access the verification page."""
        self.request.path = reverse("verify-2fa-token")
        self.request.user = self.user
        self.request.user.is_verified = Mock(return_value=False)

        response = self.middleware(self.request)
        self.assertEqual(response.status_code, 200)
        self.get_response.assert_called_with(self.request)

    def test_multiple_non_exempt_paths_redirect_unauthenticated(self):
        """Test multiple non-exempt paths redirect unauthenticated users."""
        non_exempt_paths = [
            "/dashboard/",
            "/profile/settings",
            "/api/data",
            "/reports/view",
        ]

        for path in non_exempt_paths:
            self.request.path = path
            self.request.user = AnonymousUser()
            response = self.middleware(self.request)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse("oidc_authentication_init"))

    @patch("webcaf.auth.LoginRequiredMiddleware.logger")
    def test_middleware_logs_force_authentication(self, mock_logger):
        """Test that middleware logs when forcing authentication."""
        self.request.path = "/protected/path"
        self.request.user = AnonymousUser()
        self.middleware(self.request)
        mock_logger.debug.assert_called_with("Force authentication for %s", "/protected/path")

    @patch("webcaf.auth.LoginRequiredMiddleware.logger")
    def test_middleware_logs_allowed_access(self, mock_logger):
        """Test that middleware logs when allowing access to exempt URLs."""
        self.request.path = "/static/file.css"
        self.request.user = AnonymousUser()
        self.middleware(self.request)
        mock_logger.debug.assert_called_with("Allowing access to %s, authenticated %s", "/static/file.css", False)

    @override_settings(ENABLED_2FA=False)
    @patch("webcaf.auth.LoginRequiredMiddleware.logger")
    def test_middleware_logs_local_dev_access(self, mock_logger):
        """Test that middleware logs when allowing access in local dev mode."""
        self.request.path = "/some/protected/path"
        self.request.user = self.user
        self.middleware(self.request)
        mock_logger.debug.assert_called_with("Allowing access for local development or testing")

    def test_unauthenticated_post_to_verify_2fa_redirects_session_expired(self):
        """Unauthenticated POST to verify-2fa-token should redirect to session-expired."""
        self.request.path = reverse("verify-2fa-token")
        self.request.method = "POST"
        self.request.user = AnonymousUser()

        response = self.middleware(self.request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("session-expired"))

    def test_unauthenticated_get_to_verify_2fa_redirects_oidc(self):
        """Unauthenticated GET to verify-2fa-token should redirect to OIDC init."""
        self.request.path = reverse("verify-2fa-token")
        self.request.method = "GET"
        self.request.user = AnonymousUser()

        response = self.middleware(self.request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("oidc_authentication_init"))
