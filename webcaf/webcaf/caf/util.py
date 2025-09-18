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
        Rules:
          - "achieved" if ALL indicator keys starting with "achieved_" are "agreed"
          - else "partially_achieved" if ALL indicator keys starting with "partially-achieved_" are "agreed"
          - else "not_Achieved" unless all agreed with justification provided otherwise revert to "achieved"
        Only non-comment indicator keys are considered (ignore keys ending with "_comment") for achieved and partially_achieved tests.
        """
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
                # Check all not-achieved are ticked with comments, which makes the satus achieved
                not_achieved_indicators = primary_items_with_prefix("not-achieved_")
                # Make sure all are ticked
                if not_achieved_indicators and all(v for _, v in not_achieved_indicators):
                    not_achieved_comments = [
                        (k, v and v.strip() != "")
                        for k, v in indicators.items()
                        if k.startswith("not-achieved_") and k.endswith("_comment")
                    ]
                    if (
                        not_achieved_comments
                        and len(not_achieved_comments) == len(not_achieved_indicators)
                        and all(v for _, v in not_achieved_comments)
                    ):
                        outcome_status = "Achieved"
                    else:
                        outcome_status = "Not achieved"
                else:
                    outcome_status = "Not achieved"

        return {
            "outcome_status": outcome_status,
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
