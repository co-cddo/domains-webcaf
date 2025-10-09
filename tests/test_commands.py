import importlib
import os

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from webcaf.webcaf.models import Organisation, System, UserProfile


class AddOrganisationsCommandTest(TestCase):
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    fixture_csv = os.path.join(fixtures_dir, "orgs_fixture.csv")

    def setUp(self):
        self._orig_csv_path = None
        cmd_mod = importlib.import_module("webcaf.webcaf.management.commands.add_organisations")
        self._orig_csv_path = getattr(cmd_mod, "CSV_PATH", None)
        cmd_mod.CSV_PATH = self.fixture_csv

    def tearDown(self):
        cmd_mod = importlib.import_module("webcaf.webcaf.management.commands.add_organisations")
        if self._orig_csv_path is not None:
            cmd_mod.CSV_PATH = self._orig_csv_path

    def test_does_nothing_if_table_not_empty(self):
        Organisation.objects.create(pk=999, name="Dummy Org", organisation_type="other")
        call_command("add_organisations")
        self.assertEqual(Organisation.objects.count(), 1)
        self.assertTrue(Organisation.objects.filter(pk=999).exists())

    def test_adds_organisations_if_table_empty(self):
        self.assertEqual(Organisation.objects.count(), 0)
        call_command("add_organisations")
        self.assertEqual(Organisation.objects.count(), 5)
        names = set(Organisation.objects.values_list("name", flat=True))
        self.assertSetEqual(
            names,
            {
                "Cabinet Office",
                "British Library",
                "Civil Aviation Authority",
                "Competition and Markets Authority",
                "Department for Education",
            },
        )

    def test_pk_set_from_csv(self):
        call_command("add_organisations")
        expected_pks = {1, 60, 87, 175, 212}
        actual_pks = set(Organisation.objects.values_list("pk", flat=True))
        self.assertSetEqual(actual_pks, expected_pks)


class TestAddLocalUsers(TestCase):
    def setUp(self):
        Organisation.objects.create(name="TestOrg")

    def tearDown(self):
        User.objects.all().delete()
        UserProfile.objects.all().delete()
        Organisation.objects.all().delete()
        System.objects.all().delete()

    def test_command_creates_admin_user_when_none_exist(self):
        call_command("add_local_seed_data")
        superuser = User.objects.get(username="admin")
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_staff)

    def test_command_does_not_create_admin_user_if_it_exists(self):
        User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password"  # pragma: allowlist secret
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
