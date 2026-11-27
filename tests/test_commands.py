from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.test import TestCase

from webcaf.webcaf.models import Organisation, System, UserProfile


class TestAddLocalUsers(TestCase):
    def setUp(self):
        Organisation.objects.create(name="TestOrg")

    def tearDown(self):
        User.objects.all().delete()
        UserProfile.objects.all().delete()
        Organisation.objects.all().delete()
        System.objects.all().delete()

    def test_command_creates_an_organisation_when_none_exist(self):
        Organisation.objects.all().delete()

        call_command("add_local_seed_data")

        organisation = Organisation.objects.get()
        self.assertEqual(organisation.name, "An Organisation")
        self.assertEqual(organisation.organisation_type, "council")
        self.assertEqual(organisation.gss_code, "E06000001")
        self.assertEqual(organisation.systems.count(), 2)

    def test_command_uses_an_existing_organisation(self):
        call_command("add_local_seed_data")

        self.assertEqual(list(Organisation.objects.values_list("name", flat=True)), ["TestOrg"])

    def test_command_creates_admin_user_when_none_exist(self):
        call_command("add_local_seed_data")
        superuser = User.objects.get(username="admin")
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_staff)

    def test_command_does_not_give_admin_user_a_profile(self):
        call_command("add_local_seed_data")
        self.assertFalse(UserProfile.objects.filter(user__username="admin").exists())

    def test_command_does_not_create_admin_user_if_it_exists(self):
        User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",  # pragma: allowlist secret
        )
        call_command("add_local_seed_data")
        self.assertEqual(User.objects.count(), 1)

    def test_command_creates_userprofiles_for_dex_users(self):
        user_1 = User.objects.create_user(
            username="admin@example.gov.uk",
            email="admin@example.gov.uk",
            password="password",  # pragma: allowlist secret
        )
        user_2 = User.objects.create_user(
            username="alice@example.gov.uk",
            email="alice@example.gov.uk",
            password="password",  # pragma: allowlist secret
        )
        call_command("add_local_seed_data")
        self.assertTrue(UserProfile.objects.filter(user=user_1).exists())
        self.assertTrue(UserProfile.objects.filter(user=user_2).exists())

    def test_command_does_not_replace_existing_dex_userprofiles(self):
        user_1 = User.objects.create_user(
            username="admin@example.gov.uk",
            email="admin@example.gov.uk",
            password="password",  # pragma: allowlist secret
        )
        profile_1 = UserProfile.objects.create(user=user_1)
        user_2 = User.objects.create_user(
            username="alice@example.gov.uk",
            email="alice@example.gov.uk",
            password="password",  # pragma: allowlist secret
        )
        profile_2 = UserProfile.objects.create(user=user_2)
        profile_1_orig_pk = profile_1.pk
        profile_2_orig_pk = profile_2.pk
        call_command("add_local_seed_data")
        profile_1 = UserProfile.objects.get(user=user_1)
        profile_2 = UserProfile.objects.get(user=user_2)
        profile_1_current_pk = profile_1.pk
        profile_2_current_pk = profile_2.pk
        self.assertEqual(profile_1_orig_pk, profile_1_current_pk)
        self.assertEqual(profile_2_orig_pk, profile_2_current_pk)

    def test_command_creates_systems(self):
        self.assertEqual(System.objects.count(), 0)
        call_command("add_local_seed_data")
        self.assertEqual(System.objects.count(), 2)
        org = Organisation.objects.first()
        systems = System.objects.all()
        system_names = [system.name for system in systems]
        self.assertIn("Big System", system_names)
        self.assertIn("Little System", system_names)

        for system in systems:
            self.assertEqual(system.organisation, org)


class LocalSeedOrganisationTest(TestCase):
    """The supported local seed process leaves organisation ids to the database (CS-684)."""

    def test_another_organisation_can_be_created_after_seeding(self):
        call_command("add_local_seed_data")
        council = Organisation.objects.get()

        organisation = Organisation.objects.create(name="Another Organisation", organisation_type="mhclg")

        self.assertEqual(
            (council.name, council.organisation_type, council.gss_code), ("An Organisation", "council", "E06000001")
        )
        self.assertNotEqual(organisation.pk, council.pk)
        self.assertEqual(Organisation.objects.count(), 2)

    def test_add_organisations_command_is_retired(self):
        with self.assertRaises(CommandError):
            call_command("add_organisations")
