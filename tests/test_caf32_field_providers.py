import os

import yaml
from django.test import TestCase

from webcaf.webcaf.caf_loader.caf32_field_providers import (
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
            self.assertEqual(field["type"], "choice_with_justifications")
            self.assertTrue(field["required"])
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
