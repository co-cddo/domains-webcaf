from django.test import TestCase

from webcaf.webcaf.caf32_field_providers import (
    OutcomeConfirmationFieldProvider,
    OutcomeIndicatorsFieldProvider,
)


class FormProvidersTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.outcome_data = {
            "id": "outcome_1",
            "code": "A1.1",
            "title": "Test Outcome",
            "description": "Test outcome description",
            "indicators": {
                "not-achieved": {
                    "1": "Not achieved indicator 1",
                    "2": "Not achieved indicator 2",
                },
                "partially-achieved": {
                    "3": "Partially achieved indicator 3",
                },
                "achieved": {
                    "4": "Achieved indicator 4",
                    "5": "Achieved indicator 5",
                },
            },
        }

    def test_indicators_provider_metadata(self):
        provider = OutcomeIndicatorsFieldProvider(self.outcome_data)
        metadata = provider.get_metadata()
        self.assertIsInstance(metadata, dict)
        self.assertEqual(metadata["id"], "outcome_1")
        self.assertEqual(metadata["code"], "A1.1")
        self.assertEqual(metadata["title"], "Test Outcome")
        self.assertEqual(metadata["description"], "Test outcome description")

    def test_indicators_provider_field_definitions(self):
        provider = OutcomeIndicatorsFieldProvider(self.outcome_data)
        fields = provider.get_field_definitions()
        self.assertIsInstance(fields, list)
        self.assertEqual(len(fields), 5)
        for field in fields:
            self.assertIn("name", field)
            self.assertIn("label", field)
            self.assertIn("type", field)
            self.assertIn("required", field)
            self.assertEqual(field["type"], "boolean")
            self.assertFalse(field["required"])
        field_names = [field["name"] for field in fields]
        self.assertIn("not-achieved_1", field_names)
        self.assertIn("not-achieved_2", field_names)
        self.assertIn("partially-achieved_3", field_names)
        self.assertIn("achieved_4", field_names)
        self.assertIn("achieved_5", field_names)
        field_labels = {field["name"]: field["label"] for field in fields}
        self.assertEqual(field_labels["not-achieved_1"], "Not achieved indicator 1")
        self.assertEqual(field_labels["achieved_5"], "Achieved indicator 5")

    def test_indicators_provider_layout_structure(self):
        provider = OutcomeIndicatorsFieldProvider(self.outcome_data)
        layout = provider.get_layout_structure()
        self.assertIsInstance(layout, dict)
        self.assertIn("header", layout)
        self.assertIn("groups", layout)
        self.assertEqual(layout["header"]["title"], "A1.1 Test Outcome")
        self.assertEqual(layout["header"]["description"], "Test outcome description")
        self.assertEqual(len(layout["groups"]), 3)
        group_titles = [group["title"] for group in layout["groups"]]
        self.assertIn("Not Achieved", group_titles)
        self.assertIn("Partially Achieved", group_titles)
        self.assertIn("Achieved", group_titles)
        for group in layout["groups"]:
            if group["title"] == "Not Achieved":
                self.assertEqual(len(group["fields"]), 2)
                self.assertIn("not-achieved_1", group["fields"])
                self.assertIn("not-achieved_2", group["fields"])
            elif group["title"] == "Partially Achieved":
                self.assertEqual(len(group["fields"]), 1)
                self.assertIn("partially-achieved_3", group["fields"])
            elif group["title"] == "Achieved":
                self.assertEqual(len(group["fields"]), 2)
                self.assertIn("achieved_4", group["fields"])
                self.assertIn("achieved_5", group["fields"])

    def test_outcome_provider_metadata(self):
        provider = OutcomeConfirmationFieldProvider(self.outcome_data)
        metadata = provider.get_metadata()
        self.assertIsInstance(metadata, dict)
        self.assertEqual(metadata["id"], "outcome_1")
        self.assertEqual(metadata["code"], "A1.1")
        self.assertEqual(metadata["title"], "Test Outcome")

    def test_outcome_provider_field_definitions(self):
        provider = OutcomeConfirmationFieldProvider(self.outcome_data)
        fields = provider.get_field_definitions()
        self.assertIsInstance(fields, list)
        self.assertEqual(len(fields), 2)
        status_field = next(field for field in fields if field["name"] == "status")
        comments_field = next(field for field in fields if field["name"] == "supporting_comments")
        self.assertEqual(status_field["type"], "choice")
        self.assertEqual(status_field["widget"], "radio")
        self.assertTrue(status_field["required"])
        self.assertEqual(status_field["initial"], "confirm")
        choices = [choice[0] for choice in status_field["choices"]]
        self.assertIn("confirm", choices)
        self.assertIn("not_achieved", choices)
        self.assertIn("partially_achieved", choices)
        self.assertEqual(comments_field["type"], "text")
        self.assertTrue(comments_field["required"])
        self.assertIn("widget_attrs", comments_field)
        self.assertEqual(comments_field["widget_attrs"]["rows"], 5)
        self.assertEqual(comments_field["widget_attrs"]["maxlength"], 200)

    def test_outcome_provider_layout_structure(self):
        provider = OutcomeConfirmationFieldProvider(self.outcome_data)
        layout = provider.get_layout_structure()
        self.assertIsInstance(layout, dict)
        self.assertIn("header", layout)
        self.assertIn("groups", layout)
        self.assertEqual(layout["header"]["title"], "A1.1 Outcome")
        self.assertIn("status_message", layout["header"])
        self.assertIn("help_text", layout["header"])
        self.assertEqual(len(layout["groups"]), 2)
        self.assertIn("fields", layout["groups"][0])
        self.assertEqual(layout["groups"][0]["fields"], ["status"])
        self.assertEqual(layout["groups"][1]["title"], "Supporting comments")
        self.assertEqual(layout["groups"][1]["fields"], ["supporting_comments"])

    def test_outcome_provider_without_partially_achieved(self):
        outcome_without_partial = self.outcome_data.copy()
        outcome_without_partial["indicators"] = {
            "not-achieved": self.outcome_data["indicators"]["not-achieved"],
            "achieved": self.outcome_data["indicators"]["achieved"],
        }
        provider = OutcomeConfirmationFieldProvider(outcome_without_partial)
        fields = provider.get_field_definitions()
        status_field = next(field for field in fields if field["name"] == "status")
        choices = [choice[0] for choice in status_field["choices"]]
        self.assertIn("confirm", choices)
        self.assertIn("not_achieved", choices)
        self.assertNotIn("partially_achieved", choices)
