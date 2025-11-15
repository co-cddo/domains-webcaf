import pytest
from django.test import Client
from django.urls import reverse

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import System, UserProfile


class TestSystemViewFormValidation(BaseViewTest):
    """Tests for creating a new System via SystemView focusing on SystemForm.clean behaviour."""

    def setUp(self):
        # Use a cyber_advisor user as required by the view permissions
        self.client = Client()
        self.cyber_user = self.org_map[self.organisation_name]["users"]["cyber_advisor"]
        self.client.force_login(self.cyber_user)
        # Ensure the session's current_profile_id matches the logged-in user profile
        self.cyber_profile = UserProfile.objects.get(user=self.cyber_user, role="cyber_advisor")
        session = self.client.session
        session["current_profile_id"] = self.cyber_profile.id
        session.save()

        # Convenience: pick valid choice keys
        self.system_type = System.SYSTEM_TYPES[0][0]
        self.last_assessed = System.ASSESSED_CHOICES[0][0]
        self.system_owner = [System.OWNER_TYPES[0][0]]
        self.hosting_type = [System.HOSTING_TYPES[0][0]]
        self.non_other_corp_service = System.CORPORATE_SERVICES[0][0]

    def test_clean_requires_description_when_corporate_services_is_other(self):
        """Selecting 'other' in corporate_services without description should raise validation error."""
        resp = self.client.post(
            reverse("create-new-system"),
            data={
                "action": "confirm",
                "name": "New Test System",
                "system_type": self.system_type,
                "last_assessed": self.last_assessed,
                "system_owner": self.system_owner,
                "hosting_type": self.hosting_type,
                "corporate_services": ["other"],
                "corporate_services_other": "",
            },
        )
        self.assertEqual(resp.status_code, 200)
        form = resp.context["form"]
        self.assertIn("corporate_services_other", form.errors)
        self.assertIn("Please enter a description of the corporate services.", form.errors["corporate_services_other"])

    def test_clean_clears_other_description_when_not_other(self):
        """When corporate_services does not include 'other', 'corporate_services_other' should be cleared on save."""
        name = "System Without Other"
        resp = self.client.post(
            reverse("create-new-system"),
            data={
                "action": "confirm",
                "name": name,
                "system_type": self.system_type,
                "last_assessed": self.last_assessed,
                "system_owner": self.system_owner,
                "hosting_type": self.hosting_type,
                "corporate_services": [self.non_other_corp_service],
                # Even if the user provides text, clean() should blank it when not 'other'
                "corporate_services_other": "Should be cleared",
            },
            follow=False,
        )
        # Successful creation should redirect
        self.assertIn(resp.status_code, (302, 303))
        system = System.objects.get(name=name, organisation=self.cyber_profile.organisation)
        self.assertEqual(system.corporate_services_other, "")


@pytest.mark.django_db
class TestEditSystemViewFormValidation(BaseViewTest):
    """Tests for editing a System via EditSystemView focusing on SystemForm.clean behaviour."""

    def setUp(self):
        # Use a cyber_advisor user as required by the view permissions
        self.client = Client()
        self.cyber_user = self.org_map[self.organisation_name]["users"]["cyber_advisor"]
        self.client.force_login(self.cyber_user)
        # Ensure the session's current_profile_id matches the logged-in user profile
        self.cyber_profile = UserProfile.objects.get(user=self.cyber_user, role="cyber_advisor")
        session = self.client.session
        session["current_profile_id"] = self.cyber_profile.id
        session.save()

        # Test system belongs to the same organisation as in BaseViewTest
        self.system = self.test_system
        # Ensure some initial value to be cleared later
        self.system.corporate_services_other = "Existing other description"
        self.system.save()

        # Convenience: pick valid choice keys
        self.system_type = System.SYSTEM_TYPES[0][0]
        self.last_assessed = System.ASSESSED_CHOICES[0][0]
        self.system_owner = [System.OWNER_TYPES[0][0]]
        self.hosting_type = [System.HOSTING_TYPES[0][0]]
        self.non_other_corp_service = System.CORPORATE_SERVICES[0][0]

    def test_clean_requires_description_when_corporate_services_is_other_on_edit(self):
        resp = self.client.post(
            reverse("edit-system", kwargs={"system_id": self.system.id}),
            data={
                "action": "confirm",
                "name": self.system.name,
                "system_type": self.system_type,
                "last_assessed": self.last_assessed,
                "system_owner": self.system_owner,
                "hosting_type": self.hosting_type,
                "corporate_services": ["other"],
                "corporate_services_other": "",
            },
        )
        self.assertEqual(resp.status_code, 200)
        form = resp.context["form"]
        self.assertIn("corporate_services_other", form.errors)
        self.assertIn("Please enter a description of the corporate services.", form.errors["corporate_services_other"])

    def test_clean_clears_other_description_when_not_other_on_edit(self):
        resp = self.client.post(
            reverse("edit-system", kwargs={"system_id": self.system.id}),
            data={
                "action": "confirm",
                "name": self.system.name,
                "system_type": self.system_type,
                "last_assessed": self.last_assessed,
                "system_owner": self.system_owner,
                "hosting_type": self.hosting_type,
                "corporate_services": [self.non_other_corp_service],
                # Provide text but it should be cleared by clean()
                "corporate_services_other": "Should be cleared",
            },
            follow=False,
        )
        # Successful edit should redirect
        self.assertIn(resp.status_code, (302, 303))
        self.system.refresh_from_db()
        #
        self.assertEqual(self.system.corporate_services_other, "")
