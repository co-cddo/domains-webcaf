from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import close_old_connections
from django.db.models.query import QuerySet
from django.test import TestCase, TransactionTestCase

from webcaf.webcaf.forms.user_profile import UserProfileForm
from webcaf.webcaf.models import Organisation, UserProfile


def profile_form(email, instance=None):
    return UserProfileForm(
        data={
            "email": email,
            "first_name": "New",
            "last_name": "Name",
            "role": "organisation_user",
            "action": "confirm",
        },
        instance=instance,
    )


class UserProfileFormTest(TestCase):
    def test_new_email_is_stripped_and_lowercased(self):
        form = profile_form("  New.Person@Example.gov.uk  ")
        self.assertTrue(form.is_valid(), form.errors)

        profile = form.save()

        self.assertEqual(profile.user.email, "new.person@example.gov.uk")
        self.assertEqual(profile.user.username, "new.person@example.gov.uk")
        self.assertEqual(profile.user.first_name, "New")
        self.assertEqual(profile.user.last_name, "Name")

    def test_invalid_emails_are_rejected_without_creating_records(self):
        for email in ("not-an-email", "new-email@@example.gov.uk", "", "person@"):
            with self.subTest(email=email):
                form = profile_form(email)
                self.assertFalse(form.is_valid())
                self.assertIn("email", form.errors)
        self.assertFalse(User.objects.exists())
        self.assertFalse(UserProfile.objects.exists())

    def test_case_insensitive_match_preserves_existing_user_and_memberships(self):
        # Bypass create_user's domain normalisation to model a legacy stored address.
        user = User.objects.create(
            username="Legacy.Person@Example.gov.uk",
            email="Person@Example.gov.uk",
            first_name="Original",
            last_name="Person",
        )
        organisation = Organisation.objects.create(name="Existing organisation")
        old_profile = UserProfile.objects.create(user=user, organisation=organisation, role="organisation_lead")
        form = profile_form("PERSON@EXAMPLE.GOV.UK")
        self.assertTrue(form.is_valid(), form.errors)

        new_profile = form.save()

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(new_profile.user_id, user.pk)
        user.refresh_from_db()
        self.assertEqual(user.username, "Legacy.Person@Example.gov.uk")
        self.assertEqual(user.email, "Person@Example.gov.uk")
        self.assertEqual(user.first_name, "Original")
        self.assertEqual(user.last_name, "Person")
        old_profile.refresh_from_db()
        self.assertEqual(old_profile.user_id, user.pk)
        self.assertEqual(old_profile.organisation_id, organisation.pk)
        self.assertEqual(old_profile.role, "organisation_lead")

    def test_adding_profile_for_existing_user_preserves_blank_names(self):
        user = User.objects.create_user(username="legacy-person", email="Person@example.gov.uk")
        form = profile_form("person@example.gov.uk")
        self.assertTrue(form.is_valid(), form.errors)

        profile = form.save()

        self.assertEqual(profile.user_id, user.pk)
        user.refresh_from_db()
        self.assertEqual(user.first_name, "")
        self.assertEqual(user.last_name, "")

    def test_case_only_edit_keeps_the_same_user_and_profile(self):
        user = User.objects.create(username="Person@Example.gov.uk", email="Person@Example.gov.uk")
        profile = UserProfile.objects.create(user=user, role="organisation_user")
        form = profile_form("person@example.gov.uk", instance=profile)
        self.assertTrue(form.is_valid(), form.errors)

        saved_profile = form.save()

        self.assertEqual(saved_profile.pk, profile.pk)
        self.assertEqual(saved_profile.user_id, user.pk)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(UserProfile.objects.count(), 1)
        user.refresh_from_db()
        self.assertEqual(user.username, "Person@Example.gov.uk")
        self.assertEqual(user.email, "Person@Example.gov.uk")
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "Name")

    def test_match_created_after_validation_keeps_its_existing_email_and_username(self):
        form = profile_form("PERSON@example.gov.uk")
        self.assertTrue(form.is_valid(), form.errors)
        user = User.objects.create(
            username="legacy-person", email="Person@Example.gov.uk", first_name="Original", last_name="Person"
        )

        profile = form.save()

        self.assertEqual(profile.user_id, user.pk)
        self.assertEqual(User.objects.count(), 1)
        user.refresh_from_db()
        self.assertEqual(user.email, "Person@Example.gov.uk")
        self.assertEqual(user.username, "legacy-person")
        self.assertEqual(user.first_name, "Original")
        self.assertEqual(user.last_name, "Person")

    def test_existing_duplicates_are_not_merged_or_modified(self):
        first = User.objects.create_user(username="first", email="Person@example.gov.uk", first_name="First")
        second = User.objects.create_user(username="second", email="person@example.gov.uk", first_name="Second")
        profile = UserProfile.objects.create(user=first, role="organisation_lead")
        users_before = list(User.objects.order_by("pk").values())
        profiles_before = list(UserProfile.objects.order_by("pk").values())

        for instance in (None, profile):
            with self.subTest(edit=instance is not None):
                form = profile_form("PERSON@example.gov.uk", instance=instance)
                self.assertFalse(form.is_valid())
                self.assertEqual(form.errors.as_data()["email"][0].code, "ambiguous_email")

        self.assertEqual(list(User.objects.order_by("pk").values()), users_before)
        self.assertEqual(list(UserProfile.objects.order_by("pk").values()), profiles_before)
        self.assertTrue(User.objects.filter(pk=second.pk).exists())

    def test_exact_email_duplicates_are_also_rejected(self):
        User.objects.create_user(username="first", email="person@example.gov.uk")
        User.objects.create_user(username="second", email="person@example.gov.uk")

        form = profile_form("person@example.gov.uk")

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors.as_data()["email"][0].code, "ambiguous_email")

    def test_staff_and_inactive_matches_are_not_ignored_when_checking_for_duplicates(self):
        User.objects.create_user(username="first", email="Person@example.gov.uk")
        second = User.objects.create_user(
            username="second", email="person@example.gov.uk", is_staff=True, is_active=False
        )

        form = profile_form("person@example.gov.uk")

        self.assertFalse(form.is_valid())
        second.refresh_from_db()
        self.assertTrue(second.is_staff)
        self.assertFalse(second.is_active)

    def test_username_conflict_is_a_validation_error(self):
        User.objects.create_user(username="new@example.gov.uk", email="different@example.gov.uk")

        form = profile_form("new@example.gov.uk")

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors.as_data()["email"][0].code, "username_conflict")
        self.assertEqual(User.objects.count(), 1)

    def test_save_rechecks_duplicates_created_after_validation(self):
        first = User.objects.create_user(username="first", email="Person@example.gov.uk", first_name="Original")
        form = profile_form("person@example.gov.uk")
        self.assertTrue(form.is_valid(), form.errors)
        User.objects.create_user(username="second", email="person@example.gov.uk")

        with self.assertRaises(ValidationError) as error:
            form.save()

        self.assertIn("email", error.exception.message_dict)
        self.assertEqual(User.objects.count(), 2)
        self.assertFalse(UserProfile.objects.exists())
        first.refresh_from_db()
        self.assertEqual(first.first_name, "Original")

    def test_save_handles_username_conflict_created_after_validation(self):
        form = profile_form("new@example.gov.uk")
        self.assertTrue(form.is_valid(), form.errors)
        User.objects.create_user(username="new@example.gov.uk", email="different@example.gov.uk")

        with self.assertRaises(ValidationError) as error:
            form.save()

        self.assertIn("email", error.exception.message_dict)
        self.assertEqual(User.objects.count(), 1)
        self.assertFalse(UserProfile.objects.exists())

    def test_two_prevalidated_forms_reuse_one_user(self):
        first = profile_form("Person@example.gov.uk")
        second = profile_form("PERSON@example.gov.uk")
        self.assertTrue(first.is_valid(), first.errors)
        self.assertTrue(second.is_valid(), second.errors)

        first_profile = first.save()
        second_profile = second.save()

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(first_profile.user_id, second_profile.user_id)


class ConcurrentUserProfileCreationTest(TransactionTestCase):
    def test_simultaneous_case_variants_create_only_one_user(self):
        barrier = Barrier(2)
        original_create = QuerySet.create

        def synchronised_create(queryset, **kwargs):
            if queryset.model is User:
                barrier.wait(timeout=10)
            return original_create(queryset, **kwargs)

        def create_profile(email):
            close_old_connections()
            try:
                form = profile_form(email)
                if not form.is_valid():
                    raise AssertionError(form.errors)
                return form.save().user_id
            finally:
                close_old_connections()

        with patch.object(QuerySet, "create", synchronised_create), ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(create_profile, ("Person@example.gov.uk", "PERSON@example.gov.uk")))

        self.assertEqual(results[0], results[1])
        self.assertEqual(User.objects.filter(email__iexact="person@example.gov.uk").count(), 1)
