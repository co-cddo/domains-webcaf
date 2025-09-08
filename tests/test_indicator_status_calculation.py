from unittest import TestCase

from parameterized import parameterized

from webcaf.webcaf.caf.util import IndicatorStatusChecker


class TestIndicatorStatusChecker(TestCase):
    @parameterized.expand(
        [
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "achieved_statement_1": "agreed",
                        "achieved_statement_2": "not_true_have_justification",
                        "partially-achieved_statement_2": "not_true_have_justification",
                    },
                },
                "Achieved",
            ),
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "achieved_statement_1": "not_true_no_justification",
                        "achieved_statement_2": "not_true_have_justification",
                    },
                },
                "Not achieved",
            ),
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "achieved_statement_1": "not_true_no_justification",
                        "achieved_statement_2": "not_true_have_justification",
                        "partially-achieved_statement_1": "agreed",
                        "partially-achieved_statement_2": "not_true_have_justification",
                    },
                },
                "Partially achieved",
            ),
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "partially-achieved_statement_1": "not_true_no_justification",
                        "partially-achieved_statement_2": "not_true_have_justification",
                    },
                },
                "Not achieved",
            ),
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "achieved_statement_1": "agreed",
                        "achieved_statement_2": "agreed",
                        "partially-achieved_statement_2": "not_true_have_justification",
                    },
                },
                "Achieved",
            ),
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "achieved_statement_1": "not_true_no_justification",
                        "achieved_statement_2": "agreed",
                        "not_achieved_statement_1": "not_true_no_justification",
                        "not_achieved_statement_2": "not_true_have_justification",
                    },
                },
                "Not achieved",
            ),
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "achieved_statement_1": "not_true_no_justification",
                        "achieved_statement_2": "not_true_have_justification",
                    },
                },
                "Not achieved",
            ),
            ({"confirmation": {"confirm_outcome": None}, "indicators": {}}, "Not achieved"),
        ]
    )
    def test_get_status_for_indicator(self, data, expected_outcome):
        result = IndicatorStatusChecker.get_status_for_indicator(data)
        self.assertEqual(result["outcome_status"], expected_outcome)
