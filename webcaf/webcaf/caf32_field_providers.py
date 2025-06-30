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
            "id": self.outcome_data.get("id", ""),
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
                comment_checkbox_name = f"{level}_comment"
                comment_textarea_name = f"{level}_comment_details"
                fields.append(
                    {
                        "name": comment_checkbox_name,
                        "label": "Make a comment about a statement",
                        "type": "boolean",
                        "required": False,
                    }
                )
                fields.append(
                    {
                        "name": comment_textarea_name,
                        "label": "Provide your comment",
                        "type": "text",
                        "required": False,
                        "widget_attrs": {
                            "rows": 3,
                            "class": "govuk-textarea",
                            "maxlength": 500,
                        },
                    }
                )
                fields.append(
                    {
                        "name": f"{level}_none_of_the_above",
                        "label": "None of the above",
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
        }

        for level, display_name in [
            ("not-achieved", "Not Achieved"),
            ("partially-achieved", "Partially Achieved"),
            ("achieved", "Achieved"),
        ]:
            if level in self.outcome_data.get("indicators", {}) and self.outcome_data["indicators"][level]:
                field_names = [f"{level}_{id}" for id in self.outcome_data["indicators"][level].keys()]
                field_names.append(f"{level}_comment")
                field_names.append(f"{level}_none_of_the_above")

                if field_names:
                    layout["groups"].append({"title": display_name, "fields": field_names})

        return layout


class TabbedOutcomeIndicatorsFieldProvider(OutcomeIndicatorsFieldProvider):
    """
    A field provider that structures outcome indicators into tabs.
    Extends OutcomeIndicatorsFieldProvider but changes the layout structure
    to use the tabs component from crispy-forms-gds.

    Each achievement level (not-achieved, partially-achieved, achieved)
    will be displayed as a separate tab.
    """

    def get_layout_structure(self) -> dict:
        """
        Override the layout structure to use tabs instead of sections.
        Each tab will contain one achievement level's indicators.
        """
        layout: dict[str, Any] = {
            "header": {
                "title": f"{self.outcome_data.get('code', '')} {self.outcome_data.get('title', '')}",
                "description": self.outcome_data.get("description", ""),
            },
            "use_tabs": True,
            "tabs": [],
            "button_text": "Save and Continue",
        }

        for level, display_name in [
            ("not-achieved", "Not Achieved"),
            ("partially-achieved", "Partially Achieved"),
            ("achieved", "Achieved"),
        ]:
            if level in self.outcome_data.get("indicators", {}) and self.outcome_data["indicators"][level]:
                field_names = [f"{level}_{id}" for id in self.outcome_data["indicators"][level].keys()]
                comment_field_names = [f"{level}_comment", f"{level}_comment_details"]
                field_names.extend(comment_field_names)
                field_names.append(f"{level}_none_of_the_above")

                if field_names:
                    tab = {
                        "id": f"tab-{level}",
                        "label": display_name,
                        "fields": field_names,
                    }
                    layout["tabs"].append(tab)

        return layout


class OutcomeConfirmationFieldProvider(FieldProvider):
    def __init__(self, outcome_data: dict):
        self.outcome_data = outcome_data

    def get_metadata(self) -> dict:
        return {
            "code": self.outcome_data.get("code", ""),
            "title": self.outcome_data.get("title", ""),
            "id": self.outcome_data.get("id", ""),
        }

    def get_field_definitions(self) -> list[dict]:
        status_choices = [
            ("confirm", "Confirm"),
            ("not_achieved", "Change to Not achieved"),
        ]

        if (
            "partially-achieved" in self.outcome_data.get("indicators", {})
            and self.outcome_data["indicators"]["partially-achieved"]
        ):
            status_choices.append(("partially_achieved", "Change to Partially Achieved"))

        return [
            {
                "name": "status",
                "type": "choice",
                "choices": status_choices,
                "required": True,
                "initial": "confirm",
                "label": "",
                "widget": "radio",
            },
            {
                "name": "supporting_comments",
                "type": "text",
                "label": "You must provide here comments that support your outcome.",
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
                "title": f"{self.outcome_data.get('code', '')} Outcome",
                "status_message": "<p class='govuk-body'><strong>Status: Achieved</strong></p>",
                "help_text": "<p class='govuk-body'>Message to be changed</p>",
            },
            "groups": [{"fields": ["status"]}, {"title": "Supporting comments", "fields": ["supporting_comments"]}],
        }
