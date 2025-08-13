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
            "id": self.outcome_data.get("id", ""),
        }

    def get_field_definitions(self) -> list[dict]:
        fields = []
        justifications = {
            "not-achieved": [
                ("agreed", "This does apply to my system or organisation and I have justifications", True),
                (
                    "not_true_have_justification",
                    "This does apply to my system or organisation, but I have no justifications",
                    False,
                ),
                ("not_true_no_justification", "This does not apply to my system or organisation", False),
            ],
            "achieved": [
                ("agreed", "True", False),
                ("not_true_have_justification", "Not true, but I do have justifications", True),
                ("not_true_no_justification", "Not true, and I have no justifications", False),
            ],
            "partially-achieved": [
                ("agreed", "True", False),
                ("not_true_have_justification", "Not true, but I do have justifications", True),
                ("not_true_no_justification", "Not true, and I have no justifications", False),
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
