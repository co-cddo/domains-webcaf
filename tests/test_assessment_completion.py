# Python
from unittest.mock import Mock

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import Assessment


class AssessmentCompletionWithIndicatorsShapeTests(BaseViewTest):
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

    def test_is_objective_complete_false_when_no_data(self):
        # Default there is no data
        self.assertFalse(self.assessment.is_objective_complete("A"))

    def test_is_objective_complete_false_without_confirmation(self):
        # Data present but missing confirmation block
        self.assessment.assessments_data = {
            f"{code}": {
                "indicators": {
                    f"achieved_{code}.5": False,
                    f"not-achieved_{code}.1": True,
                },
                "confirmation": {},
            }
            for code in ["A1.a", "A1.b", "A1.c", "A2.a", "A2.b", "A3.a", "A4.a"]
        }
        self.assertFalse(self.assessment.is_objective_complete("A"))

    def test_is_objective_complete_true_with_confirmation_block(self):
        # Matches your example shape: indicators + confirmation containing confirm_outcome
        self.assessment.assessments_data = {
            f"{code}": {
                "indicators": {
                    f"achieved_{code}.5": False,
                    f"not-achieved_{code}.1": True,
                },
                "confirmation": {"confirm_outcome": "confirm"},
            }
            for code in ["A1.a", "A1.b", "A1.c", "A2.a", "A2.b", "A3.a", "A4.a"]
        }
        self.assertTrue(self.assessment.is_objective_complete("A"))

    def test_is_objective_complete_false_if_any_outcome_missing_confirmation(self):
        # Only A1.a confirmed; A1.b has indicators but no confirmation
        self.assessment.assessments_data = {
            f"{code}": {
                "indicators": {
                    f"achieved_{code}.5": False,
                    f"not-achieved_{code}.1": True,
                },
                "confirmation": {"confirm_outcome": "confirm"},
            }
            for code in ["A1.a", "A1.b", "A1.c", "A2.a", "A2.b", "A3.a", "A4.a"]
        }
        # Remove the confirmation for A1.a
        self.assessment.assessments_data["A1.a"]["confirmation"] = {}
        self.assertFalse(self.assessment.is_objective_complete("A"))

    def test_is_complete_true_when_all_objectives_complete(self):
        # Two objectives each with one outcome and both confirmed

        mock_router = self.get_mock_router()
        self.assessment.get_router = Mock(return_value=mock_router)
        for code in ["A", "B"]:
            for item in [
                f"{code}1.a",
                f"{code}1.b",
                f"{code}1.c",
                f"{code}2.a",
                f"{code}2.b",
                f"{code}3.a",
                f"{code}4.a",
            ]:
                self.assessment.assessments_data[item] = {}
                self.assessment.assessments_data[item]["indicators"] = {}
                self.assessment.assessments_data[item]["confirmation"] = {}
                self.assessment.assessments_data[item]["indicators"][f"achieved_{item}"] = False
                self.assessment.assessments_data[item]["confirmation"]["confirm_outcome"] = "confirm"

        self.assertTrue(self.assessment.is_complete())

    def test_is_complete_false_when_any_objectives_incomplete(self):
        """
        Tests that the :func:`is_complete` method returns ``False`` when any objectives are incomplete.

        This test configures a mock router and populates the assessment data with various items,
        setting indicators to ``False`` for all of them except one specific item ("B4.a").
        The confirmation status for "B4.a" is removed, making its objective incomplete.
        The method under test, :func:`is_complete`, should then return ``False``
        indicating that not all objectives are complete.
        """
        mock_router = self.get_mock_router()
        self.assessment.get_router = Mock(return_value=mock_router)
        for code in ["A", "B"]:
            for item in [
                f"{code}1.a",
                f"{code}1.b",
                f"{code}1.c",
                f"{code}2.a",
                f"{code}2.b",
                f"{code}3.a",
                f"{code}4.a",
            ]:
                self.assessment.assessments_data[item] = {}
                self.assessment.assessments_data[item]["indicators"] = {}
                self.assessment.assessments_data[item]["confirmation"] = {}
                self.assessment.assessments_data[item]["indicators"][f"achieved_{item}"] = False
                self.assessment.assessments_data[item]["confirmation"]["confirm_outcome"] = "confirm"

        # Remove confirmation  from B4.a which  will make B objective incomplete
        self.assessment.assessments_data["B4.a"]["confirmation"]["confirm_outcome"] = ""
        self.assertFalse(self.assessment.is_complete())

    def get_mock_router(self) -> Mock:
        """
        Generate a mock router object with predefined objectives and sections.
        By default it has two objectives: A and B.
        each with four outcomes: A1.a, A1.b, A1.c, A2.a, A2.b, A3.a, A4.a.
        :return: A mocked router object configured with predefined objectives and sections.
        """
        mock_router = Mock()
        objectives = ["A", "B"]

        def get_sections():
            return [{"code": f"{objective}", "title": f"Objective {objective}"} for objective in objectives]

        def get_section(code):
            return {
                "code": f"{code}",
                "title": f"Objective {code}",
                "principles": {
                    "P1": {
                        "outcomes": {
                            outcome: {"code": outcome, "title": f"Outcome {outcome}"}
                            for outcome in [
                                f"{code}1.a",
                                f"{code}1.b",
                                f"{code}1.c",
                                f"{code}2.a",
                                f"{code}2.b",
                                f"{code}3.a",
                                f"{code}4.a",
                            ]
                        }
                    }
                },
            }

        mock_router.get_sections.side_effect = get_sections
        mock_router.get_section.side_effect = get_section
        return mock_router
