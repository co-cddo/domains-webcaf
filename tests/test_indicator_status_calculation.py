from unittest import TestCase

from parameterized import parameterized

from webcaf.webcaf.caf.util import IndicatorStatusChecker


class TestIndicatorStatusChecker(TestCase):
    def setUp(self):
        self.maxDiff = None

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
                {
                    "outcome_status": "Achieved",
                    "outcome_status_message": "You have received this status because you have selected all achieved IGP statements.",
                },
            ),
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "achieved_statement_1": False,
                        "achieved_statement_2": True,
                    },
                },
                {
                    "outcome_status": "Not achieved",
                    "outcome_status_message": "You have received this status because not all of the achieved or partially achieved IGP statements have been selected. If you believe this is incorrect, you should review the IGP statements again and select all that are appropriate, providing comments where alternative controls or exemptions are in place.",
                },
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
                {
                    "outcome_status": "Partially achieved",
                    "outcome_status_message": "You have received this status because you have selected all partially achieved IGP statements.",
                },
            ),
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "partially-achieved_statement_1": False,
                        "partially-achieved_statement_2": True,
                    },
                },
                {
                    "outcome_status": "Not achieved",
                    "outcome_status_message": "You have received this status because not all of the achieved or partially achieved IGP statements have been selected. If you believe this is incorrect, you should review the IGP statements again and select all that are appropriate, providing comments where alternative controls or exemptions are in place.",
                },
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
                {
                    "outcome_status": "Achieved",
                    "outcome_status_message": "You have received this status because you have selected all achieved IGP statements.",
                },
            ),
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "achieved_statement_1": False,
                        "achieved_statement_2": True,
                        "not-achieved_statement_1": False,
                        "not-achieved_statement_2": True,
                    },
                },
                {
                    "outcome_status": "Not achieved",
                    "outcome_status_message": "You have received this status because you have selected one or more not achieved IGP statements.",
                },
            ),
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "achieved_statement_1": False,
                        "achieved_statement_2": True,
                    },
                },
                {
                    "outcome_status": "Not achieved",
                    "outcome_status_message": "You have received this status because not all of the achieved or partially achieved IGP statements have been selected. If you believe this is incorrect, you should review the IGP statements again and select all that are appropriate, providing comments where alternative controls or exemptions are in place.",
                },
            ),
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "not-achieved_statement_1": True,
                        "not-achieved_statement_2": True,
                    },
                },
                {
                    "outcome_status": "Not achieved",
                    "outcome_status_message": "You have received this status because you have selected one or more not achieved IGP statements.",
                },
            ),
            (
                {
                    "confirmation": {"confirm_outcome": None},
                    "indicators": {
                        "not-achieved_statement_1": True,
                        "not-achieved_statement_2": False,
                    },
                },
                {
                    "outcome_status": "Not achieved",
                    "outcome_status_message": "You have received this status because you have selected one or more not achieved IGP statements.",
                },
            ),
            (
                {"confirmation": {"confirm_outcome": None}, "indicators": {}},
                {
                    "outcome_status": "Not achieved",
                    "outcome_status_message": "You have received this status because not all of the achieved or partially achieved IGP statements have been selected. If you believe this is incorrect, you should review the IGP statements again and select all that are appropriate, providing comments where alternative controls or exemptions are in place.",
                },
            ),
        ]
    )
    def test_get_status_for_indicator(self, data, expected_outcome):
        result = IndicatorStatusChecker.get_status_for_indicator(data)
        self.assertEqual(result, expected_outcome)
