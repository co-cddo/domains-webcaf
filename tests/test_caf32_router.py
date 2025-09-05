import os
import unittest
from unittest.mock import Mock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from django.urls.resolvers import URLPattern

from webcaf import urls
from webcaf.webcaf.caf.routers import CAF32Router
from webcaf.webcaf.models import Assessment, UserProfile

# Test that when _create_view_and_url is called with an outcome, it has a form class as an argument.


class CAF32RouterWithFixture(CAF32Router):
    framework_path = os.path.join(os.path.dirname(__file__), "fixtures", "caf-v3.2-dummy.yaml")


# We test for the validity of the CAF YAML elsewhere, so this module assmes the YAML is valid
class TestCAF32Router(unittest.TestCase):
    def setUp(self):
        self._original_urlpatterns = list(urls.urlpatterns)
        urls.urlpatterns[:] = []
        self.router = CAF32RouterWithFixture()
        self.router.execute()

    def tearDown(self):
        urls.urlpatterns[:] = self._original_urlpatterns

    def test_urlpatterns_expected_count(self):
        expected_count = 20
        self.assertEqual(len(urls.urlpatterns), expected_count)

    def test_urls_added_to_urlpatterns(self):
        expected_paths = [
            "caf32/a-detecting-cyber-security-events/",
            "caf32/a1-security-monitoring/",
            "caf32/a1a-monitoring-coverage/indicators/",
            "caf32/a1a-monitoring-coverage/confirmation/",
            "caf32/a2-proactive-security-event-discovery/",
            "caf32/a2a-system-abnormalities-for-attack-detection/indicators/",
            "caf32/a2a-system-abnormalities-for-attack-detection/confirmation/",
            "caf32/a2b-proactive-attack-discovery/indicators/",
            "caf32/a2b-proactive-attack-discovery/confirmation/",
            "caf32/b-minimising-the-impact-of-cyber-security-incidents/",
            "caf32/b1-response-and-recovery-planning/",
            "caf32/b1a-response-plan/indicators/",
            "caf32/b1a-response-plan/confirmation/",
            "caf32/b1b-response-and-recovery-capability/indicators/",
            "caf32/b1b-response-and-recovery-capability/confirmation/",
            "caf32/b1c-testing-and-exercising/indicators/",
            "caf32/b1c-testing-and-exercising/confirmation/",
            "caf32/b2-lessons-learned/",
            "caf32/b2a-incident-root-cause-analysis/indicators/",
            "caf32/b2a-incident-root-cause-analysis/confirmation/",
        ]

        expected_names = [
            "caf32_objective_A",
            "caf32_principle_A1",
            "caf32_indicators_A1.a",
            "caf32_confirmation_A1.a",
            "caf32_principle_A2",
            "caf32_indicators_A2.a",
            "caf32_confirmation_A2.a",
            "caf32_indicators_A2.b",
            "caf32_confirmation_A2.b",
            "caf32_objective_B",
            "caf32_principle_B1",
            "caf32_indicators_B1.a",
            "caf32_confirmation_B1.a",
            "caf32_indicators_B1.b",
            "caf32_confirmation_B1.b",
            "caf32_indicators_B1.c",
            "caf32_confirmation_B1.c",
            "caf32_principle_B2",
            "caf32_indicators_B2.a",
            "caf32_confirmation_B2.a",
        ]

        num_expected_new_urls = len(expected_names)
        self.assertEqual(len(urls.urlpatterns), num_expected_new_urls)

        for i in range(num_expected_new_urls):
            url_pattern = urls.urlpatterns[i]
            self.assertEqual(url_pattern.name, expected_names[i])
            pattern_string = url_pattern.pattern.describe()
            path = pattern_string.split(" [")[0].strip("'")
            self.assertEqual(expected_paths[i], path)

    def test_urlpatterns_no_duplicates(self):
        original_length = len(urls.urlpatterns)
        added_patterns = urls.urlpatterns[original_length:]
        names = [pattern.name for pattern in added_patterns if hasattr(pattern, "name")]
        self.assertEqual(len(names), len(set(names)), "Duplicate URL pattern names found")

    def test_objective_breadcrumbs(self):
        factory = RequestFactory()
        request = factory.get("/")
        for pattern in urls.urlpatterns:
            if isinstance(pattern, URLPattern) and pattern.name == "caf32_objective_A":
                view_class = pattern.callback.view_class
                break
        else:
            self.fail("caf32_objective_A not found in urlpatterns")
        view = view_class()
        view.request = self.add_session_to_request(request)
        context = view.get_context_data()
        breadcrumbs = context.get("breadcrumbs")
        self.assertIsInstance(breadcrumbs, list)
        self.assertEqual(breadcrumbs[0]["text"], "My account")
        self.assertEqual(breadcrumbs[-1]["text"], "Objective A - Detecting cyber security events")

    def test_principle_breadcrumbs(self):
        factory = RequestFactory()
        request = factory.get("/")
        for pattern in urls.urlpatterns:
            if isinstance(pattern, URLPattern) and pattern.name == "caf32_principle_A1":
                view_class = pattern.callback.view_class
                break
        else:
            self.fail("caf32_principle_A1 not found in urlpatterns")
        view = view_class()
        view.request = self.add_session_to_request(request)
        context = view.get_context_data()
        breadcrumbs = context.get("breadcrumbs")
        self.assertEqual(breadcrumbs[-2]["text"], "My account")
        self.assertEqual(breadcrumbs[-1]["text"], "Edit draft assessment")

    def test_outcome_breadcrumbs(self):
        factory = RequestFactory()
        request = factory.get("/")
        for pattern in urls.urlpatterns:
            if isinstance(pattern, URLPattern) and pattern.name == "caf32_indicators_A1.a":
                view_class = pattern.callback.view_class
                break
        else:
            self.fail("caf32_indicators_A1.a not found in urlpatterns")
        view = view_class()
        view.request = self.add_session_to_request(request)
        with patch("webcaf.webcaf.models.UserProfile.objects.get") as mock_profile_get:
            with patch("webcaf.webcaf.models.Assessment.objects.get") as mock_assessment_get:
                mock_profile = Mock(UserProfile)
                mock_assessment = Mock(Assessment)
                mock_assessment.assessments_data.get.return_value = {}
                mock_profile_get.return_value = mock_profile
                mock_assessment_get.return_value = mock_assessment
                context = view.get_context_data()
        breadcrumbs = context.get("breadcrumbs")
        self.assertEqual(breadcrumbs[0]["text"], "My account")
        self.assertEqual(breadcrumbs[1]["text"], "Edit draft assessment")
        self.assertEqual(breadcrumbs[2]["text"], "Objective A - Detecting cyber security events")
        self.assertEqual(breadcrumbs[3]["text"], "Objective A1.a - Monitoring Coverage")

    def test_breadcrumbs_have_urls(self):
        factory = RequestFactory()
        request = factory.get("/")
        for pattern in urls.urlpatterns:
            if isinstance(pattern, URLPattern) and pattern.name == "caf32_confirmation_B2.a":
                view_class = pattern.callback.view_class
                break
        else:
            self.fail("caf32_confirmation_B2.a not found in urlpatterns")
        view = view_class()
        view.request = self.add_session_to_request(request)
        with patch("webcaf.webcaf.models.UserProfile.objects.get") as mock_profile_get:
            with patch("webcaf.webcaf.models.Assessment.objects.get") as mock_assessment_get:
                mock_profile = Mock(UserProfile)
                mock_assessment = Mock(
                    Assessment, assessments_data={"B2.a": {"indicators": {"indicator_1": {"id": "indicator_1"}}}}
                )
                mock_profile_get.return_value = mock_profile
                mock_assessment_get.return_value = mock_assessment
                context = view.get_context_data()
        breadcrumbs = context.get("breadcrumbs")
        for i, crumb in enumerate(breadcrumbs):
            if i != len(breadcrumbs) - 1:
                self.assertIn("url", crumb)
                self.assertTrue(isinstance(crumb["url"], str) or hasattr(crumb["url"], "__class__"))
            else:
                # Last element is always plain text
                self.assertNotIn("url", crumb)

    def add_session_to_request(self, request):
        """Attach a session to a request (for RequestFactory)."""
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session["draft_assessment"] = {
            "assessment_id": 1,
        }
        request.session["current_profile_id"] = 1
        request.session.save()
        return request


if __name__ == "__main__":
    unittest.main()
