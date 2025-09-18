from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from webcaf.webcaf.models import Assessment, Organisation, System, UserProfile


def setUpModule():
    call_command("add_seed_data")


class SetupAssessmentTestData(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_assessment_url = reverse("create-draft-assessment")
        cls.create_system_url = reverse("create-draft-assessment-system")
        cls.create_profile_url = reverse("create-draft-assessment-profile")
        cls.create_review_type_url = reverse("create-draft-assessment-choose-review-type")

        cls.user_profile = UserProfile.objects.all()[0]
        cls.test_system = System.objects.all()[0]
        cls.test_user = User.objects.all()[0]
        cls.test_organisation = Organisation.objects.get(id=cls.test_system.organisation.id)
        cls.user_profile.organisation = cls.test_organisation
        cls.user_profile.save()

    def setUp(self):
        self.client = Client()
        # login to authenticate test user
        self.client.force_login(self.test_user)
        session = self.client.session
        session["current_profile_id"] = self.user_profile.id
        session.save()


class TestCreateAssessmentViews(SetupAssessmentTestData):
    def setUp(self):
        super().setUp()
        self.edit_review_type_url = reverse("edit-draft-assessment-choose-review-type", kwargs={"assessment_id": 1})

    def test_create_system(self):
        response = self.client.get(self.create_system_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "system/system-details.html")

    def test_create_profile(self):
        response = self.client.get(self.create_profile_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "assessment-profile.html")

    def test_create_review_type(self):
        response = self.client.get(self.create_review_type_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "assessment/choose-review-type.html")

    def test_profile_baseline(self):
        """test selection of baseline caf profile, results in simply returning to the draft asssessment page"""

        # populate the session with required values for test case
        session = self.client.session
        session["draft_assessment"] = {"system": self.test_system.id}

        session.save()

        # form data
        valid_data = {"caf_profile": "baseline"}
        response = self.client.post(self.create_profile_url, valid_data)

        # The Assessment will not be saved outside the session, as all of system profile and review must be complete first
        # we do not expect to have prepopulated review type in this scenario
        self.assertEqual(
            self.client.session["draft_assessment"], {"system": self.test_system.id, "caf_profile": "baseline"}
        )
        # We should also be redirected to the review page to be shown this review type is mandatory for an enhanced profile
        self.assertRedirects(response, self.create_assessment_url)

    def test_profile_enhanced(self):
        """test selection of enhanced caf profile, that completes section 1, results an independent review type"""

        # populate the session with required values for test case
        session = self.client.session
        session["draft_assessment"] = {"system": self.test_system.id}
        session["current_profile_id"] = self.user_profile.id
        session.save()

        # form data
        valid_data = {"caf_profile": "enhanced"}
        response = self.client.post(self.create_profile_url, valid_data)

        # we can now test that submission o the profile form has created the correct reviewtype in
        # the assessment
        assessment = Assessment.objects.get(id=1)
        self.assertEqual(assessment.review_type, "independent")

        # We should also be redirected to the review page to be shown this review type is mandatory for an enhanced profile
        self.assertRedirects(response, self.edit_review_type_url)


class TestEditAssessmentViews(SetupAssessmentTestData):
    def setUp(self):
        super().setUp()
        self.assessment = Assessment.objects.create(
            system=self.test_system,
            status="draft",
            assessment_period="25/26",
            review_type="peer_review",
            framework="caf32",
            caf_profile="baseline",
        )
        self.edit_asssement_url = reverse("edit-draft-assessment", kwargs={"assessment_id": self.assessment.id})
        self.edit_system_url = reverse("edit-draft-assessment-system", kwargs={"assessment_id": self.assessment.id})
        self.edit_profile_url = reverse("edit-draft-assessment-profile", kwargs={"assessment_id": self.assessment.id})
        self.edit_review_type_url = reverse(
            "edit-draft-assessment-choose-review-type", kwargs={"assessment_id": self.assessment.id}
        )

    def test_edit_system(self):
        response = self.client.get(self.edit_system_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "system/system-details.html")

    def test_edit_profile(self):
        response = self.client.get(self.create_profile_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "assessment-profile.html")

    def test_edit_review_type(self):
        response = self.client.get(self.create_review_type_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "assessment/choose-review-type.html")

    def test_edit_completed_profile_to_enhanced(self):
        """
        this tests the scenario where the assessment was initially created as a baseline
        profile not with independent review, that is then changed to enhanced so we expect
        the review type to be automatically set to independent
        """
        # populate the session with required values for test case
        session = self.client.session
        session["draft_assessment"] = {
            "system": self.assessment.system.id,
            "review_type": self.assessment.review_type,
            "assessment_id": self.assessment.id,
        }
        session["current_profile_id"] = self.user_profile.id
        session.save()

        # form data
        valid_data = {"caf_profile": "enhanced"}
        response = self.client.post(self.edit_profile_url, valid_data)
        assessment = Assessment.objects.get(id=self.assessment.id)
        self.assertEqual(assessment.review_type, "independent")
        self.assertRedirects(response, self.edit_review_type_url)
