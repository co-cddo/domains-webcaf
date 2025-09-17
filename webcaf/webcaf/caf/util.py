from typing import Any, Dict, Optional

from webcaf.webcaf.models import Assessment


class IndicatorStatusChecker:
    @staticmethod
    def get_status_for_indicator(data: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """
        Given an assessment entry shaped like:
        {
            "confirmation": {...},
            "indicators": {...}
        }
        compute:
          - outcome_status: "achieved" | "partially_achieved" | "not_achieved"
          - override_status: value of confirmation["confirm_outcome"] or None
          - outcome_status_text: ""
        Rules:
          - "achieved" if ALL indicator keys starting with "achieved_" are "agreed"
          - else "partially_achieved" if ALL indicator keys starting with "partially-achieved_" are "agreed"
          - else "not_Achieved"
        Only non-comment indicator keys are considered (ignore keys ending with "_comment").
        """
        confirmation = (data or {}).get("confirmation") or {}
        indicators = (data or {}).get("indicators") or {}

        # Helper: filter only primary indicator keys (ignore any *_comment variants)
        def primary_items_with_prefix(prefix: str):
            return [(k, v) for k, v in indicators.items() if k.startswith(prefix) and not k.endswith("_comment")]

        achieved_items = primary_items_with_prefix("achieved_")
        partial_items = primary_items_with_prefix("partially-achieved_")

        # Determine achieved
        outcome_status: str
        if achieved_items and all(v for _, v in achieved_items):
            outcome_status = "Achieved"
        else:
            # Determine partially achieved
            if partial_items and all(v for _, v in partial_items):
                outcome_status = "Partially achieved"
            else:
                outcome_status = "Not achieved"

        # - "confirm" -> None
        # - "change_to_xxx" -> "xxx"
        raw_override = confirmation.get("confirm_outcome")
        if raw_override == "confirm":
            override_status: Optional[str] = None
        elif isinstance(raw_override, str) and raw_override.startswith("change_to_"):
            override_status = raw_override[len("change_to_") :].replace("_", " ").capitalize()
        else:
            override_status = None

        outcome_status_text_map = {
            "Achieved": """You selected 'true' to all the achieved statements.
Please confirm you agree with this status, or you can choose to change the outcome.""",
            "Not achieved": """You selected 'not true' to at least one of the achieved or partially achieved statements.
Please confirm you agree with this status, or you can choose to change the outcome.""",
            "Partially achieved": """You selected 'partially achieved'""",
        }
        return {
            "outcome_status": outcome_status,
            "override_status": override_status,
            "outcome_status_text": outcome_status_text_map[outcome_status],
        }

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
        status_key = IndicatorStatusChecker.status_to_key(status)

        filtered_history = []
        for i in range(len(historical_assessments) - 1):
            prev_outcome = (
                historical_assessments[i]
                .assessments_data.get(indicator_id, {})
                .get("confirmation", {})
                .get("confirm_outcome", "")
            )
            next_outcome = (
                historical_assessments[i + 1]
                .assessments_data.get(indicator_id, {})
                .get("confirmation", {})
                .get("confirm_outcome", "")
            )
            # We get the records in reverse order, so we need to check the next outcome first
            if prev_outcome == f"change_to_{status_key}" and next_outcome != f"change_to_{status_key}":
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

    @classmethod
    def get_justification_text(cls, assessments_data: dict[str, Any], indicator_id: str) -> str | None:
        """
        Returns the justification text for a given indicator based on assessment data.

        :param assessments_data: Dictionary containing assessment data.
        :type assessments_data: dict

        :param indicator_id: Identifier of the indicator to retrieve justification text for.
        :type indicator_id: int

        :return: Justification text if found, otherwise None.
        :rtype: str | None
        """
        confirmation = assessments_data.get(indicator_id, {}).get("confirmation", {})
        if confirm_outcome := confirmation.get("confirm_outcome"):
            if confirm_outcome.startswith("change_to_"):
                return confirmation.get(f"confirm_outcome_{confirm_outcome}_comment")
        return None
