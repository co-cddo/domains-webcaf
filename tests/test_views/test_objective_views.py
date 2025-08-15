from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase
from django.urls import reverse


class TestObjectiveViewHelpers(TestCase):
    def setUp(self):
        from webcaf.webcaf.views.objective_views import ObjectiveView

        self.view = ObjectiveView()

    def test_format_objective_heading(self):
        parent_map = {"objective_A": {"text": "Governance"}}
        result = self.view._format_objective_heading("objective_A", parent_map)
        self.assertEqual(result, "Objective A - Governance")

    def test_format_principle_name(self):
        result = self.view._format_principle_name("principle_A1", "Principle Text")
        self.assertEqual(result, "Principle:A1 Principle Text")

    def test_format_indicator_title(self):
        result = self.view._format_indicator_title("indicators_A1.a", "Indicator Text")
        self.assertEqual(result, "A1.a Indicator Text")

    def test_principles_for_objective_filters_correctly(self):
        parent_map = {
            "objective_A": {"text": "Governance"},
            "principle_A1": {"parent": "objective_A", "text": "A1 text"},
            "principle_A2": {"parent": "objective_A", "text": "A2 text"},
            "principle_B1": {"parent": "objective_B", "text": "B1 text"},
        }
        res = self.view._principles_for_objective(parent_map, "objective_A")
        keys = [k for k, _ in res]
        self.assertEqual(sorted(keys), sorted(["principle_A1", "principle_A2"]))

    def test_indicators_for_principle_filters_correctly(self):
        parent_map = {
            "principle_A1": {"parent": "objective_A"},
            "indicators_A1.a": {"parent": "principle_A1", "text": "Ia"},
            "indicators_A1.b": {"parent": "principle_A1", "text": "Ib"},
            "something_else": {"parent": "principle_A1"},
        }
        res = self.view._indicators_for_principle(parent_map, "principle_A1")
        keys = [k for k, _ in res]
        self.assertEqual(sorted(keys), sorted(["indicators_A1.a", "indicators_A1.b"]))

    def test_objective_navigation_first_and_last(self):
        parent_map = {
            "objective_A": {"text": "A"},
            "objective_B": {"text": "B"},
        }
        # First objective
        is_last, nxt = self.view._objective_navigation("objective_A", parent_map)
        self.assertFalse(is_last)
        self.assertEqual(nxt, "objective_B")
        # Last objective
        is_last, nxt = self.view._objective_navigation("objective_B", parent_map)
        self.assertTrue(is_last)
        self.assertIsNone(nxt)


class TestObjectiveViewAssessmentAccess(TestCase):
    def setUp(self):
        from webcaf.webcaf.views.objective_views import ObjectiveView

        self.factory = RequestFactory()
        self.view = ObjectiveView()
        request = self.factory.get("/")
        # Minimal session values required by get_assessment
        request.session = {
            "draft_assessment": {"assessment_id": 123},
            "current_profile_id": 77,
        }
        self.view.request = request

    @patch("webcaf.webcaf.views.objective_views.UserProfile")
    @patch("webcaf.webcaf.views.objective_views.Assessment")
    def test_get_assessment_uses_session_filters(self, MockAssessment, MockUserProfile):
        # Setup mocks
        mock_profile = MagicMock()
        mock_org = object()
        mock_profile.organisation = mock_org
        MockUserProfile.objects.get.return_value = mock_profile

        mock_assessment = MagicMock()
        MockAssessment.objects.get.return_value = mock_assessment

        result = self.view.get_assessment()

        MockUserProfile.objects.get.assert_called_once_with(id=77)
        MockAssessment.objects.get.assert_called_once_with(status="draft", id=123, system__organisation=mock_org)
        self.assertIs(result, mock_assessment)

    @patch("webcaf.webcaf.views.objective_views.calculate_outcome_status")
    def test_calculate_outcome_status_uses_cached_assessment(self, mock_calc):
        # Provide cached assessment to avoid DB hit
        assessment = MagicMock()
        assessment.assessments_data = {
            "indicator_indicators_A1.a": {"a": 1},
            "confirmation_indicators_A1.a": {"c": True},
        }
        # set cached_property value directly
        object.__setattr__(self.view, "assessment", assessment)

        # If get_assessment were called, raise to fail test
        with patch.object(self.view, "get_assessment", side_effect=AssertionError("should not be called")):
            res = self.view.calculate_outcome_status("indicator_indicators_A1.a")

        mock_calc.assert_called_once_with({"c": True}, {"a": 1})
        self.assertEqual(res, mock_calc.return_value)


class TestObjectiveViewContextData(TestCase):
    def setUp(self):
        from webcaf.webcaf.views.objective_views import ObjectiveView

        self.factory = RequestFactory()
        self.view = ObjectiveView()
        self.request = self.factory.get("/")
        self.request.session = {
            "draft_assessment": {"assessment_id": 1},
            "current_profile_id": 10,
        }
        self.view.request = self.request

    @patch("webcaf.webcaf.views.objective_views.ROUTE_FACTORY.get_router")
    @patch("webcaf.webcaf.views.objective_views.calculate_outcome_status")
    def test_get_context_data_builds_expected_structure(self, mock_calc_status, mock_get_router):
        # Parent map contains 1 objective with 1 principle and 2 indicators
        parent_map = {
            "objective_A": {"text": "Objective A text"},
            "principle_A1": {"parent": "objective_A", "text": "Principle A1 text"},
            "indicators_A1.a": {"parent": "principle_A1", "text": "Indicator A"},
            "indicators_A1.b": {"parent": "principle_A1", "text": "Indicator B"},
        }
        mock_get_router.return_value = MagicMock(parent_map=parent_map)

        # Cached assessment with completion and data
        assessment = MagicMock()
        assessment.assessments_data = {
            "indicator_indicators_A1.a": {"value": 42},
            "confirmation_indicators_A1.a": {"confirm_outcome": "confirm"},
            # No entry for indicators_A1.b, so complete=False expected
        }
        object.__setattr__(self.view, "assessment", assessment)

        kwargs = {"objective_id": "objective_A"}
        context = self.view.get_context_data(**kwargs)

        # Breadcrumbs
        expected_breadcrumbs = [
            {"url": reverse("my-account", kwargs={}), "text": "Home"},
            {
                "url": reverse("edit-draft-assessment", kwargs={"version": "v3.2", "assessment_id": 1}),
                "text": "Edit draft assessment",
            },
            {"text": "Objective A - Objective A text"},
        ]
        self.assertEqual(context["breadcrumbs"], expected_breadcrumbs)

        # Heading
        self.assertEqual(context["objective_heading"], "Objective A - Objective A text")

        # Navigation
        self.assertIn("final_objective", context)
        self.assertIn("assessment_id", context)
        self.assertTrue(context["final_objective"])  # only one objective => last
        self.assertEqual(context["assessment_id"], 1)

        # Principles and indicators
        self.assertEqual(len(context["principles"]), 1)
        principle = context["principles"][0]
        self.assertEqual(principle["name"], "Principle:A1 Principle A1 text")
        indicators = principle["indicators"]
        self.assertEqual(len(indicators), 2)

        # Indicator A should be complete and have outcome calculated
        ind_a = [i for i in indicators if i["id"] == "indicators_A1.a"][0]
        self.assertTrue(ind_a["complete"])  # has indicator data
        mock_calc_status.assert_any_call({"confirm_outcome": "confirm"}, {"value": 42})

        # Indicator B should be incomplete and still call outcome with empty dicts
        ind_b = [i for i in indicators if i["id"] == "indicators_A1.b"][0]
        self.assertFalse(ind_b["complete"])  # no indicator data

    @patch("webcaf.webcaf.views.objective_views.ROUTE_FACTORY.get_router")
    def test_get_context_data_adds_next_objective_when_not_last(self, mock_get_router):
        parent_map = {
            "objective_A": {"text": "A"},
            "objective_B": {"text": "B"},
            "principle_A1": {"parent": "objective_A", "text": ""},
            "indicators_A1.a": {"parent": "principle_A1", "text": ""},
        }
        mock_get_router.return_value = MagicMock(parent_map=parent_map)

        assessment = MagicMock()
        assessment.assessments_data = {}
        object.__setattr__(self.view, "assessment", assessment)

        ctx = self.view.get_context_data(objective_id="objective_A")
        self.assertEqual(ctx.get("next_objective"), "objective_B")
        self.assertFalse(ctx.get("final_objective"))

    @patch("webcaf.webcaf.views.objective_views.ROUTE_FACTORY.get_router")
    def test_get_context_data_marks_last_objective(self, mock_get_router):
        parent_map = {
            "objective_A": {"text": "A"},
            "principle_A1": {"parent": "objective_A", "text": ""},
            "indicators_A1.a": {"parent": "principle_A1", "text": ""},
        }
        mock_get_router.return_value = MagicMock(parent_map=parent_map)

        assessment = MagicMock()
        assessment.assessments_data = {}
        object.__setattr__(self.view, "assessment", assessment)

        ctx = self.view.get_context_data(objective_id="objective_A")
        self.assertTrue(ctx.get("final_objective"))
        self.assertIsNone(ctx.get("next_objective"))
