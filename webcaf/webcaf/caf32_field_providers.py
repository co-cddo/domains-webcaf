from abc import ABC, abstractmethod
from typing import Any


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

    @abstractmethod
    def get_layout_structure(self) -> dict:
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

    def get_layout_structure(self) -> dict:
        layout: dict[str, Any] = {
            "header": {
                "title": f"{self.outcome_data.get('code', '')} {self.outcome_data.get('title', '')}",
                "description": self.outcome_data.get("description", ""),
            },
            "groups": [],
            "tabbed": True,
        }

        for level, display_name in [
            ("not-achieved", "Not Achieved"),
            ("partially-achieved", "Partially Achieved"),
            ("achieved", "Achieved"),
        ]:
            if level in self.outcome_data.get("indicators", {}) and self.outcome_data["indicators"][level]:
                field_names = [f"{level}_{id}" for id in self.outcome_data["indicators"][level].keys()]

                if field_names:
                    layout["groups"].append({"title": display_name, "fields": field_names})

        return layout


class OutcomeConfirmationFieldProvider(FieldProvider):
    def __init__(self, outcome_data: dict):
        self.outcome_data = outcome_data

    def get_metadata(self) -> dict:
        return {"code": self.outcome_data.get("code", ""), "title": self.outcome_data.get("title", "")}

    def get_field_definitions(self) -> list[dict]:
        # Choices will be updated dynamically on form init
        # This is needed so that we can change the label of the override value
        # depending on the current values given by the user
        # But the keys for the status will still remain the same as "confirm" and "override"
        status_choices = [("confirm", ""), ("override", "")]

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

    def get_layout_structure(self) -> dict:
        return {
            "header": {
                "title": f"{self.outcome_data.get('code', '')} {self.outcome_data.get('title', '')} Outcome",
                "status_message": "<p class='govuk-body'><strong>Status: {{ outcome_status }}</strong></p>",
                "help_text": "<p class='govuk-body'>{{outcome_message}}</p>",
            },
            "groups": [
                {"fields": ["status", "overriding_comments"]},
                {"title": "Supporting comments", "fields": ["supporting_comments"]},
            ],
            "tabbed": False,
        }
