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
