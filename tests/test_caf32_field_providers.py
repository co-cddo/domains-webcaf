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
        self.assertEqual(metadata["id"], "A1.a")
        self.assertEqual(metadata["code"], "A1.a")
        self.assertEqual(metadata["title"], "Monitoring Coverage")
        self.assertEqual(
            metadata["description"], "Monitoring data sources allow for timely identification of security events."
        )

    def test_indicators_provider_field_definitions(self):
        provider = OutcomeIndicatorsFieldProvider(self.outcome_data)
        fields = provider.get_field_definitions()
        self.assertIsInstance(fields, list)
        expected_field_names = [
            "not-achieved_A1.a.1",
            "not-achieved_A1.a.2",
            "not-achieved_A1.a.3",
            "not-achieved_A1.a.4",
            "not-achieved_comment",
            "not-achieved_comment_details",
            "not-achieved_none_of_the_above",
            "partially-achieved_A1.a.5",
            "partially-achieved_A1.a.6",
            "partially-achieved_A1.a.7",
            "partially-achieved_A1.a.8",
            "partially-achieved_comment",
            "partially-achieved_comment_details",
            "partially-achieved_none_of_the_above",
            "achieved_A1.a.9",
            "achieved_A1.a.10",
            "achieved_A1.a.11",
            "achieved_A1.a.12",
            "achieved_A1.a.13",
            "achieved_A1.a.14",
            "achieved_comment",
            "achieved_comment_details",
            "achieved_none_of_the_above",
        ]
        self.assertEqual([f["name"] for f in fields], expected_field_names)
        for field in fields:
            self.assertIn("name", field)
            self.assertIn("label", field)
            self.assertIn("type", field)
            self.assertIn("required", field)
            if field["type"] == "text":
                self.assertIn("widget_attrs", field)
                self.assertEqual(field["widget_attrs"]["class"], "govuk-textarea")
                self.assertEqual(field["widget_attrs"]["rows"], 3)
                self.assertEqual(field["widget_attrs"]["maxlength"], 500)
            else:
                self.assertNotIn("widget_attrs", field)
            self.assertFalse(field["required"])
        field_labels = {field["name"]: field["label"] for field in fields}
        self.assertEqual(field_labels["not-achieved_A1.a.1"], "Security operation data is not collected.")
        self.assertEqual(field_labels["achieved_A1.a.14"], "New systems are evaluated as monitoring data sources.")
        self.assertEqual(field_labels["not-achieved_comment"], "Make a comment about a statement")
        self.assertEqual(field_labels["not-achieved_comment_details"], "Provide your comment")
        self.assertEqual(field_labels["not-achieved_none_of_the_above"], "None of the above")
        self.assertEqual(field_labels["partially-achieved_comment"], "Make a comment about a statement")
        self.assertEqual(field_labels["partially-achieved_comment_details"], "Provide your comment")
        self.assertEqual(field_labels["partially-achieved_none_of_the_above"], "None of the above")
        self.assertEqual(field_labels["achieved_comment"], "Make a comment about a statement")
        self.assertEqual(field_labels["achieved_comment_details"], "Provide your comment")
        self.assertEqual(field_labels["achieved_none_of_the_above"], "None of the above")

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
        expected_groups = [
            {
                "title": "Not Achieved",
                "fields": [
                    "not-achieved_A1.a.1",
                    "not-achieved_A1.a.2",
                    "not-achieved_A1.a.3",
                    "not-achieved_A1.a.4",
                    "not-achieved_comment",
                    "not-achieved_none_of_the_above",
                ],
            },
            {
                "title": "Partially Achieved",
                "fields": [
                    "partially-achieved_A1.a.5",
                    "partially-achieved_A1.a.6",
                    "partially-achieved_A1.a.7",
                    "partially-achieved_A1.a.8",
                    "partially-achieved_comment",
                    "partially-achieved_none_of_the_above",
                ],
            },
            {
                "title": "Achieved",
                "fields": [
                    "achieved_A1.a.9",
                    "achieved_A1.a.10",
                    "achieved_A1.a.11",
                    "achieved_A1.a.12",
                    "achieved_A1.a.13",
                    "achieved_A1.a.14",
                    "achieved_comment",
                    "achieved_none_of_the_above",
                ],
            },
        ]
        self.assertEqual(layout["groups"], expected_groups)

    def test_outcome_provider_metadata(self):
        provider = OutcomeConfirmationFieldProvider(self.outcome_data)
        metadata = provider.get_metadata()
        self.assertIsInstance(metadata, dict)
        self.assertEqual(metadata["id"], "A1.a")
        self.assertEqual(metadata["code"], "A1.a")
        self.assertEqual(metadata["title"], "Monitoring Coverage")

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
        self.assertEqual(layout["header"]["title"], "A1.a Outcome")
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
