import os
import unittest

from django.test import RequestFactory
from django.urls.resolvers import URLPattern

from webcaf import urls
from webcaf.webcaf.caf32_router import CAF32Router

# Test that when _create_view_and_url is called with an outcome, it has a form class as an argument.


# We test for the validity of the CAF YAML elsewhere, so this module assmes the YAML is valid
class TestCAF32Router(unittest.TestCase):
    def setUp(self):
        self.fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "caf-v3.2-dummy.yaml")
        self._original_urlpatterns = list(urls.urlpatterns)
        urls.urlpatterns[:] = []

    def tearDown(self):
        urls.urlpatterns[:] = self._original_urlpatterns

    def test_urlpatterns_expected_count(self):
        router = CAF32Router(self.fixture_path)
        original_length = len(urls.urlpatterns)
        router.execute()

        added_patterns = urls.urlpatterns[original_length:]
        expected_count = 20
        self.assertEqual(len(added_patterns), expected_count)

    def test_urls_added_to_urlpatterns(self):
        original_length = len(urls.urlpatterns)
        router = CAF32Router(self.fixture_path)
        router.execute()

        expected_paths = [
            "a-detecting-cyber-security-events/",
            "a1-security-monitoring/",
            "a1a-monitoring-coverage/indicators/",
            "a1a-monitoring-coverage/confirmation/",
            "a2-proactive-security-event-discovery/",
            "a2a-system-abnormalities-for-attack-detection/indicators/",
            "a2a-system-abnormalities-for-attack-detection/confirmation/",
            "a2b-proactive-attack-discovery/indicators/",
            "a2b-proactive-attack-discovery/confirmation/",
            "b-minimising-the-impact-of-cyber-security-incidents/",
            "b1-response-and-recovery-planning/",
            "b1a-response-plan/indicators/",
            "b1a-response-plan/confirmation/",
            "b1b-response-and-recovery-capability/indicators/",
            "b1b-response-and-recovery-capability/confirmation/",
            "b1c-testing-and-exercising/indicators/",
            "b1c-testing-and-exercising/confirmation/",
            "b2-lessons-learned/",
            "b2a-incident-root-cause-analysis/indicators/",
            "b2a-incident-root-cause-analysis/confirmation/",
        ]

        expected_names = [
            "objective_A",
            "principle_A1",
            "indicators_A1.a",
            "confirmation_A1.a",
            "principle_A2",
            "indicators_A2.a",
            "confirmation_A2.a",
            "indicators_A2.b",
            "confirmation_A2.b",
            "objective_B",
            "principle_B1",
            "indicators_B1.a",
            "confirmation_B1.a",
            "indicators_B1.b",
            "confirmation_B1.b",
            "indicators_B1.c",
            "confirmation_B1.c",
            "principle_B2",
            "indicators_B2.a",
            "confirmation_B2.a",
        ]

        num_expected_new_urls = len(expected_names)
        self.assertEqual(len(urls.urlpatterns) - original_length, num_expected_new_urls)

        for i in range(num_expected_new_urls):
            url_pattern = urls.urlpatterns[original_length + i]
            self.assertEqual(url_pattern.name, expected_names[i])
            self.assertIn(expected_paths[i], url_pattern.pattern.describe())

    def test_urlpatterns_no_duplicates(self):
        router = CAF32Router(self.fixture_path)
        original_length = len(urls.urlpatterns)
        router.execute()

        added_patterns = urls.urlpatterns[original_length:]
        names = [pattern.name for pattern in added_patterns if hasattr(pattern, "name")]
        self.assertEqual(len(names), len(set(names)), "Duplicate URL pattern names found")

    def test_objective_breadcrumbs(self):
        router = CAF32Router(self.fixture_path)
        router.execute()
        factory = RequestFactory()
        request = factory.get("/")
        for pattern in urls.urlpatterns:
            if isinstance(pattern, URLPattern) and pattern.name == "objective_A":
                view_class = pattern.callback.view_class
                break
        else:
            self.fail("objective_A not found in urlpatterns")
        view = view_class()
        view.request = request
        context = view.get_context_data()
        breadcrumbs = context.get("breadcrumbs")
        self.assertIsInstance(breadcrumbs, list)
        self.assertEqual(breadcrumbs[0]["text"], "Root")
        self.assertEqual(breadcrumbs[-1]["text"], "Detecting cyber security events")

    def test_principle_breadcrumbs(self):
        router = CAF32Router(self.fixture_path)
        router.execute()
        factory = RequestFactory()
        request = factory.get("/")
        for pattern in urls.urlpatterns:
            if isinstance(pattern, URLPattern) and pattern.name == "principle_A1":
                view_class = pattern.callback.view_class
                break
        else:
            self.fail("principle_A1 not found in urlpatterns")
        view = view_class()
        view.request = request
        context = view.get_context_data()
        breadcrumbs = context.get("breadcrumbs")
        self.assertEqual(breadcrumbs[-2]["text"], "Detecting cyber security events")
        self.assertEqual(breadcrumbs[-1]["text"], "Security Monitoring")

    def test_outcome_breadcrumbs(self):
        router = CAF32Router(self.fixture_path)
        router.execute()
        factory = RequestFactory()
        request = factory.get("/")
        for pattern in urls.urlpatterns:
            if isinstance(pattern, URLPattern) and pattern.name == "indicators_A1.a":
                view_class = pattern.callback.view_class
                break
        else:
            self.fail("indicators_A1.a not found in urlpatterns")
        view = view_class()
        view.request = request
        context = view.get_context_data()
        breadcrumbs = context.get("breadcrumbs")
        self.assertEqual(breadcrumbs[0]["text"], "Root")
        self.assertEqual(breadcrumbs[1]["text"], "Detecting cyber security events")
        self.assertEqual(breadcrumbs[2]["text"], "Security Monitoring")
        self.assertEqual(breadcrumbs[3]["text"], "Monitoring Coverage")

    def test_breadcrumbs_have_urls(self):
        router = CAF32Router(self.fixture_path)
        router.execute()
        factory = RequestFactory()
        request = factory.get("/")
        for pattern in urls.urlpatterns:
            if isinstance(pattern, URLPattern) and pattern.name == "confirmation_B2.a":
                view_class = pattern.callback.view_class
                break
        else:
            self.fail("confirmation_B2.a not found in urlpatterns")
        view = view_class()
        view.request = request
        context = view.get_context_data()
        breadcrumbs = context.get("breadcrumbs")
        for crumb in breadcrumbs:
            self.assertIn("url", crumb)
            self.assertTrue(isinstance(crumb["url"], str) or hasattr(crumb["url"], "__class__"))


if __name__ == "__main__":
    unittest.main()
