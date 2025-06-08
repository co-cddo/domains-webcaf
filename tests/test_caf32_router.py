import os
import unittest

from webcaf.webcaf.caf32_router import FrameworkRouter


# We test for the validity of the CAF YAML elsewhere, so this module assmes the YAML is valid
class TestFrameworkRouter(unittest.TestCase):
    def setUp(self):
        self.fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "caf-v3.2-dummy.yaml")

    def test_all_route_orders_pages_correctly(self):
        router = FrameworkRouter(self.fixture_path)
        descriptions = [
            "Capabilities exist to ensure security defences remain effective.",
            "The organisation monitors the security status of systems.",
            "Monitoring data sources allow for timely identification of security events.",
            "Monitoring data sources allow for timely identification of security events.",
            "The organisation detects malicious activity even when it evades standard solutions.",
            "Abnormality detection is used to identify malicious activity.",
            "Abnormality detection is used to identify malicious activity.",
            "Sophisticated attack detection through behavior monitoring.",
            "Sophisticated attack detection through behavior monitoring.",
            "Capabilities exist to minimize adverse impacts of security incidents.",
            "Well-defined incident management processes are in place.",
            "Incident response plan is based on risk assessment.",
            "Incident response plan is based on risk assessment.",
            "Capability exists to execute the response plan effectively.",
            "Capability exists to execute the response plan effectively.",
            "Response plans are regularly tested with realistic scenarios.",
            "Response plans are regularly tested with realistic scenarios.",
            "Incident root causes are analyzed to prevent recurrence.",
            "Root cause analysis ensures appropriate remediation.",
            "Root cause analysis ensures appropriate remediation.",
        ]
        page_types = [
            "objective",
            "principle",
            "section-indicators",
            "section-outcome",
            "principle",
            "section-indicators",
            "section-outcome",
            "section-indicators",
            "section-outcome",
            "objective",
            "principle",
            "section-indicators",
            "section-outcome",
            "section-indicators",
            "section-outcome",
            "section-indicators",
            "section-outcome",
            "principle",
            "section-indicators",
            "section-outcome",
        ]
        for i, item in enumerate(router.all_route()):
            self.assertEqual(item["description"], descriptions[i])
            self.assertEqual(item["type"], page_types[i])

    def test_org_route_orders_pages_correctly(self):
        router = FrameworkRouter(self.fixture_path)
        descriptions = [
            "Capabilities exist to ensure security defences remain effective.",
            "The organisation detects malicious activity even when it evades standard solutions.",
            "Abnormality detection is used to identify malicious activity.",
            "Abnormality detection is used to identify malicious activity.",
            "Capabilities exist to minimize adverse impacts of security incidents.",
            "Well-defined incident management processes are in place.",
            "Capability exists to execute the response plan effectively.",
            "Capability exists to execute the response plan effectively.",
        ]
        page_types = [
            "objective",
            "principle",
            "section-indicators",
            "section-outcome",
            "objective",
            "principle",
            "section-indicators",
            "section-outcome",
            "objective",
            "principle",
            "section-indicators",
            "section-outcome",
            "objective",
            "principle",
            "section-indicators",
            "section-outcome",
        ]
        for i, item in enumerate(router.org_route()):
            self.assertEqual(item["description"], descriptions[i])
            self.assertEqual(item["type"], page_types[i])

    def test_system_route_orders_pages_correctly(self):
        router = FrameworkRouter(self.fixture_path)
        descriptions = [
            "Capabilities exist to ensure security defences remain effective.",
            "The organisation monitors the security status of systems.",
            "Monitoring data sources allow for timely identification of security events.",
            "Monitoring data sources allow for timely identification of security events.",
            "The organisation detects malicious activity even when it evades standard solutions.",
            "Sophisticated attack detection through behavior monitoring.",
            "Sophisticated attack detection through behavior monitoring.",
            "Capabilities exist to minimize adverse impacts of security incidents.",
            "Well-defined incident management processes are in place.",
            "Incident response plan is based on risk assessment.",
            "Incident response plan is based on risk assessment.",
            "Response plans are regularly tested with realistic scenarios.",
            "Response plans are regularly tested with realistic scenarios.",
            "Incident root causes are analyzed to prevent recurrence.",
            "Root cause analysis ensures appropriate remediation.",
            "Root cause analysis ensures appropriate remediation.",
        ]
        page_types = [
            "objective",
            "principle",
            "section-indicators",
            "section-outcome",
            "principle",
            "section-indicators",
            "section-outcome",
            "objective",
            "principle",
            "section-indicators",
            "section-outcome",
            "section-indicators",
            "section-outcome",
            "principle",
            "section-indicators",
            "section-outcome",
        ]
        for i, item in enumerate(router.system_route()):
            self.assertEqual(item["description"], descriptions[i])
            self.assertEqual(item["type"], page_types[i])

    def test_urls_added_to_urlpatterns(self):
        """Test that URLs are correctly added to Django's urlpatterns."""
        from webcaf import urls

        original_length = len(urls.urlpatterns)
        router = FrameworkRouter(self.fixture_path)
        route_items = router.all_route()
        num_expected_new_urls = len(route_items)

        expected_paths = [
            "a-detecting-cyber-security-events/",
            "a1-security-monitoring/",
            "a1a-monitoring-coverage/indicators/",
            "a1a-monitoring-coverage/outcome/",
            "a2-proactive-security-event-discovery/",
            "a2a-system-abnormalities-for-attack-detection/indicators/",
            "a2a-system-abnormalities-for-attack-detection/outcome/",
            "a2b-proactive-attack-discovery/indicators/",
            "a2b-proactive-attack-discovery/outcome/",
            "b-minimising-the-impact-of-cyber-security-incidents/",
            "b1-response-and-recovery-planning/",
            "b1a-response-plan/indicators/",
            "b1a-response-plan/outcome/",
            "b1b-response-and-recovery-capability/indicators/",
            "b1b-response-and-recovery-capability/outcome/",
            "b1c-testing-and-exercising/indicators/",
            "b1c-testing-and-exercising/outcome/",
            "b2-lessons-learned/",
            "b2a-incident-root-cause-analysis/indicators/",
            "b2a-incident-root-cause-analysis/outcome/",
        ]

        expected_names = [
            "objective_1",
            "principle_1",
            "section-indicators_1",
            "section-outcome_1",
            "principle_2",
            "section-indicators_2",
            "section-outcome_2",
            "section-indicators_3",
            "section-outcome_3",
            "objective_2",
            "principle_3",
            "section-indicators_4",
            "section-outcome_4",
            "section-indicators_5",
            "section-outcome_5",
            "section-indicators_6",
            "section-outcome_6",
            "principle_4",
            "section-indicators_7",
            "section-outcome_7",
        ]

        self.assertEqual(len(urls.urlpatterns) - original_length, num_expected_new_urls)

        for i in range(num_expected_new_urls):
            url_pattern = urls.urlpatterns[original_length + i]
            self.assertEqual(url_pattern.name, expected_names[i])
            self.assertIn(expected_paths[i], url_pattern.pattern.describe())
            route_item = route_items[i]
            view_class = url_pattern.callback.view_class
            self.assertIs(view_class, route_item["view_class"])


if __name__ == "__main__":
    unittest.main()
