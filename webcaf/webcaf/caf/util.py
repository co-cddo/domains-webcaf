from typing import Any, Dict, Optional


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
        if achieved_items and all(v == "agreed" for _, v in achieved_items):
            outcome_status = "Achieved"
        else:
            # Determine partially achieved
            if partial_items and all(v == "agreed" for _, v in partial_items):
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
