from collections import namedtuple

from webcaf.webcaf.abcs import FieldProvider

AchievementChoice = namedtuple("AchievementChoice", ["value", "label", "needs_justification_text"])

MAX_WORD_COUNT = 1500


class OutcomeIndicatorsFieldProvider(FieldProvider):
    def __init__(self, outcome_data: dict):
        self.outcome_data = outcome_data

    def get_metadata(self) -> dict:
        return {
            "code": self.outcome_data.get("code", ""),
            "title": self.outcome_data.get("title", ""),
            "description": self.outcome_data.get("description", ""),
            "id": self.outcome_data.get("code", ""),
        }

    def get_field_definitions(self) -> list[dict]:
        fields = []
        for level in ["not-achieved", "partially-achieved", "achieved"]:
            if level in self.outcome_data.get("indicators", {}):
                for indicator_id, indicator_text in self.outcome_data["indicators"][level].items():
                    fields.append(
                        {
                            "name": f"{level}_{indicator_id}",
                            "label": indicator_text["description"],
                            "type": "boolean",
                            "required": False,
                        }
                    )
                    # Not achieved choices have an extra justification field
                    if level in ["not-achieved"]:
                        fields.append(
                            {
                                "name": f"{level}_{indicator_id}_comment",
                                "label": "Tell us your justification",
                                "type": "text",
                                "required": False,
                                "widget_attrs": {
                                    "rows": 5,
                                    "class": "govuk-textarea",
                                    "max_words": MAX_WORD_COUNT,
                                },
                            }
                        )

        return fields


class OutcomeConfirmationFieldProvider(FieldProvider):
    def __init__(self, outcome_data: dict):
        self.outcome_data = outcome_data

    def get_metadata(self) -> dict:
        return {"code": self.outcome_data.get("code", ""), "title": self.outcome_data.get("title", "")}

    def get_field_definitions(self) -> list[dict]:
        # This is the full list of options for the status field.
        # The irrelevant ones are filtered out in the view as the options are
        # dependent on the indicator outcome answers
        status_choices = [
            AchievementChoice("confirm", "Confirm", False),
            AchievementChoice("change_to_achieved", "Change to Achieved", True),
            AchievementChoice("change_to_not_achieved", "Change to Not Achieved", True),
        ]

        if (
            "partially-achieved" in self.outcome_data.get("indicators", {})
            and self.outcome_data["indicators"]["partially-achieved"]
        ):
            status_choices.append(
                AchievementChoice("change_to_partially_achieved", "Change to Partially Achieved", True)
            )

        return [
            {
                "name": "confirm_outcome",
                "type": "choice",
                "choices": [
                    (
                        choice.value,
                        choice.label,
                    )
                    for choice in status_choices
                ],
                "required": True,
                "label": "",
            },
            {
                "name": "supporting_comments",
                "type": "text",
                "label": "Please write a short summary outlining how you worked towards achieving this outcome.",
                "required": True,
                "widget_attrs": {
                    "rows": 5,
                    "class": "govuk-textarea",
                    "max_words": MAX_WORD_COUNT,
                },
            },
        ] + [
            # Add justification_text for the confirmation choice list
            {
                "name": f"confirm_outcome_{status_choice.value}_comment",
                "label": "Tell us your justifications",
                "type": "text",
                "required": False,
                "widget_attrs": {
                    "rows": 5,
                    "class": "govuk-textarea",
                    "max_words": MAX_WORD_COUNT,
                },
            }
            for status_choice in status_choices
            if status_choice.needs_justification_text
        ]
