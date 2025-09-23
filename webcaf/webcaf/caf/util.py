from typing import Any, Dict, Literal, Optional

from webcaf.webcaf.abcs import FrameworkRouter
from webcaf.webcaf.models import Assessment


class IndicatorStatusChecker:
    @staticmethod
    def get_router(framework) -> FrameworkRouter:
        from webcaf.webcaf.frameworks import routers

        return routers[framework]

    @staticmethod
    def get_status_for_indicator(
        data: Dict[str, Any], framework: Literal["caf32", "caf40"] | None = None
    ) -> Dict[str, Optional[str]]:
        """
        Get the status for an indicator based on the provided data and framework.
        Not achieved status is returned if if at least one not achieved statement is present or none of
        achieved or partially achieved statements are present.
        The user can get Achieved status if all achieved statements are present and none of not achieved statements are present.
        The user can get Partially achieved status if all Partially achieved statements are present and none of not achieved statements are present..

        :param data: Dictionary containing indicators.
        :type data: Dict[str, Any]
        :param framework: The framework to use. Defaults to "caf32".
        :type framework: Literal["caf32", "caf40"] | None

        :return: A dictionary with the outcome status and its corresponding message.
        :rtype: Dict[str, Optional[str]]
        """
        indicators = (data or {}).get("indicators") or {}
        if not framework:
            framework = "caf32"
        router = IndicatorStatusChecker.get_router(framework)

        # Helper: filter only primary indicator keys (ignore any *_comment variants)
        def primary_items_with_prefix(prefix: str):
            return [(k, v) for k, v in indicators.items() if k.startswith(prefix) and not k.endswith("_comment")]

        def generate_key(indicator_items: list[tuple[str, Any]]):
            """
            Generates a key based on the provided indicator items.
            :param indicator_items: List of tuples where each tuple contains an identifier and a value. The function evaluates these values to determine the key.
            :return: A string indicating whether all values are present, some values are missing, or no values are provided.
            """
            if not indicator_items or all(not v for _, v in indicator_items):
                return "none"
            elif all(v for _, v in indicator_items):
                return "all"
            else:
                return "some"

        achieved_items = primary_items_with_prefix("achieved_")
        partial_items = primary_items_with_prefix("partially-achieved_")
        not_achieved_items = primary_items_with_prefix("not-achieved_")

        achieved_key = generate_key(achieved_items)
        partially_achieved_key = generate_key(partial_items)
        not_achieved_key = generate_key(not_achieved_items)

        return router.framework["assessment-rules"][  # type: ignore
            f"{achieved_key}_{partially_achieved_key}_{not_achieved_key}"
        ]

    @staticmethod
    def get_when_the_status_changed(assessment: Assessment, indicator_id: str, status: str) -> Assessment | None:
        """
        Provides details about when the status of an indicator within an assessment has changed.
        Go through the assessment history and find the timestamp of the first occurrence of the given status for the given indicator.
        :param assessment: Assessment object containing all indicators and their statuses.
        :param indicator_id: Unique identifier for the indicator whose status change is being tracked.
        :param status: New status of the indicator after the change.

        :return: Timestamp indicating when the status change occurred.
        """
        historical_assessments = assessment.history.all()

        # Filter historical assessments where the indicator's status has changed

        filtered_history = []
        for i in range(len(historical_assessments) - 1):
            prev_outcome = (
                historical_assessments[i]
                .assessments_data.get(indicator_id, {})
                .get("confirmation", {})
                .get("confirm_outcome_status", "")
            )
            next_outcome = (
                historical_assessments[i + 1]
                .assessments_data.get(indicator_id, {})
                .get("confirmation", {})
                .get("confirm_outcome_status", "")
            )
            # We get the records in reverse order, so we need to check the next outcome first
            if prev_outcome == status and next_outcome != status:
                filtered_history.append(historical_assessments[i])

        # If there are no matching statuses, return None
        if not filtered_history:
            return None

        # Return the timestamp of the first occurrence
        return filtered_history[0]

    @classmethod
    def indicator_min_profile_requirement_met(
        cls, assessment: Assessment, principal_id: str, indicator_id: str, status: str
    ) -> str:
        """
        Checks if the minimum profile requirement for the given indicator is met.
        :param assessment:
        :param principal_id:
        :param indicator_id:
        :param status:
        :return:
        """

        principal = assessment.get_router().get_section(principal_id[0])["principles"][principal_id]  # type: ignore
        outcome = principal["outcomes"][indicator_id]
        min_profile_requirement = outcome.get("min_profile_requirement")
        profile_scores = {
            "achieved": 3,
            "partially_achieved": 2,
            "not_achieved": 1,
        }
        if min_profile_requirement:
            if status:
                return (
                    "Yes"
                    if profile_scores[cls.status_to_key(status)]
                    >= profile_scores[cls.status_to_key(min_profile_requirement[assessment.caf_profile])]
                    else "Not met"
                )
            else:
                return "Not met"
        else:
            return "Yes"

    @staticmethod
    def status_to_key(status: str) -> str:
        """
        Converts a status string to its corresponding key.

        :param status: Status in string format. Possible values are "Achieved", "Partially achieved", and "Not achieved".
        :return: Key for the given status. For example, "Achieved" is converted to "achieved".

        :raises ValueError: If an invalid status value is provided.
        """
        if status == "Achieved":
            status_key = "achieved"
        elif status == "Partially achieved":
            status_key = "partially_achieved"
        elif status == "Not achieved":
            status_key = "not_achieved"
        else:
            raise ValueError(f"Invalid status: {status}")
        return status_key

    @staticmethod
    def key_to_status(status: str) -> str:
        """
        Converts a string representation of a status into a more formal key.

        :param status:
        :return:
        """
        if status == "achieved":
            status_key = "Achieved"
        elif status == "partially_achieved":
            status_key = "Partially achieved"
        elif status == "not_achieved":
            status_key = "Not achieved"
        else:
            raise ValueError(f"Invalid key: {status}")
        return status_key
