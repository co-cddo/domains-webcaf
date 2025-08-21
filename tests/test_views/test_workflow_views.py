from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase
from django.urls import reverse


class TestOutcomeIndicatorsHandlerViewGetSuccessUrl(TestCase):
    """Test cases for OutcomeIndicatorsHandlerView.get_success_url method.
    Always redirects the user to the confirmation view.
    """

    def setUp(self):
        from webcaf.webcaf.views.workflow_views import OutcomeIndicatorsHandlerView

        self.factory = RequestFactory()
        self.view = OutcomeIndicatorsHandlerView()
        self.view.kwargs = {"indicator_id": "indicators_A1.a"}

    def test_get_success_url_returns_correct_url(self):
        """Test that get_success_url returns the correct confirmation URL."""
        expected_url = reverse(
            "indicator-confirmation-view", kwargs={"version": "v3.2", "indicator_id": "indicators_A1.a"}
        )

        result = self.view.get_success_url()

        self.assertEqual(result, expected_url)

    def test_get_success_url_with_different_indicator_id(self):
        """Test get_success_url with a different indicator ID."""
        self.view.kwargs = {"indicator_id": "indicators_B2.b"}

        expected_url = reverse(
            "indicator-confirmation-view", kwargs={"version": "v3.2", "indicator_id": "indicators_B2.b"}
        )

        result = self.view.get_success_url()

        self.assertEqual(result, expected_url)


class TestOutcomeConfirmationHandlerViewGetSuccessUrl(TestCase):
    """Test cases for OutcomeConfirmationHandlerView.get_success_url method."""

    def setUp(self):
        from webcaf.webcaf.views.workflow_views import OutcomeConfirmationHandlerView

        self.factory = RequestFactory()
        self.view = OutcomeConfirmationHandlerView()
        self.view.request = MagicMock()
        self.view.request.session = {"draft_assessment": {"assessment_id": 1}}

    @patch("webcaf.webcaf.router_factory._RouterFactory.get_router")
    def test_get_success_url_next_indicator_in_same_parent(self, mock_framework_router):
        """Test navigation to next indicator within the same parent."""
        self.view.kwargs = {"indicator_id": "indicators_A1.a"}

        # Mock the framework router data
        mock_router = MagicMock(
            parent_map={
                "indicators_A1.a": {"parent": "principle_A1"},
                "indicators_A1.b": {"parent": "principle_A1"},
                "indicators_A1.c": {"parent": "principle_A1"},
            }
        )
        mock_framework_router.return_value = mock_router
        expected_url = reverse("indicator-view", kwargs={"version": "v3.2", "indicator_id": "indicators_A1.b"})

        result = self.view.get_success_url()

        self.assertEqual(result, expected_url)

    @patch("webcaf.webcaf.router_factory._RouterFactory.get_router")
    def test_get_success_url_last_indicator_not_last_principle(self, mock_framework_router):
        """Test navigation when at last indicator but not last principle."""
        self.view.kwargs = {"indicator_id": "indicators_A1.c"}

        # Mock the framework router data
        mock_router = MagicMock(
            parent_map={
                "indicators_A1.a": {"parent": "principle_A1"},
                "indicators_A1.b": {"parent": "principle_A1"},
                "indicators_A1.c": {"parent": "principle_A1"},
                "principle_A1": {},
                "principle_A2": {},
            }
        )
        mock_framework_router.return_value = mock_router

        expected_url = reverse("objective-overview", kwargs={"version": "v3.2", "objective_id": "objective_A"})

        result = self.view.get_success_url()

        self.assertEqual(result, expected_url)

    @patch("webcaf.webcaf.router_factory._RouterFactory.get_router")
    def test_get_success_url_last_indicator_last_principle(self, mock_framework_router):
        """Test navigation when at last indicator of last principle (flow complete)."""
        self.view.kwargs = {"indicator_id": "indicators_B2.z"}

        # Mock the framework router data - only one principle exists
        mock_router = MagicMock(
            parent_map={
                "indicators_B2.z": {"parent": "principle_B2"},
                "principle_B2": {},
            }
        )
        mock_framework_router.return_value = mock_router

        expected_url = reverse("edit-draft-assessment", kwargs={"version": "v3.2", "assessment_id": 1})

        result = self.view.get_success_url()

        self.assertEqual(result, expected_url)

    @patch("webcaf.webcaf.router_factory._RouterFactory.get_router")
    def test_get_success_url_multiple_indicators_same_parent(self, mock_framework_router):
        """Test with multiple indicators in the same parent."""
        self.view.kwargs = {"indicator_id": "indicators_C3.b"}

        mock_router = MagicMock(
            parent_map={
                "indicators_C3.a": {"parent": "principle_C3"},
                "indicators_C3.b": {"parent": "principle_C3"},
                "indicators_C3.c": {"parent": "principle_C3"},
                "indicators_C3.d": {"parent": "principle_C3"},
                "principle_C3": {},
                "principle_C4": {},
            }
        )
        mock_framework_router.return_value = mock_router

        expected_url = reverse("indicator-view", kwargs={"version": "v3.2", "indicator_id": "indicators_C3.c"})

        result = self.view.get_success_url()

        self.assertEqual(result, expected_url)

    @patch("webcaf.webcaf.router_factory._RouterFactory.get_router")
    def test_get_success_url_multiple_principles(self, mock_framework_router):
        """Test with multiple principles available.
        Once the final indicator is reached, the user is redirected to the objective overview.
        """
        self.view.kwargs = {"indicator_id": "indicators_D1.final"}

        mock_router = MagicMock(
            parent_map={
                "indicators_D1.final": {"parent": "principle_D1"},
                "principle_D1": {},
                "principle_D2": {},
                "principle_D3": {},
            }
        )
        mock_framework_router.return_value = mock_router

        expected_url = reverse("objective-overview", kwargs={"version": "v3.2", "objective_id": "objective_D"})

        result = self.view.get_success_url()

        self.assertEqual(result, expected_url)

    def test_get_success_url_extracts_objective_id_correctly(self):
        """Test that objective ID is correctly extracted from indicator ID."""
        test_cases = [
            ("indicators_A1.a", "A"),
            ("indicators_B2.x", "B"),
            ("indicators_C10.z", "C"),
            ("indicators_Z99.final", "Z"),
        ]

        for indicator_id, expected_objective_id in test_cases:
            with self.subTest(f"Test indicator ID: {indicator_id}"):
                with self.subTest(indicator_id=indicator_id):
                    self.view.kwargs = {"indicator_id": indicator_id}

                    with patch("webcaf.webcaf.router_factory._RouterFactory.get_router") as mock_framework_router:
                        # Setup mock to trigger objective overview path
                        mock_router = MagicMock(
                            parent_map={
                                indicator_id: {"parent": f"principle_{indicator_id[11:]}"},
                                f"principle_{indicator_id[11:]}": {},
                                "principle_other": {},
                            }
                        )
                        mock_framework_router.return_value = mock_router

                        result = self.view.get_success_url()

                        expected_url = reverse(
                            "objective-overview",
                            kwargs={"version": "v3.2", "objective_id": f"objective_{expected_objective_id}"},
                        )
                        self.assertEqual(result, expected_url)

    @patch("webcaf.webcaf.router_factory._RouterFactory.get_router")
    def test_private_get_parent_id(self, mock_framework_router):
        """Test the _get_parent_id utility method."""
        indicator_id = "indicators_A1.test"
        expected_parent = "principle_A1"

        mock_router = MagicMock(parent_map={indicator_id: {"parent": expected_parent}})
        mock_framework_router.return_value = mock_router

        result = self.view._get_parent_id(indicator_id)

        self.assertEqual(result, expected_parent)

    @patch("webcaf.webcaf.router_factory._RouterFactory.get_router")
    def test_private_get_indicator_siblings(self, mock_framework_router):
        """Test the _get_indicator_siblings utility method."""
        parent_id = "principle_A1"

        mock_router = MagicMock(
            parent_map={
                "indicators_A1.a": {"parent": parent_id},
                "indicators_A1.b": {"parent": parent_id},
                "indicators_A1.c": {"parent": parent_id},
                "indicators_B2.x": {"parent": "principle_B2"},
                "some_other_key": {"parent": parent_id},  # Should be excluded (doesn't start with 'indicators')
            }
        )
        mock_framework_router.return_value = mock_router

        expected_siblings = ["indicators_A1.a", "indicators_A1.b", "indicators_A1.c"]

        result = self.view._get_indicator_siblings(parent_id)

        self.assertEqual(sorted(result), sorted(expected_siblings))

    @patch("webcaf.webcaf.router_factory._RouterFactory.get_router")
    def test_private_get_principle_siblings(self, mock_framework_router):
        """Test the _get_principle_siblings utility method."""
        mock_router = MagicMock(
            parent_map={
                "principle_A1": {},
                "principle_A2": {},
                "principle_B1": {},
                "indicators_A1.a": {"parent": "principle_A1"},
                "other_key": {},  # Should be excluded (doesn't start with 'principle')
            }
        )
        mock_framework_router.return_value = mock_router

        expected_principles = ["principle_A1", "principle_A2", "principle_B1"]

        result = self.view._get_principle_siblings()

        self.assertEqual(sorted(result), sorted(expected_principles))

    def test_private_is_last_index(self):
        """Test the _is_last_index utility method."""
        test_cases = [
            # (index, items_length, expected_result)
            (0, 3, False),  # First of 3 items
            (1, 3, False),  # Second of 3 items
            (2, 3, True),  # Last of 3 items
            (0, 1, True),  # Only item
            (0, 2, False),  # First of 2 items
            (1, 2, True),  # Last of 2 items
        ]

        for index, items_length, expected in test_cases:
            with self.subTest(index=index, items_length=items_length):
                items = ["item"] * items_length
                result = self.view._is_last_index(index, items)
                self.assertEqual(result, expected)

    @patch("webcaf.webcaf.router_factory._RouterFactory.get_router")
    def test_get_success_url_edge_case_empty_siblings(self, mock_get_router):
        """Test behavior when there are no sibling indicators."""
        self.view.kwargs = {"indicator_id": "indicators_X1.only"}

        # Only one indicator in this principle
        mock_router = MagicMock(
            parent_map={
                "indicators_X1.only": {"parent": "principle_X1"},
                "principle_X1": {},
                "principle_X2": {},
            }
        )
        mock_get_router.return_value = mock_router
        expected_url = reverse("objective-overview", kwargs={"version": "v3.2", "objective_id": "objective_X"})

        result = self.view.get_success_url()

        self.assertEqual(result, expected_url)

    def test_get_success_url_uses_session_assessment_id(self):
        """Test that the method uses the correct assessment ID from session.
        Also test that the user is redirected to the edit draft assessment view as this is the last step"""
        different_assessment_id = 2
        self.view.request.session["draft_assessment"]["assessment_id"] = 2
        self.view.kwargs = {"indicator_id": "indicators_Z9.final"}

        with patch("webcaf.webcaf.router_factory._RouterFactory.get_router") as mock_framework_router:
            # Setup to trigger the complete flow path
            mock_router = MagicMock(
                parent_map={
                    "indicators_Z9.final": {"parent": "principle_Z9"},
                    "principle_Z9": {},  # Only principle, so it's the last one
                }
            )
            mock_framework_router.return_value = mock_router

            result = self.view.get_success_url()

            expected_url = reverse(
                "edit-draft-assessment", kwargs={"version": "v3.2", "assessment_id": different_assessment_id}
            )
            self.assertEqual(result, expected_url)
