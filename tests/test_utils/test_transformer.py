from unittest import TestCase

from webcaf.webcaf.caf.util import IndicatorStatusChecker
from webcaf.webcaf.utils.data_analysis import transform_assessment, transform_review


def _profile_met_callback(outcome_code: str, status: str | None):
    """
    Mock implementation for status check
    Not implementing the logic as that is not the part of this test
    :param outcome_code:
    :param status:
    :return:
    """
    from webcaf.webcaf.frameworks import routers

    router = routers["caf32"]
    principal = router.get_section(outcome_code[0])["principles"][outcome_code[:2]]  # type: ignore
    outcome = principal["outcomes"][outcome_code]
    min_profile_requirement = outcome.get("min_profile_requirement")
    return IndicatorStatusChecker.calculate_profile_met("baseline", min_profile_requirement, True, status)


class TestAssessmentTransformToOutcomeFormat(TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_transforms_assessment_into_expected_outcomes_format(self):
        assessment = {
            "A1.a": {
                "confirmation": {
                    "outcome_status": "Achieved",
                    "outcome_status_message": "Outcome is met",
                    "confirm_outcome_confirm_comment": "Confirmed by testing",
                },
                "supplementary_questions": [{"question": "Q1", "answer": "A1"}],
                "indicators": {
                    "achieved_A1.a.1": True,
                    "achieved_A1.a.1_comment": "Strong evidence",
                    "not-achieved_A1.a.2": False,
                },
            }
        }

        result = transform_assessment(
            assessment,
            {
                "assessment_id": "abc123",
                "organisation_id": "org123",
                "system_id": "sys123",
                "app_version": "webcaf-2",
                "caf_version": 3.2,
                "caf_description": "GovAssure",
            },
            _profile_met_callback,
        )

        self.assertEqual(result["metadata"], {"completed": None, "created": None, "last_updated": None})
        self.assertEqual(len(result["outcomes"]), 1)
        self.assertEqual(
            result["outcomes"][0],
            {
                "outcome_id": "A1.a",
                "outcome_status": "Achieved",
                "outcome_profile_met": "Met",
                "outcome_min_profile_requirement": "Achieved",
                "outcome_status_message": "Outcome is met",
                "outcome_confirm_comment": "Confirmed by testing",
                "indicators": [
                    {
                        "indicator_id": "A1.a.1",
                        "indicator_category": "achieved",
                        "value": True,
                        "comment": "Strong evidence",
                    },
                    {
                        "indicator_id": "A1.a.2",
                        "indicator_category": "not-achieved",
                        "value": False,
                        "comment": "",
                    },
                ],
                "supplementary_questions": [{"question": "Q1", "answer": "A1"}],
            },
        )

    def test_uses_defaults_when_confirmation_or_indicators_missing(self):
        assessment = {
            "B2.b": {},
        }

        result = transform_assessment(
            assessment,
            {
                "assessment_id": "abc123",
                "organisation_id": "org123",
                "system_id": "sys123",
                "app_version": "webcaf-2",
                "caf_version": 3.2,
                "caf_description": "GovAssure",
            },
            _profile_met_callback,
        )

        self.assertEqual(result["metadata"], {"completed": None, "created": None, "last_updated": None})
        self.assertEqual(result["outcomes"][0]["outcome_id"], "B2.b")
        self.assertEqual(result["outcomes"][0]["outcome_status"], "")
        self.assertEqual(result["outcomes"][0]["outcome_status_message"], "")
        self.assertEqual(result["outcomes"][0]["outcome_confirm_comment"], "")
        self.assertEqual(result["outcomes"][0]["indicators"], [])
        self.assertEqual(result["outcomes"][0]["supplementary_questions"], [])

    def test_only_indicators_present(self):
        """
        Confirm we do not introduce any inconsistent data during the transformation process.
        i.e if the outcome status is not present, we represent with empty string "" and not any
        specific status values
        :return:
        """
        assessment = {
            "A1.a": {
                "indicators": {
                    "achieved_A1.a.1": True,
                    "achieved_A1.a.1_comment": "Some comment",
                },
            },
        }
        result = transform_assessment(
            assessment,
            {
                "assessment_id": "abc123",
                "organisation_id": "org123",
                "system_id": "sys123",
                "app_version": "webcaf-2",
                "caf_version": 3.2,
                "caf_description": "GovAssure",
            },
            _profile_met_callback,
        )
        outcome = result["outcomes"][0]
        self.assertEqual(outcome["outcome_status"], "")
        self.assertEqual(
            outcome["indicators"],
            [
                {"indicator_id": "A1.a.1", "indicator_category": "achieved", "value": True, "comment": "Some comment"},
            ],
        )

    def test_multiple_outcomes_partial_and_full(self):
        assessment = {
            "A1.a": {
                "confirmation": {"outcome_status": "Achieved"},
                "indicators": {"achieved_A1.a.1": True},
            },
            "B1.b": {},
        }
        result = transform_assessment(
            assessment,
            {
                "assessment_id": "abc123",
                "organisation_id": "org123",
                "system_id": "sys123",
                "app_version": "webcaf-2",
                "caf_version": 3.2,
                "caf_description": "GovAssure",
            },
            _profile_met_callback,
        )
        self.assertEqual(result["metadata"], {"completed": None, "created": None, "last_updated": None})
        self.assertEqual(len(result["outcomes"]), 2)
        outcome_codes = {o["outcome_id"] for o in result["outcomes"]}
        self.assertIn("A1.a", outcome_codes)
        self.assertIn("B1.b", outcome_codes)

    def test_empty_assessment_produces_empty_outcomes(self):
        result = transform_assessment(
            {},
            {
                "assessment_id": "abc123",
                "organisation_id": "org123",
                "system_id": "sys123",
                "app_version": "webcaf-2",
                "caf_version": 3.2,
                "caf_description": "GovAssure",
            },
            _profile_met_callback,
        )
        self.assertEqual(result["outcomes"], [])
        self.assertEqual(result["metadata"], {"completed": None, "created": None, "last_updated": None})


class TestReviewTransformToOutcomeFormat(TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_transforms_review_into_expected_outcomes_format(self):
        review = {
            "A": {
                "A1.a": {
                    "indicators": {
                        "achieved_A1.a.5": "yes",
                        "achieved_A1.a.6": "yes",
                        "achieved_A1.a.7": "yes",
                        "achieved_A1.a.8": "yes",
                        "not-achieved_A1.a.1": "yes",
                        "not-achieved_A1.a.2": "yes",
                        "not-achieved_A1.a.3": "yes",
                        "not-achieved_A1.a.4": "yes",
                        "achieved_A1.a.5_comment": "Lorem ipsum ",
                        "achieved_A1.a.6_comment": "Lorem ipsum ",
                        "achieved_A1.a.7_comment": "Lorem ipsum ",
                        "achieved_A1.a.8_comment": "Lorem ipsum ",
                        "not-achieved_A1.a.1_comment": "",
                        "not-achieved_A1.a.2_comment": "",
                        "not-achieved_A1.a.3_comment": "",
                        "not-achieved_A1.a.4_comment": "",
                    },
                    "review_data": {"review_comment": "Lorem ipsum ", "review_decision": "not-achieved"},
                    "recommendations": [
                        {"text": "Lorem ipsum ", "title": "Issue 1"},
                        {"text": "Lorem ipsum ", "title": "Issue 1"},
                        {"text": "Lorem ipsum ", "title": "Issue 2"},
                    ],
                },
                "recommendations": [{"text": "rtyrty", "title": "tryrt ty"}],
                "objective-areas-of-improvement": "Lorem ipsum ",
                "objective-areas-of-good-practice": "Lorem ipsum ",
            },
            "system_and_scope": {
                "completed": "yes",
                "completed_data": {
                    "review_details": {
                        "caf_version": "Cyber Assessment Framework v3.2",
                        "review_type": "Peer review",
                        "government_caf_profile": "Enhanced",
                        "self_assessment_reference_number": "CAF03102025GFLZ",
                    },
                    "system_details": {
                        "system_name": "Test system",
                        "system_ownership": "Another government organisation",
                        "corporate_services": "Office productivity, Procurement and contract management",
                        "system_description": "It provides corporate services or functions required for day-to-day operations for example, payroll",
                        "hosting_and_connectivity": "Hybrid",
                        "other_corporate_services": "",
                        "previous_govassure_self_assessments": "Yes, in 2023/24",
                    },
                },
            },
            "review_completion": {
                "review_completed": "yes",
                "review_completed_at": "2025-12-23T17:52:01.846950",
                "review_completed_by": "cyber_advisor ",
                "review_completed_by_role": "cyber_advisor",
                "review_completed_by_email": "cyber_advisor@example.gov.uk",
            },
            "additional_information": {
                "iar_period": {"end_date": "12/12/2025", "start_date": "11/11/2024"},
                "review-method": "fdffgy ghgfhfg",
                "review_method": "Lorem ipsum ",
                "company_details": {"company_name": "Assessor company", "company_email": "dharshana@ee.com"},
                "quality-of-evidence": "dgdghhdgh",
                "quality_of_evidence": "Lorem ipsum ",
                "areas_for_improvement": "ERT we weer wer",
                "areas_of_good_practice": "dt wrrW RE",
            },
        }

        result = transform_review(
            {k: v for k, v in review.items() if k in {"A", "B", "C", "D"}},
            {
                "assessment_id": "ABC123",
                "app_version": "webcaf-2",
                "additional_information": {"company_details": {"company_name": "independent"}},
            },
            _profile_met_callback,
        )
        self.assertEqual(result["review_details"]["company_name"], "independent")
        self.assertEqual(len(result["outcomes"]), 1)
        self.assertEqual(
            result["outcomes"][0],
            {
                "outcome_id": "A1.a",
                "outcome_min_profile_requirement": "Achieved",
                "recommendations": [
                    {
                        "priority_recommendation": True,
                        "recommendation_id": "REC-A1A1",
                        "recommendation_text": "Lorem ipsum ",
                        "risk_text": "Issue 1",
                    },
                    {
                        "priority_recommendation": True,
                        "recommendation_id": "REC-A1A2",
                        "recommendation_text": "Lorem ipsum ",
                        "risk_text": "Issue 1",
                    },
                    {
                        "priority_recommendation": True,
                        "recommendation_id": "REC-A1A3",
                        "recommendation_text": "Lorem ipsum ",
                        "risk_text": "Issue 2",
                    },
                ],
                "review_decision": "Not achieved",
                "review_profile_met": "Not met",
                "review_comment": "Lorem ipsum ",
                "indicators": [
                    {"indicator_id": "A1.a.5", "category": "achieved", "value": True, "comment": "Lorem ipsum "},
                    {"indicator_id": "A1.a.6", "category": "achieved", "value": True, "comment": "Lorem ipsum "},
                    {"indicator_id": "A1.a.7", "category": "achieved", "value": True, "comment": "Lorem ipsum "},
                    {"indicator_id": "A1.a.8", "category": "achieved", "value": True, "comment": "Lorem ipsum "},
                    {"indicator_id": "A1.a.1", "category": "not-achieved", "value": True, "comment": ""},
                    {"indicator_id": "A1.a.2", "category": "not-achieved", "value": True, "comment": ""},
                    {"indicator_id": "A1.a.3", "category": "not-achieved", "value": True, "comment": ""},
                    {"indicator_id": "A1.a.4", "category": "not-achieved", "value": True, "comment": ""},
                ],
            },
        )

    def test_uses_defaults_when_review_data_or_indicators_missing(self):
        review = {
            "B": {
                "B2.b": {},
            },
        }

        result = transform_review(review, {"assessment_id": "ABC123", "app_version": "webcaf-2"}, _profile_met_callback)

        self.assertEqual(result["outcomes"][0]["outcome_id"], "B2.b")
        self.assertEqual(result["outcomes"][0]["review_decision"], "N/A")
        self.assertEqual(result["outcomes"][0]["review_comment"], "")
        self.assertEqual(result["outcomes"][0]["indicators"], [])
