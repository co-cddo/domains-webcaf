import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import UserProfile


@pytest.mark.django_db
class TestUserProfileView(BaseViewTest):
    def setUp(self):
        """Set up test client and session"""
        self.client = Client()
        # Use organisation lead as they have permission to manage users
        self.org_lead_user = self.org_map[self.organisation_name]["users"]["organisation_lead"]
        self.org_lead_profile = UserProfile.objects.get(user=self.org_lead_user, organisation=self.test_organisation)

        # Create a user profile to edit
        self.target_user = User.objects.create_user(username="testuser@example.com", email="testuser@example.com")
        self.target_profile = UserProfile.objects.create(
            user=self.target_user, organisation=self.test_organisation, role="organisation_user"
        )

        self.client.force_login(self.org_lead_user)
        session = self.client.session
        session["current_profile_id"] = self.org_lead_profile.id
        session.save()

    def test_create_user_with_mixed_case_email_is_lowercased(self):
        """
        When creating a user with a mixed-case email address via CreateUserProfileView,
        the email should be saved in lowercase and the username should match the email.
        """
        mixed_email = "NewUser@BigOrganisation.gov.uk"
        expected_email = mixed_email.lower()

        # First GET to initialise any view state
        self.client.get(reverse("create-new-profile"))

        response = self.client.post(
            reverse("create-new-profile"),
            data={
                "email": mixed_email,
                "role": "organisation_user",
                "first_name": "New",
                "last_name": "Person",
                "action": "confirm",
            },
        )

        # Should redirect to success URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/view-profiles/")

        # User should be created with lowercased email and username
        user = User.objects.get(email=expected_email)
        self.assertEqual(user.username, expected_email)

        # A UserProfile should be created for the same organisation
        profile = UserProfile.objects.get(user=user, organisation=self.test_organisation)
        self.assertEqual(profile.role, "organisation_user")

    def test_form_valid_saves_profile_changes(self):
        """Test that form_valid saves the user profile with valid data
        Converting organisation user to organisation lead
        """
        # Get the edit profile page first
        self.client.get(reverse("edit-profile", kwargs={"user_profile_id": self.target_profile.id}))

        # Post valid data with action=confirm
        response = self.client.post(
            reverse("edit-profile", kwargs={"user_profile_id": self.target_profile.id}),
            data={
                "email": self.target_user.email,
                "role": "organisation_lead",
                "first_name": "Test",
                "last_name": "User",
                "action": "confirm",
            },
        )

        # Refresh from database
        self.target_profile.refresh_from_db()

        # Assert the role was updated
        self.assertEqual(self.target_profile.role, "organisation_lead")
        self.assertEqual(self.target_profile.user.first_name, "Test")
        self.assertEqual(self.target_profile.user.last_name, "User")
        # Assert redirect to success URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/view-profiles/")

    def test_form_valid_saves_profile_changes_with_email(self):
        """Test that form_valid saves the user profile with valid data
        Converting organisation user to organisation lead
        """
        # Get the edit profile page first
        self.client.get(reverse("edit-profile", kwargs={"user_profile_id": self.target_profile.id}))

        # Post valid data with action=confirm
        response = self.client.post(
            reverse("edit-profile", kwargs={"user_profile_id": self.target_profile.id}),
            data={
                "email": "new-email@@bigorganisation.gov.uk",
                "role": "organisation_lead",
                "action": "confirm",
                "first_name": "Test",
                "last_name": "User",
            },
        )

        # Refresh from database
        self.target_profile.refresh_from_db()

        # Assert the role was updated
        self.assertEqual(self.target_profile.role, "organisation_lead")
        self.assertEqual(self.target_profile.user.email, "new-email@@bigorganisation.gov.uk")
        self.assertEqual(self.target_profile.user.username, "new-email@@bigorganisation.gov.uk")
        # Assert redirect to success URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/view-profiles/")

    def test_form_valid_returns_to_form_with_change_action(self):
        """Test that form_valid returns to edit form when action is 'change'"""
        # Get the edit profile page first
        self.client.get(reverse("edit-profile", kwargs={"user_profile_id": self.target_profile.id}))

        # Post with action=change
        response = self.client.post(
            reverse("edit-profile", kwargs={"user_profile_id": self.target_profile.id}),
            data={
                "email": self.target_user.email,
                "role": "organisation_lead",
                "action": "change",
                "first_name": "Test",
                "last_name": "User",
            },
        )

        # Should show confirmation template
        self.assertEqual(response.status_code, 200)
        self.assertIn("users/user.html", [t.name for t in response.templates])

    def test_form_valid_raises_permission_error_for_cyber_advisor_role(self):
        """
        Test that form_valid raises PermissionError when trying to set cyber_advisor role
        Not allowed to change role to cyber_advisor
        """
        # Get the edit profile page first
        self.client.get(reverse("edit-profile", kwargs={"user_profile_id": self.target_profile.id}))

        # Assert PermissionError is raised when trying to set cyber_advisor role
        with pytest.raises(PermissionError, match="You are not allowed to change this role"):
            self.client.post(
                reverse("edit-profile", kwargs={"user_profile_id": self.target_profile.id}),
                data={
                    "email": self.target_user.email,
                    "role": "cyber_advisor",
                    "action": "confirm",
                    "first_name": "Test",
                    "last_name": "User",
                },
            )

    def test_form_valid_does_not_save_with_change_action(self):
        """Test that form_valid does not persist changes when action is 'change'"""
        original_role = self.target_profile.role

        # Get the edit profile page first
        self.client.get(reverse("edit-profile", kwargs={"user_profile_id": self.target_profile.id}))

        # Post with action=change
        self.client.post(
            reverse("edit-profile", kwargs={"user_profile_id": self.target_profile.id}),
            data={
                "email": self.target_user.email,
                "role": "organisation_lead",
                "action": "change",
                "first_name": "Test",
                "last_name": "User",
            },
        )

        # Refresh from database
        self.target_profile.refresh_from_db()

        # Assert the role was NOT updated
        self.assertEqual(self.target_profile.role, original_role)

    def test_create_profile(self):
        """Test creating a new user profile"""
        new_email = "newuser@bigorganisation.gov.uk"

        response = self.client.post(
            reverse("create-new-profile"),
            data={
                "email": new_email,
                "role": "organisation_user",
                "action": "confirm",
                "first_name": "Test",
                "last_name": "User",
            },
        )

        # Assert user was created
        self.assertTrue(User.objects.filter(email=new_email).exists())
        created_user = User.objects.get(email=new_email)

        # Assert profile was created
        self.assertTrue(UserProfile.objects.filter(user=created_user, organisation=self.test_organisation).exists())

        created_profile = UserProfile.objects.get(user=created_user)
        self.assertEqual(created_profile.role, "organisation_user")

        # Assert redirect to success URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/view-profiles/")

    def test_cyber_advisor_cannot_be_created_on_front_end(self):
        """
        This method ensures that a cyber_advisor role cannot be assigned on the front-end.
        """
        new_email = "cyberadvisor2@bigorganisation.gov.uk"

        # Get the create profile page
        self.client.get(reverse("create-new-profile"))

        # Assert PermissionError is raised when trying to create cyber_advisor
        with pytest.raises(PermissionError, match="You are not allowed to change this role"):
            self.client.post(
                reverse("create-new-profile"),
                data={
                    "email": new_email,
                    "role": "cyber_advisor",
                    "action": "confirm",
                    "first_name": "Test",
                    "last_name": "User",
                },
            )

        # Assert user was not created with cyber_advisor role
        self.assertFalse(User.objects.filter(email=new_email).exists())

    def test_create_profile_with_new_email_creates_new_user(self):
        """
        When creating a profile with an email that doesn't match any existing user,
        a new user should be created and assigned to the profile.
        """
        new_email = "brandnew@bigorganisation.gov.uk"
        first_name = "Brand"
        last_name = "New"

        # Verify user doesn't exist
        self.assertFalse(User.objects.filter(email=new_email).exists())

        response = self.client.post(
            reverse("create-new-profile"),
            data={
                "email": new_email,
                "role": "organisation_user",
                "action": "confirm",
                "first_name": first_name,
                "last_name": last_name,
            },
        )

        # Should redirect to success URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/view-profiles/")

        # New user should be created
        self.assertTrue(User.objects.filter(email=new_email).exists())
        created_user = User.objects.get(email=new_email)
        self.assertEqual(created_user.first_name, first_name)
        self.assertEqual(created_user.last_name, last_name)
        self.assertEqual(created_user.username, new_email)

        # Profile should be created with the new user
        profile = UserProfile.objects.get(user=created_user, organisation=self.test_organisation)
        self.assertEqual(profile.role, "organisation_user")

    def test_create_profile_with_existing_email_associates_existing_user(self):
        """
        When creating a profile with an email that matches an existing user,
        that existing user should be associated with the profile and their name should be updated.
        """
        # Create an existing user without a profile in this organisation
        existing_email = "existing@bigorganisation.gov.uk"
        existing_user = User.objects.create_user(
            username=existing_email, email=existing_email, first_name="Old", last_name="Name"
        )

        new_first_name = "Updated"
        new_last_name = "Person"

        response = self.client.post(
            reverse("create-new-profile"),
            data={
                "email": existing_email,
                "role": "organisation_user",
                "action": "confirm",
                "first_name": new_first_name,
                "last_name": new_last_name,
            },
        )

        # Should redirect to success URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/view-profiles/")

        # Should not create a new user
        self.assertEqual(User.objects.filter(email=existing_email).count(), 1)

        # User's name should be updated
        existing_user.refresh_from_db()
        self.assertEqual(existing_user.first_name, new_first_name)
        self.assertEqual(existing_user.last_name, new_last_name)

        # Profile should be created with the existing user
        profile = UserProfile.objects.get(user=existing_user, organisation=self.test_organisation)
        self.assertEqual(profile.role, "organisation_user")

    def test_update_profile_with_new_email_creates_new_user_and_orphans_old(self):
        """
        When updating a profile with an email that doesn't match any existing user,
        a new user should be created and assigned, and the old user should be orphaned.
        """
        # Keep reference to old user
        old_user = self.target_user
        old_user_id = old_user.id

        new_email = "completelynew@bigorganisation.gov.uk"
        new_first_name = "Completely"
        new_last_name = "New"

        # Verify new user doesn't exist
        self.assertFalse(User.objects.filter(email=new_email).exists())

        response = self.client.post(
            reverse("edit-profile", kwargs={"user_profile_id": self.target_profile.id}),
            data={
                "email": new_email,
                "role": "organisation_lead",
                "action": "confirm",
                "first_name": new_first_name,
                "last_name": new_last_name,
            },
        )

        # Should redirect to success URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/view-profiles/")

        # New user should be created
        self.assertTrue(User.objects.filter(email=new_email).exists())
        new_user = User.objects.get(email=new_email)
        self.assertEqual(new_user.first_name, new_first_name)
        self.assertEqual(new_user.last_name, new_last_name)

        # Profile should now be associated with the new user
        self.target_profile.refresh_from_db()
        self.assertEqual(self.target_profile.user.id, new_user.id)
        self.assertEqual(self.target_profile.role, "organisation_lead")

        # Old user should still exist but not be associated with any profile in this organisation
        old_user.refresh_from_db()
        self.assertEqual(old_user.id, old_user_id)
        self.assertFalse(UserProfile.objects.filter(user=old_user, organisation=self.test_organisation).exists())

    def test_update_profile_with_existing_email_associates_existing_user_and_orphans_old(self):
        """
        When updating a profile with an email that matches an existing user,
        that existing user should be associated with the profile (and their name updated),
        and the old user should be orphaned.
        """
        # Create an existing user without a profile in this organisation
        existing_email = "existingother@bigorganisation.gov.uk"
        existing_user = User.objects.create_user(
            username=existing_email, email=existing_email, first_name="Existing", last_name="Other"
        )

        # Keep reference to old user
        old_user = self.target_user
        old_user_id = old_user.id

        new_first_name = "Updated"
        new_last_name = "Name"

        response = self.client.post(
            reverse("edit-profile", kwargs={"user_profile_id": self.target_profile.id}),
            data={
                "email": existing_email,
                "role": "organisation_lead",
                "action": "confirm",
                "first_name": new_first_name,
                "last_name": new_last_name,
            },
        )

        # Should redirect to success URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/view-profiles/")

        # Should not create a new user
        self.assertEqual(User.objects.filter(email=existing_email).count(), 1)

        # Existing user's name should be updated
        existing_user.refresh_from_db()
        self.assertEqual(existing_user.first_name, new_first_name)
        self.assertEqual(existing_user.last_name, new_last_name)

        # Profile should now be associated with the existing user
        self.target_profile.refresh_from_db()
        self.assertEqual(self.target_profile.user.id, existing_user.id)
        self.assertEqual(self.target_profile.role, "organisation_lead")

        # Old user should still exist but not be associated with any profile in this organisation
        old_user.refresh_from_db()
        self.assertEqual(old_user.id, old_user_id)
        self.assertFalse(UserProfile.objects.filter(user=old_user, organisation=self.test_organisation).exists())
