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
                        "achieved_statement_1": True,
                        "achieved_statement_2": True,
                        "partially-achieved_statement_2": True,
                    },
                },
                "Achieved",
            ),
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "achieved_statement_1": False,
                        "achieved_statement_2": True,
                    },
                },
                "Not achieved",
            ),
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "achieved_statement_1": False,
                        "achieved_statement_2": True,
                        "partially-achieved_statement_1": True,
                        "partially-achieved_statement_2": True,
                    },
                },
                "Partially achieved",
            ),
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "partially-achieved_statement_1": False,
                        "partially-achieved_statement_2": True,
                    },
                },
                "Not achieved",
            ),
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "achieved_statement_1": True,
                        "achieved_statement_2": True,
                        "partially-achieved_statement_2": True,
                    },
                },
                "Achieved",
            ),
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "achieved_statement_1": False,
                        "achieved_statement_2": True,
                        "not_achieved_statement_1": False,
                        "not_achieved_statement_2": True,
                    },
                },
                "Not achieved",
            ),
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "achieved_statement_1": False,
                        "achieved_statement_2": True,
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
