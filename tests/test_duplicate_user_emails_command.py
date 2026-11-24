from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from webcaf.webcaf.models import Organisation, UserProfile


class FindDuplicateUserEmailsCommandTest(TestCase):
    def run_command(self):
        output = StringIO()
        call_command("find_duplicate_user_emails", stdout=output)
        return output.getvalue()

    def test_no_duplicates(self):
        User.objects.create_user(username="one", email="one@example.gov.uk")
        User.objects.create_user(username="two", email="two@example.gov.uk")

        self.assertIn("Found 0 duplicate email groups.", self.run_command())

    def test_lists_mixed_case_duplicates_with_membership_context_without_emails(self):
        first = User.objects.create_user(username="first", email="Person@Example.gov.uk")
        second = User.objects.create_user(username="second", email="person@example.gov.uk", is_active=False)
        organisation = Organisation.objects.create(name="Test organisation")
        profile = UserProfile.objects.create(user=first, organisation=organisation, role="organisation_lead")
        users_before = list(User.objects.order_by("pk").values())
        profiles_before = list(UserProfile.objects.order_by("pk").values())
        history_before = UserProfile.history.count()

        output = self.run_command()

        self.assertIn("Found 1 duplicate email groups.", output)
        self.assertIn(f"user_id={first.pk}", output)
        self.assertIn(f"user_id={second.pk}", output)
        self.assertIn(f"profile_id={profile.pk} organisation_id={organisation.pk} role=organisation_lead", output)
        self.assertIn("active=False", output)
        self.assertNotIn("@", output)
        self.assertNotIn("Person", output)
        self.assertEqual(list(User.objects.order_by("pk").values()), users_before)
        self.assertEqual(list(UserProfile.objects.order_by("pk").values()), profiles_before)
        self.assertEqual(UserProfile.history.count(), history_before)

    def test_includes_staff_accounts_with_case_only_duplicates(self):
        first = User.objects.create_user(username="first", email="person@example.gov.uk")
        staff = User.objects.create_user(username="staff", email="PERSON@example.gov.uk", is_staff=True)

        output = self.run_command()

        self.assertIn("Found 1 duplicate email groups.", output)
        self.assertIn(f"user_id={first.pk}", output)
        self.assertIn(f"user_id={staff.pk}", output)
        self.assertIn("staff=True", output)

    def test_ignores_groups_with_identical_stored_emails(self):
        User.objects.create_user(username="first", email="Person@example.gov.uk")
        User.objects.create_user(username="second", email="Person@example.gov.uk")

        output = self.run_command()

        self.assertIn("Found 0 duplicate email groups.", output)
        self.assertNotIn("user_id=", output)

    def test_reports_every_account_in_a_group_with_multiple_capitalisations(self):
        users = [
            User.objects.create_user(username="first", email="person@example.gov.uk"),
            User.objects.create_user(username="second", email="person@example.gov.uk"),
            User.objects.create_user(username="third", email="Person@example.gov.uk"),
        ]

        output = self.run_command()

        self.assertIn("Found 1 duplicate email groups.", output)
        self.assertEqual(output.count("user_id="), 3)
        for user in users:
            self.assertIn(f"user_id={user.pk}", output)

    def test_detects_differences_in_domain_capitalisation_only(self):
        # Bypass create_user's domain normalisation to model legacy stored addresses.
        first = User.objects.create(username="first", email="person@Example.gov.uk")
        second = User.objects.create(username="second", email="person@example.gov.uk")

        output = self.run_command()

        self.assertIn("Found 1 duplicate email groups.", output)
        self.assertIn(f"user_id={first.pk}", output)
        self.assertIn(f"user_id={second.pk}", output)

    def test_ignores_empty_emails(self):
        User.objects.create_user(username="first", email="")
        User.objects.create_user(username="second", email="")

        self.assertIn("Found 0 duplicate email groups.", self.run_command())

    def test_reports_separate_groups_and_excludes_unique_users(self):
        for username, email in (
            ("first", "first@example.gov.uk"),
            ("first-upper", "FIRST@example.gov.uk"),
            ("second", "second@example.gov.uk"),
            ("second-upper", "SECOND@example.gov.uk"),
        ):
            User.objects.create_user(username=username, email=email)
        unique_user = User.objects.create_user(username="unique", email="unique@example.gov.uk")
        identical_users = [
            User.objects.create_user(username="identical-first", email="identical@example.gov.uk"),
            User.objects.create_user(username="identical-second", email="identical@example.gov.uk"),
        ]

        output = self.run_command()

        self.assertIn("Found 2 duplicate email groups.", output)
        self.assertNotIn(f"user_id={unique_user.pk}", output)
        for user in identical_users:
            self.assertNotIn(f"user_id={user.pk}", output)
        self.assertEqual(output.count("user_id="), 4)
