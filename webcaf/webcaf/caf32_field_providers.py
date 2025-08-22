from abc import ABC, abstractmethod


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


class OutcomeIndicatorsFieldProvider(FieldProvider):
    def __init__(self, outcome_data: dict):
        self.outcome_data = outcome_data

    def get_metadata(self) -> dict:
        return {
            "code": self.outcome_data.get("code", ""),
            "title": self.outcome_data.get("title", ""),
            "description": self.outcome_data.get("description", ""),
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

        return fields


class OutcomeConfirmationFieldProvider(FieldProvider):
    def __init__(self, outcome_data: dict):
        self.outcome_data = outcome_data

    def get_metadata(self) -> dict:
        return {"code": self.outcome_data.get("code", ""), "title": self.outcome_data.get("title", "")}

    def get_field_definitions(self) -> list[dict]:
        status_choices = [("confirm", "Confirm"), ("override", "Override")]
        if (
            "partially-achieved" in self.outcome_data.get("indicators", {})
            and self.outcome_data["indicators"]["partially-achieved"]
        ):
            status_choices.append(("partially_achieved", "Change to Partially Achieved"))

        return [
            {
                "name": "status",
                "type": "choice",
                "choices": status_choices.copy(),
                "required": True,
                "initial": "confirm",
                "label": "",
                "widget": "radio",
            },
            {
                "name": "override_comments",
                "type": "text",
                "label": "Explain why you've changed the outcome.",
                "required": False,
                "widget_attrs": {
                    "rows": 5,
                    "class": "govuk-textarea overriding_comments",
                    "maxlength": 200,
                },
            },
            {
                "name": "partially_achieved_comments",
                "type": "text",
                "label": "Explain why you've changed the outcome.",
                "required": False,
                "widget_attrs": {
                    "rows": 5,
                    "class": "govuk-textarea partially_achieved_comments",
                    "maxlength": 200,
                },
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
