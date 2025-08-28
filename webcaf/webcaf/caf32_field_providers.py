from abc import ABC, abstractmethod
from collections import namedtuple


class FieldProvider(ABC):
    """
    An interface for providing specifications for form fields, based on an
    assessment framework. These are consumed by the form factory.

    The purpose of this class is to separate the form factory from the
    specifics of the assessment framework.
    """

    @abstractmethod
    def get_metadata(self) -> dict:
        pass

    @abstractmethod
    def get_field_definitions(self) -> list[dict]:
        pass


Choice = namedtuple("Choice", ["value", "label", "needs_justification_text"])


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
        justifications = {
            "not-achieved": [
                Choice("agreed", "This does apply to my system or organisation and I have justifications", True),
                Choice(
                    "not_true_have_justification",
                    "This does apply to my system or organisation, but I have no justifications",
                    False,
                ),
                Choice("not_true_no_justification", "This does not apply to my system or organisation", False),
            ],
            "achieved": [
                Choice("agreed", "True", False),
                Choice("not_true_have_justification", "Not true, but I do have justifications", True),
                Choice("not_true_no_justification", "Not true, and I have no justifications", False),
            ],
            "partially-achieved": [
                Choice("agreed", "True", False),
                Choice("not_true_have_justification", "Not true, but I do have justifications", True),
                Choice("not_true_no_justification", "Not true, and I have no justifications", False),
            ],
        }
        for level in ["not-achieved", "partially-achieved", "achieved"]:
            if level in self.outcome_data.get("indicators", {}):
                for indicator_id, indicator_text in self.outcome_data["indicators"][level].items():
                    fields.append(
                        {
                            "name": f"{level}_{indicator_id}",
                            "label": indicator_text["description"],
                            "type": "choice_with_justifications",
                            "required": True,
                            "choices": justifications[level],
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
            Choice("confirm", "Confirm", False),
            Choice("change_to_achieved", "Change to Achieved", True),
            Choice("change_to_not_achieved", "Change to Not Achieved", True),
        ]

        if (
            "partially-achieved" in self.outcome_data.get("indicators", {})
            and self.outcome_data["indicators"]["partially-achieved"]
        ):
            status_choices.append(Choice("change_to_partially_achieved", "Change to Partially Achieved", True))

        return [
            {
                "name": "status",
                "type": "choice_with_justifications",
                "choices": status_choices,
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
                    "maxlength": 200,
                },
            },
        ]
