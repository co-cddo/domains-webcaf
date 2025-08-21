import os

import yaml
from django.test import TestCase

from webcaf.webcaf.caf32_field_providers import (
    OutcomeConfirmationFieldProvider,
    OutcomeIndicatorsFieldProvider,
)


class FormProvidersTestCase(TestCase):
    def setUp(self):
        """Set up test data from actual YAML fixture file"""
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "caf-v3.2-dummy.yaml")
        with open(fixture_path, "r") as file:
            framework_data = yaml.safe_load(file)
        self.outcome_data = framework_data["objectives"]["A"]["principles"]["A1"]["outcomes"]["A1.a"]
        self.outcome_data["id"] = "A1.a"

    def test_indicators_provider_metadata(self):
        provider = OutcomeIndicatorsFieldProvider(self.outcome_data)
        metadata = provider.get_metadata()
        self.assertIsInstance(metadata, dict)
        self.assertEqual(metadata["code"], "A1.a")
        self.assertEqual(metadata["title"], "Monitoring Coverage")
        self.assertEqual(
            metadata["description"], "Monitoring data sources allow for timely identification of security events."
        )

    def test_indicators_provider_field_definitions(self):
        provider = OutcomeIndicatorsFieldProvider(self.outcome_data)
        fields = provider.get_field_definitions()
        self.assertIsInstance(fields, list)
        self.assertEqual(len(fields), 14)
        for field in fields:
            self.assertIn("name", field)
            self.assertIn("label", field)
            self.assertIn("type", field)
            self.assertIn("required", field)
            self.assertEqual(field["type"], "boolean")
            self.assertFalse(field["required"])
        field_names = [field["name"] for field in fields]
        self.assertIn("not-achieved_A1.a.1", field_names)
        self.assertIn("not-achieved_A1.a.4", field_names)
        self.assertIn("partially-achieved_A1.a.5", field_names)
        self.assertIn("partially-achieved_A1.a.8", field_names)
        self.assertIn("achieved_A1.a.9", field_names)
        self.assertIn("achieved_A1.a.14", field_names)
        field_labels = {field["name"]: field["label"] for field in fields}
        self.assertEqual(field_labels["not-achieved_A1.a.1"], "Security operation data is not collected.")
        self.assertEqual(field_labels["achieved_A1.a.14"], "New systems are evaluated as monitoring data sources.")

    def test_indicators_provider_layout_structure(self):
        provider = OutcomeIndicatorsFieldProvider(self.outcome_data)
        layout = provider.get_layout_structure()
        self.assertIsInstance(layout, dict)
        self.assertIn("header", layout)
        self.assertIn("groups", layout)
        self.assertEqual(layout["header"]["title"], "A1.a Monitoring Coverage")
        self.assertEqual(
            layout["header"]["description"],
            "Monitoring data sources allow for timely identification of security events.",
        )
        self.assertEqual(len(layout["groups"]), 3)
        group_titles = [group["title"] for group in layout["groups"]]
        self.assertIn("Not Achieved", group_titles)
        self.assertIn("Partially Achieved", group_titles)
        self.assertIn("Achieved", group_titles)
        for group in layout["groups"]:
            if group["title"] == "Not Achieved":
                self.assertEqual(len(group["fields"]), 4)
                self.assertIn("not-achieved_A1.a.1", group["fields"])
                self.assertIn("not-achieved_A1.a.4", group["fields"])
            elif group["title"] == "Partially Achieved":
                self.assertEqual(len(group["fields"]), 4)
                self.assertIn("partially-achieved_A1.a.5", group["fields"])
                self.assertIn("partially-achieved_A1.a.8", group["fields"])
            elif group["title"] == "Achieved":
                self.assertEqual(len(group["fields"]), 6)
                self.assertIn("achieved_A1.a.9", group["fields"])
                self.assertIn("achieved_A1.a.14", group["fields"])

    def test_outcome_provider_metadata(self):
        provider = OutcomeConfirmationFieldProvider(self.outcome_data)
        metadata = provider.get_metadata()
        self.assertIsInstance(metadata, dict)
        self.assertEqual(metadata["code"], "A1.a")
        self.assertEqual(metadata["title"], "Monitoring Coverage")

    def test_outcome_provider_field_definitions(self):
        provider = OutcomeConfirmationFieldProvider(self.outcome_data)
        fields = provider.get_field_definitions()
        self.assertIsInstance(fields, list)
        self.assertEqual(len(fields), 4)
        status_field = next(field for field in fields if field["name"] == "status")
        comments_field = next(field for field in fields if field["name"] == "supporting_comments")
        self.assertEqual(status_field["type"], "choice")
        self.assertEqual(status_field["widget"], "radio")
        self.assertTrue(status_field["required"])
        self.assertEqual(status_field["initial"], "confirm")
        choices = [choice[0] for choice in status_field["choices"]]
        self.assertIn("confirm", choices)
        self.assertIn("override", choices)
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
        self.assertEqual(layout["header"]["title"], "A1.a Monitoring Coverage Outcome")
        self.assertIn("status_message", layout["header"])
        self.assertIn("help_text", layout["header"])
        self.assertEqual(len(layout["groups"]), 2)
        self.assertIn("fields", layout["groups"][0])
        self.assertEqual(layout["groups"][0]["fields"], ["status", "overriding_comments"])
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
        self.assertIn("override", choices)
        self.assertNotIn("partially_achieved", choices)
