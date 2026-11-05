"""
Integration tests for OIDCBackend.

Tests user creation and update behaviour against a real database.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import SuspiciousOperation
from django.test import TestCase, override_settings

from webcaf.auth import EMAIL_DOMAIN_REJECTED_SESSION_KEY, OIDCBackend
from webcaf.webcaf.models import AllowedEmailDomain, UserProfile

User = get_user_model()

CLAIMS = {
    "email": "jane.doe@example.com",
    "given_name": "Jane",
    "family_name": "Doe",
}


@override_settings(
    OIDC_RP_CLIENT_ID="test-client",
    OIDC_RP_CLIENT_SECRET="test-secret",  # pragma: allowlist secret
    OIDC_OP_AUTHORIZATION_ENDPOINT="http://dex:5556/auth",
    OIDC_OP_TOKEN_ENDPOINT="http://dex:5556/token",
    OIDC_OP_USER_ENDPOINT="http://dex:5556/userinfo",
    OIDC_OP_JWKS_ENDPOINT="http://dex:5556/keys",
)
class OIDCBackendIntegrationTest(TestCase):
    def setUp(self):
        self.backend = OIDCBackend()
        AllowedEmailDomain.objects.create(domain="example.com")

    def test_create_user_when_staff_with_same_email_exists(self):
        """A new non-staff user is created even when a staff user shares the email."""
        User.objects.create_user(username="admin-user", email=CLAIMS["email"], is_staff=True)

        # filter_users_by_claims excludes staff, so no match → create_user is called
        filtered = self.backend.filter_users_by_claims(CLAIMS)
        self.assertFalse(filtered.exists())

        new_user = self.backend.create_user(CLAIMS)

        self.assertEqual(User.objects.filter(email__iexact=CLAIMS["email"]).count(), 2)
        self.assertFalse(new_user.is_staff)
        self.assertEqual(new_user.first_name, "Jane")
        self.assertEqual(new_user.last_name, "Doe")

    def test_no_new_user_when_non_staff_with_same_email_exists(self):
        """filter_users_by_claims returns the existing non-staff user, preventing duplicate creation."""
        existing = User.objects.create_user(username=CLAIMS["email"], email=CLAIMS["email"], is_staff=False)

        filtered = self.backend.filter_users_by_claims(CLAIMS)

        self.assertEqual(list(filtered), [existing])
        self.assertEqual(User.objects.filter(email__iexact=CLAIMS["email"]).count(), 1)

    def test_update_user_syncs_first_and_last_name(self):
        """update_user overwrites first/last name from claims."""
        user = User.objects.create_user(
            username=CLAIMS["email"],
            email=CLAIMS["email"],
            first_name="Old",
            last_name="Name",
            is_staff=False,
        )

        updated_claims = {**CLAIMS, "given_name": "Janet", "family_name": "Smith"}
        self.backend.update_user(user, updated_claims)

        user.refresh_from_db()
        self.assertEqual(user.first_name, "Janet")
        self.assertEqual(user.last_name, "Smith")

    def test_does_not_create_user_for_unapproved_email_domain(self):
        AllowedEmailDomain.objects.all().delete()
        self.backend.request = type("Request", (), {"session": {}})()

        with self.assertLogs("OIDCBackend", "WARNING") as logs:
            user = self.backend.create_user(CLAIMS)

        self.assertIsNone(user)
        self.assertFalse(User.objects.exists())
        self.assertTrue(self.backend.request.session[EMAIL_DOMAIN_REJECTED_SESSION_KEY])
        self.assertIn("ja***@example.com", logs.output[0])

    @override_settings(SSO_MODE="internal-access")
    def test_internal_access_links_email_with_different_username_and_preserves_profile(self):
        existing = User.objects.create_user(username="legacy-user", email=CLAIMS["email"].upper())
        profile = UserProfile.objects.create(user=existing, role="organisation_user")
        AllowedEmailDomain.objects.all().delete()

        with patch.object(self.backend, "get_userinfo", return_value=CLAIMS):
            user = self.backend.get_or_create_user("access-token", "id-token", {})

        self.assertEqual(user.pk, existing.pk)
        profile.refresh_from_db()
        self.assertEqual(profile.user_id, user.pk)
        self.assertEqual(profile.role, "organisation_user")
        self.assertEqual(User.objects.count(), 1)
        user.refresh_from_db()
        self.assertEqual(user.username, "legacy-user")

    @override_settings(SSO_MODE="internal-access")
    def test_internal_access_rejects_ambiguous_non_staff_email(self):
        User.objects.create_user(username="first", email=CLAIMS["email"])
        User.objects.create_user(username="second", email=CLAIMS["email"].upper())

        with patch.object(self.backend, "get_userinfo", return_value=CLAIMS):
            with self.assertRaisesMessage(SuspiciousOperation, "Multiple users returned"):
                self.backend.get_or_create_user("access-token", "id-token", {})

        self.assertEqual(User.objects.count(), 2)

    @override_settings(SSO_MODE="internal-access")
    def test_internal_access_does_not_match_staff(self):
        User.objects.create_user(username="admin", email=CLAIMS["email"], is_staff=True)

        self.assertFalse(self.backend.filter_users_by_claims(CLAIMS).exists())

    @override_settings(SSO_MODE="external")
    def test_other_oidc_modes_keep_username_and_email_matching(self):
        User.objects.create_user(username="legacy-user", email=CLAIMS["email"])

        self.assertFalse(self.backend.filter_users_by_claims(CLAIMS).exists())
