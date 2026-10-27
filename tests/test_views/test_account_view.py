from unittest.mock import patch

from django.test import Client
from django.urls import reverse

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import Assessment, Settings
from webcaf.webcaf.utils.permission import PermissionUtil


class TestAccountView(BaseViewTest):
    def setUp(self):
        self.client = Client()
        self.client, self.profile = self._login_with_role("organisation_lead", self.test_organisation)
        settings = Settings.get_instance()
        settings.filter_previous_assessments = True
        settings.save()

    def test_previous_assessments_link_requires_access_and_previous_assessments(self):
        link_text = "View previous GovAssure submissions"

        with patch.object(Assessment, "is_previous_assessments_present", return_value=True):
            response = self.client.get(reverse("my-account"))
        self.assertContains(response, link_text)

        with (
            patch.object(Assessment, "is_previous_assessments_present", return_value=True),
            patch.object(PermissionUtil, "current_user_can_view_assessments", return_value=False),
            patch.object(PermissionUtil, "current_user_can_create_review", return_value=False),
            patch.object(PermissionUtil, "current_user_can_view_tips", return_value=False),
        ):
            response = self.client.get(reverse("my-account"))
        self.assertNotContains(response, link_text)

        with patch.object(Assessment, "is_previous_assessments_present", return_value=False):
            response = self.client.get(reverse("my-account"))
        self.assertNotContains(response, link_text)
