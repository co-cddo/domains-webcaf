# Python
from django.test import Client
from django.urls import reverse

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import Assessment


class ObjectiveViewIntegrationTests(BaseViewTest):
    @classmethod
    def setUpTestData(cls):
        BaseViewTest.setUpTestData()
        # Create a draft assessment for caf32 so the session can resolve it
        cls.assessment = Assessment.objects.create(
            system=cls.test_system,
            status="draft",
            assessment_period="25/26",
            review_type="peer_review",
            framework="caf32",
            caf_profile="baseline",
        )

    def setUp(self):
        self.client = Client()
        # Login the user and set required session keys
        self.client.force_login(self.test_user)
        session = self.client.session
        session["current_profile_id"] = self.user_profile.id
        session["draft_assessment"] = {"assessment_id": self.assessment.id}
        session.save()

    def test_post_confirm_redirects_to_next_objective(self):
        response = self.client.get(reverse("caf32_objective_A"), follow=False)
        self.assertInHTML(
            '<input type="hidden" name="next_objective" value="B">',
            response.content.decode(),
        )

        # Post with action=confirm -> should go to <framework>_objective_<next_objective>
        resp = self.client.post(
            reverse("caf32_objective_A"),
            data={"action": "confirm", "next_objective": "B"},
            follow=False,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/caf32/b-protecting-against-cyber-attack/")

    def test_post_skip_redirects_to_edit_draft_assessment(self):
        # Post with action=skip -> should go to edit-draft-assessment/<assessment_id>/
        resp = self.client.post(
            reverse("caf32_objective_A"),
            data={"action": "skip", "next_objective": "B"},
            follow=False,
        )
        self.assertEqual(resp.status_code, 302)

        expected_url = reverse("edit-draft-assessment", kwargs={"assessment_id": self.assessment.id})
        self.assertEqual(resp["Location"], expected_url)
