import unittest

from parameterized import parameterized

from webcaf.webcaf.status_calculator import calculate_outcome_status


def name_func(testcase_func, param_num, param):
    return f"{testcase_func.__name__}_{param_num}_expected_status_{param.args[1]}_override_status_{param.args[3]}"


class TestCalculateOutcomeStatus(unittest.TestCase):
    @parameterized.expand(
        [
            # All achieved_* values are "agreed" -> Achieved
            (
                {
                    "achieved_statement_one": "agreed",
                    "achieved_statement_two": "agreed",
                    # comments should be ignored
                    "achieved_statement_one_comment": "some note",
                    # unrelated keys should be ignored
                    "something_else": "foo",
                },
                "Achieved",
                None,
                None,
            ),
            # Empty indicators -> Not achieved (no achieved_ keys yields empty set)
            ({}, "Not achieved", {}, None),
            # Mixed values -> Not achieved
            (
                {
                    "achieved_statement_one": "agreed",
                    "achieved_statement_two": "not agreed",
                },
                "Not achieved",
                None,
                None,
            ),
            # Single achieved_* but not agreed -> Not achieved
            (
                {
                    "achieved_statement_one": "not agreed",
                },
                "Not achieved",
                None,
                None,
            ),
            # Multiple achieved_* all the same but not "agreed" -> Not achieved
            (
                {
                    "achieved_statement_one": "partially",
                    "achieved_statement_two": "partially",
                },
                "Not achieved",
                None,
                None,
            ),
            #     Test override status
            (
                {
                    "achieved_statement_one": "agreed",
                    "achieved_statement_two": "not_true_have_justification",
                },
                "Not achieved",
                {
                    "confirm_outcome": "change_to_achieved",
                    "summary_outline": "fdgdafgdfgf",
                    "change_to_achieved_detail": "fdgdfagdfgdfgfd",
                    "change_to_not_achieved_detail": "",
                    "change_to_partially_achieved_detail": "",
                },
                "Achieved",
            ),
            (
                {
                    "achieved_statement_one": "not_true_have_justification",
                    "achieved_statement_two": "not_true_have_justification",
                },
                "Not achieved",
                {
                    "confirm_outcome": "change_to_achieved",
                    "summary_outline": "fdgdafgdfgf",
                    "change_to_achieved_detail": "fdgdfagdfgdfgfd",
                    "change_to_not_achieved_detail": "",
                    "change_to_partially_achieved_detail": "",
                },
                "Achieved",
            ),
            (
                {
                    "achieved_statement_one": "not_true_have_justification",
                    "achieved_statement_two": "not_true_have_justification",
                },
                "Not achieved",
                {
                    "confirm_outcome": "change_to_partially_achieved",
                    "summary_outline": "fdgdafgdfgf",
                    "change_to_achieved_detail": "fdgdfagdfgdfgfd",
                    "change_to_not_achieved_detail": "",
                    "change_to_partially_achieved_detail": "",
                },
                "Partially achieved",
            ),
        ],
        name_func=name_func,
    )
    def test_calculate_outcome_status(self, indicators, expected_outcome, confirmation, expected_override):
        """
        Calculates the outcome status and override status based on provided indicators.

        :param indicators: Dictionary containing achieved statements with their statuses.
        :type indicators: dict

        :param expected_outcome: Expected outcome status ("Achieved", "Not achieved", or "Partially achieved").
        :type expected_outcome: str

        :param confirmation: Confirmation dictionary that may include override details.
        :type confirmation: dict, optional

        :param expected_override: Expected override status ("Achieved", "Not achieved", or "Partially achieved").
        :type expected_override: str, optional
        """
        result = calculate_outcome_status(confirmation=confirmation or {}, indicators=indicators)
        assert result["outcome_status"] == expected_outcome
        assert result["override_status"] == expected_override

    def test_ignores_comment_keys_and_unrelated_keys_for_achieved_set(self):
        indicators = {
            "achieved_a": "agreed",
            "achieved_b": "agreed",
            "achieved_a_comment": "ignored",
            "not_achieved_c": "should be ignored as it doesn't start with achieved_",
        }
        result = calculate_outcome_status(confirmation={}, indicators=indicators)
        assert result == {"outcome_status": "Achieved", "override_status": None}
