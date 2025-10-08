import pytest
from django.test import Client
from django.urls import reverse

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import Assessment


@pytest.mark.django_db
class TestEditAssessmentSystemViewFormValid(
    BaseViewTest,
):
    """Test suite for EditAssessmentSystemView.form_valid method"""

    def setUp(self):
        self.assessment = Assessment.objects.create(
            status="draft",
            assessment_period="25/26",
            system=self.test_system,
            framework="caf32",
            caf_profile="baseline",
            review_type="independent",
            created_by=self.test_user,
            last_updated_by=self.test_user,
        )
        self.client = Client()
        self.client.force_login(self.test_user)
        session = self.client.session
        session["current_profile_id"] = self.user_profile.id
        session.save()

    def test_form_valid_updates_session_with_system_id(self):
        """Test that form_valid updates the session with the selected system ID"""
        # you have to call the view before you can access the session
        self.client.get(reverse("edit-draft-assessment-system", kwargs={"assessment_id": self.assessment.id}))
        self.assertEqual(self.assessment.system.id, self.test_system.id)

        available_systems = self.org_map[self.test_organisation.name]["systems"]
        # Default is the medium system
        self.client.post(
            reverse(
                "edit-draft-assessment-system",
                kwargs={"assessment_id": self.assessment.id},
            ),
            data={"system": available_systems["Large system"].id},
        )

        self.assessment.refresh_from_db()
        self.assertEqual(self.assessment.system.id, available_systems["Large system"].id)

    def test_form_valid_raises_permission_error_for_wrong_organisation(self):
        """Test that form_valid raises PermissionError when system belongs to different organisation"""
        # Create another organisation and system
        other_system = self.org_map["Large organisation"]["systems"]["Large system"]
        # View page

        self.client.get(reverse("edit-draft-assessment-system", kwargs={"assessment_id": self.assessment.id}))

        # Assert PermissionError is raised
        with pytest.raises(PermissionError, match="You do not have access to this system"):
            self.client.post(
                reverse(
                    "edit-draft-assessment-system",
                    kwargs={"assessment_id": self.assessment.id},
                ),
                data={"system": other_system.id},
            )
