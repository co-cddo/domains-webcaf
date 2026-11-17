from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from webcaf.auth import EMAIL_DOMAIN_REJECTED_SESSION_KEY, OneLoginBackend
from webcaf.webcaf.models import AllowedEmailDomain, Organisation, OrganisationEmailDomain, UserProfile

User = get_user_model()

PROFILE = {
    "sub": "urn:fdc:gov.uk:2022:test-subject",
    "email": "jane.doe@example.com",
    "email_verified": True,
}


class OneLoginBackendTest(TestCase):
    def setUp(self):
        self.backend = OneLoginBackend()
        AllowedEmailDomain.objects.create(domain="example.com")

    def authenticate(self, profile=PROFILE):
        with (
            patch("webcaf.auth.get_client", return_value=Mock()) as get_client,
            patch("webcaf.auth.has_valid_token", return_value=True),
            patch("webcaf.auth.get_userinfo", return_value=profile),
        ):
            user = self.backend.authenticate(Mock())

        get_client.assert_called_once()
        return user

    def test_links_existing_user_and_preserves_profile(self):
        existing_user = User.objects.create_user(username=PROFILE["email"], email=PROFILE["email"])
        user_profile = UserProfile.objects.create(user=existing_user, role="organisation_user")

        user = self.authenticate()

        self.assertEqual(user, existing_user)
        self.assertTrue(UserProfile.objects.filter(pk=user_profile.pk, user=existing_user).exists())

    def test_creates_user_without_profile_for_unknown_verified_email(self):
        user = self.authenticate()

        self.assertIsNotNone(user)
        self.assertEqual(user.email, PROFILE["email"])
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.username, PROFILE["email"])
        self.assertFalse(UserProfile.objects.filter(user=user).exists())

    def test_linked_domain_does_not_grant_membership_or_choose_an_organisation(self):
        first_organisation = Organisation.objects.create(name="First organisation")
        second_organisation = Organisation.objects.create(name="Second organisation")
        domain = AllowedEmailDomain.objects.get(domain="example.com")
        OrganisationEmailDomain.objects.create(organisation=first_organisation, domain=domain, is_primary=True)
        OrganisationEmailDomain.objects.create(organisation=second_organisation, domain=domain, is_primary=True)

        user = self.authenticate()

        self.assertIsNotNone(user)
        self.assertFalse(UserProfile.objects.filter(user=user).exists())

    def test_uses_existing_user_on_subsequent_login_with_same_email(self):
        user = self.authenticate()

        authenticated_user = self.authenticate()

        self.assertEqual(authenticated_user, user)
        self.assertEqual(User.objects.count(), 1)

    def test_does_not_link_unverified_email(self):
        user = self.authenticate({**PROFILE, "email_verified": False})

        self.assertIsNone(user)
        self.assertFalse(User.objects.exists())

    def test_does_not_create_user_without_subject(self):
        user = self.authenticate({**PROFILE, "sub": ""})

        self.assertIsNone(user)
        self.assertFalse(User.objects.exists())

    def test_does_not_link_ambiguous_email(self):
        User.objects.create_user(username="first", email=PROFILE["email"])
        User.objects.create_user(username="second", email=PROFILE["email"].upper())

        user = self.authenticate()

        self.assertIsNone(user)

    def test_does_not_link_to_staff_user(self):
        staff_user = User.objects.create_user(username="admin", email=PROFILE["email"], is_staff=True)

        user = self.authenticate()

        self.assertNotEqual(user, staff_user)
        self.assertFalse(user.is_staff)
        self.assertEqual(User.objects.filter(email__iexact=PROFILE["email"]).count(), 2)

    def test_rejects_inactive_mapped_user(self):
        User.objects.create_user(username="inactive", email=PROFILE["email"], is_active=False)

        authenticated_user = self.authenticate()

        self.assertIsNone(authenticated_user)

    def test_does_not_create_user_for_unapproved_email_domain(self):
        AllowedEmailDomain.objects.all().delete()
        request = Mock(session={})

        with self.assertLogs("OneLoginBackend", "WARNING") as logs:
            user = self.backend.get_or_create_user(PROFILE, request)

        self.assertIsNone(user)
        self.assertFalse(User.objects.exists())
        self.assertTrue(request.session[EMAIL_DOMAIN_REJECTED_SESSION_KEY])
        self.assertIn("ja***@example.com", logs.output[0])

    def test_existing_user_can_sign_in_after_domain_is_removed(self):
        existing_user = User.objects.create_user(username=PROFILE["email"], email=PROFILE["email"])
        AllowedEmailDomain.objects.all().delete()

        self.assertEqual(self.authenticate(), existing_user)
