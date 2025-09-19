import parameterized
from django.test import Client
from django.urls import reverse

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import Assessment, UserProfile


class OutcomeIndicatorsViewTests(BaseViewTest):
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

        # URL name is added dynamically by the CAF32 router in AppConfig.ready()
        cls.url = reverse("caf32_indicators_A1.a")
        cls.confirmation_url = reverse("caf32_confirmation_A1.a")

    def setUp(self):
        self.client = Client()
        # Login the user and set required session keys
        self.client.force_login(self.test_user)
        session = self.client.session
        session["current_profile_id"] = self.user_profile.id
        session["draft_assessment"] = {"assessment_id": self.assessment.id}
        session.save()

    @parameterized.parameterized.expand(
        [
            [
                {
                    "achieved_A1.a.5": False,
                    "achieved_A1.a.6": False,
                    "achieved_A1.a.7": False,
                    "achieved_A1.a.8": False,
                    "not-achieved_A1.a.1": True,
                    "not-achieved_A1.a.2": True,
                    "not-achieved_A1.a.3": True,
                    "not-achieved_A1.a.4": True,
                    "achieved_A1.a.5_comment": "",
                    "achieved_A1.a.6_comment": "",
                    "achieved_A1.a.7_comment": "",
                    "achieved_A1.a.8_comment": "",
                    "not-achieved_A1.a.1_comment": "Comment 1",
                    "not-achieved_A1.a.2_comment": "Comment 2",
                    "not-achieved_A1.a.3_comment": "Comment 3",
                    "not-achieved_A1.a.4_comment": "Comment 4",
                },
                "Achieved",
            ],
            [
                {
                    "achieved_A1.a.5": False,
                    "achieved_A1.a.6": False,
                    "achieved_A1.a.7": False,
                    "achieved_A1.a.8": False,
                    "not-achieved_A1.a.1": True,
                    "not-achieved_A1.a.2": True,
                    "not-achieved_A1.a.3": True,
                    "not-achieved_A1.a.4": True,
                    "achieved_A1.a.5_comment": "",
                    "achieved_A1.a.6_comment": "",
                    "achieved_A1.a.7_comment": "",
                    "achieved_A1.a.8_comment": "",
                    "not-achieved_A1.a.1_comment": "Comment 1",
                    "not-achieved_A1.a.2_comment": "Comment 2",
                    "not-achieved_A1.a.3_comment": "Comment 3",
                    "not-achieved_A1.a.4_comment": "",
                },
                "Not achieved",
            ],
        ]
    )
    def test_post_outcome_indicators_status(self, form_data, expected_outcome):
        """
        Tests the handling of outcome indicators status through a POST request.

        :param form_data:
            Dictionary containing form data to be submitted in the POST request.
            The keys and values represent specific outcomes and their statuses.

        :param expected_outcome:
            String representing the expected outcome status after processing the POST request.
            This can be either "Achieved" or "Not achieved".

        :return:
        """
        response = self.client.post(self.url, data=form_data, follow=True)
        self.assertEqual(response.redirect_chain[0][1], 302)
        self.assertEqual(response.redirect_chain[0][0], reverse("caf32_confirmation_A1.a"))
        self.assertRegex(response.content.decode(), rf"Status: {expected_outcome}")
        # Confirm the database has recorded the information
        self.assessment.refresh_from_db()
        self.assertEqual(form_data, self.assessment.assessments_data["A1.a"]["indicators"])

    def test_post_confirmation_with_no_summary(self):
        """
        Summary:
        This method tests the post confirmation functionality of an assessment.
        It sets up session data with a current profile and draft assessment,
        configures indicator data for the assessment, sends a POST request to confirm the outcome,
        and asserts the response status code and content.
        This scenario tests when the user does not enter summary, which is a validation error.
        :param client: HTTP client instance used to send requests
        :type client: object

        :param user_profiles: List of user profiles available in the system
        :type user_profiles: list

        :param assessment: Assessment object representing the draft assessment being confirmed
        :type assessment: object

        :param confirmation_url: URL for confirming the assessment outcome
        :type confirmation_url: str

        """
        # Setup the indicator data that should exist before the confirmation
        self.assessment.assessments_data = {
            "A1.a": {
                "indicators": {
                    "achieved_A1.a.5": False,
                    "not-achieved_A1.a.1": True,
                    "not-achieved_A1.a.2": True,
                    "achieved_A1.a.5_comment": "",
                    "not-achieved_A1.a.1_comment": "Comment 1",
                    "not-achieved_A1.a.2_comment": "Comment 2",
                }
            }
        }
        self.assessment.save()
        response = self.client.post(
            self.confirmation_url,
            data={"confirm_outcome": "confirm", "confirm_outcome_confirm_comment": ""},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertRegex(response.content.decode(), r"Status: Achieved")
        self.assertRegex(response.content.decode(), r"You must provide a summary.")

    def test_post_confirmation_with_summary(self):
        """
        Sends a post-confirmation request to the server.
        This is the valid path and the confirmation details will be saved in the database.
        USer will be redirected to the objective summary page.
        :param summary: A brief summary of the confirmation request.
        :type summary: str

        :return:
        """
        self.assessment.assessments_data = {
            "A1.a": {
                "indicators": {
                    "achieved_A1.a.5": False,
                    "not-achieved_A1.a.1": True,
                    "not-achieved_A1.a.2": True,
                    "achieved_A1.a.5_comment": "",
                    "not-achieved_A1.a.1_comment": "Comment 1",
                    "not-achieved_A1.a.2_comment": "Comment 2",
                }
            }
        }
        self.assessment.save()
        form_data = {"confirm_outcome": "confirm", "confirm_outcome_confirm_comment": "This is my summary comment"}
        response = self.client.post(
            self.confirmation_url,
            data=form_data,
            follow=True,
        )
        self.assertEqual(
            response.redirect_chain[0][1],
            302,
        )
        self.assertRegex(response.redirect_chain[0][0], "/caf32/a-managing-security-risk/")
        # Confirm the database has recorded the information
        self.assessment.refresh_from_db()
        # We store the calculated outcome status along with the confirmation input
        self.assertEqual(
            {"outcome_status": "Achieved"} | form_data, self.assessment.assessments_data["A1.a"]["confirmation"]
        )

    def test_only_users_in_the_organisation_can_modify(self):
        """
        User will get a 404 if they are not in the organisation's user profile
        :return:
        """

        session = self.client.session
        # Assume the credentials of the same user role, but different organisation
        other_user_profile = UserProfile.objects.get(role=self.user_role, organisation__name="Medium organisation")
        session["current_profile_id"] = other_user_profile.id
        session["draft_assessment"] = {"assessment_id": self.assessment.id}
        session.save()
        self.client.force_login(other_user_profile.user)

        form_data = {
            "achieved_A1.a.5": False,
            "not-achieved_A1.a.1": True,
            "achieved_A1.a.5_comment": "",
            "not-achieved_A1.a.1_comment": "Comment 1",
        }
        with self.assertLogs() as cm:
            response = self.client.post(self.url, data=form_data)
        self.assertEqual(response.status_code, 404)
        self.assertIn(
            "ERROR:SessionUtil:Unable to retrieve assessment with id None for user organisation_user@mediumorganisation.gov.uk",
            cm.output[0],
        )
