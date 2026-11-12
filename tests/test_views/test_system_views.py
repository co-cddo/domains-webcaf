from unittest.mock import patch

import pytest
from django.test import Client, override_settings
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

    def _create_system(self, **overrides):
        data = {
            "action": "confirm",
            "name": "Notified System",
            "system_type": self.system_type,
            "last_assessed": self.last_assessed,
            "system_owner": self.system_owner,
            "hosting_type": self.hosting_type,
            "corporate_services": [self.non_other_corp_service],
            "corporate_services_other": "",
            **overrides,
        }
        return self.client.post(reverse("create-new-system"), data=data, follow=False)

    def test_clean_requires_description_when_corporate_services_is_other(self):
        """Selecting 'other' in corporate_services without description should raise validation error."""
        resp = self._create_system(name="New Test System", corporate_services=["other"], corporate_services_other="")
        self.assertEqual(resp.status_code, 200)
        form = resp.context["form"]
        self.assertIn("corporate_services_other", form.errors)
        self.assertIn("Please enter a description of the corporate services.", form.errors["corporate_services_other"])

    def test_clean_clears_other_description_when_not_other(self):
        """When corporate_services does not include 'other', 'corporate_services_other' should be cleared on save."""
        name = "System Without Other"
        # Even if the user provides text, clean() should blank it when not 'other'
        resp = self._create_system(name=name, corporate_services_other="Should be cleared")
        # Successful creation should redirect
        self.assertIn(resp.status_code, (302, 303))
        system = System.objects.get(name=name, organisation=self.cyber_profile.organisation)
        self.assertEqual(system.corporate_services_other, "")

    @override_settings(NOTIFY_NEW_SYSTEM_TEMPLATE_ID="test-new-system-template")
    @patch("webcaf.webcaf.views.system.send_notify_email")
    def test_create_system_sends_notification_email(self, mock_send_email):
        """Creating a system sends a notification email addressed to the organisation leads."""
        org_lead = self.org_map[self.organisation_name]["users"]["organisation_lead"]

        resp = self._create_system()

        self.assertIn(resp.status_code, (302, 303))
        mock_send_email.assert_called_once()
        call_kwargs = mock_send_email.call_args.kwargs
        self.assertEqual(call_kwargs["email_addresses"], [org_lead.email])
        self.assertEqual(call_kwargs["template_id"], "test-new-system-template")

    @override_settings(NOTIFY_NEW_SYSTEM_TEMPLATE_ID="test-new-system-template")
    @patch("webcaf.webcaf.views.system.send_notify_email")
    def test_create_system_email_personalisation(self, mock_send_email):
        """New system notification email carries the expected personalisation fields."""
        name = "Personalised System"
        self._create_system(name=name)

        mock_send_email.assert_called_once()
        personalisation = mock_send_email.call_args.kwargs["personalisation_data"]
        self.assertEqual(personalisation["system_name"], name)
        self.assertEqual(personalisation["organisation_name"], self.cyber_profile.organisation.name)

    @override_settings(NOTIFY_NEW_SYSTEM_TEMPLATE_ID="")
    @patch("webcaf.webcaf.views.system.send_notify_email")
    def test_create_system_does_not_send_email_when_template_id_empty(self, mock_send_email):
        """No notification email is sent when NOTIFY_NEW_SYSTEM_TEMPLATE_ID is empty."""
        resp = self._create_system(name="System Without Email")

        self.assertIn(resp.status_code, (302, 303))
        mock_send_email.assert_not_called()

    @override_settings(NOTIFY_NEW_SYSTEM_TEMPLATE_ID="test-new-system-template")
    @patch("webcaf.webcaf.views.system.send_notify_email")
    def test_create_system_email_failure_does_not_raise_error(self, mock_send_email):
        """Email notification failure is logged and does not break system creation."""
        mock_send_email.side_effect = Exception("Notify service error")
        name = "Email fail System"

        resp = self._create_system(name=name)

        self.assertIn(resp.status_code, (302, 303))
        self.assertTrue(System.objects.filter(name=name, organisation=self.cyber_profile.organisation).exists())


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
