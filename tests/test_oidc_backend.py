"""
Integration tests for OIDCBackend.

Tests user creation and update behaviour against a real database.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from webcaf.auth import OIDCBackend

User = get_user_model()

CLAIMS = {
    "email": "jane.doe@example.com",
    "given_name": "Jane",
    "family_name": "Doe",
}


class OIDCBackendIntegrationTest(TestCase):
    def setUp(self):
        self.backend = OIDCBackend()

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
