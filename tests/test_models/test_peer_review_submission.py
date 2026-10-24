from unittest.mock import patch

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import Assessment, Review


class PeerReviewSubmissionTests(BaseViewTest):
    @classmethod
    def setUpTestData(cls):
        BaseViewTest.setUpTestData()
        cls.assessment = Assessment.objects.create(
            system=cls.test_system,
            assessment_period="24/25",
            framework="caf32",
            caf_profile="baseline",
            review_type="peer_review",
        )
        cls.objective = {
            "code": "A",
            "principles": {
                "A1": {
                    "code": "A1",
                    "outcomes": {"A1.a": {"code": "A1.a"}},
                }
            },
        }

    def set_outcome_data(self, review, recommendations=None):
        outcome_data = {"review_data": {"review_decision": "partially-achieved"}}
        if recommendations is not None:
            outcome_data["recommendations"] = recommendations

        review.review_data = {
            "assessor_response_data": {
                "A": {"A1.a": outcome_data},
                "system_and_scope": {"completed": "yes"},
                "additional_information": {
                    "iar_period": "2024-2025",
                    "quality_of_evidence": "good",
                    "review_method": "interviews",
                    "company_details": {"company_name": "Example"},
                },
            }
        }

    def configure_objective(self):
        self.assessment.get_all_caf_objectives = lambda: [self.objective]
        self.assessment.get_caf_objective_by_id = lambda objective_code: self.objective

    def test_peer_review_requires_recommendations_only_when_minimum_profile_is_not_met(self):
        self.configure_objective()
        review = Review(assessment=self.assessment, status="in_progress")

        with patch(
            "webcaf.webcaf.caf.util.IndicatorStatusChecker.indicator_min_profile_requirement_met",
            return_value="No",
        ):
            self.set_outcome_data(review)
            self.assertFalse(review.is_ready_to_submit())

            self.set_outcome_data(review, recommendations=[{"id": "rec-1"}])
            self.assertTrue(review.is_ready_to_submit())

        with patch(
            "webcaf.webcaf.caf.util.IndicatorStatusChecker.indicator_min_profile_requirement_met",
            return_value="Yes",
        ):
            self.set_outcome_data(review)
            self.assertTrue(review.is_ready_to_submit())

            outcome_info = review.get_completed_outcomes_info()
            self.assertEqual(outcome_info["completed_outcomes"], outcome_info["total_outcomes"])
