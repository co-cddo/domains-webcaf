"""
Tests for AssessmentNotSelectedHandlerMiddleware.

This module verifies that AssessmentNotSelectedException exceptions are handled correctly,
with appropriate redirects for regular users and returning None for staff/admin users
to allow Django's default exception handling.
"""

from unittest.mock import Mock, patch

from django.http import HttpRequest, HttpResponse
from django.test import SimpleTestCase

from webcaf.middleware import AssessmentNotSelectedHandlerMiddleware
from webcaf.webcaf.views.general import AssessmentNotSelectedException


class AssessmentNotSelectedHandlerMiddlewareTest(SimpleTestCase):
    """Test suite for AssessmentNotSelectedHandlerMiddleware."""

    def setUp(self):
        """Set up test fixtures."""
        self.request = HttpRequest()
        self.request.path = "/assessment/edit/objective/1/"
        self.request.META = {"HTTP_ACCEPT": "text/html"}

    @patch("webcaf.middleware.redirect")
    @patch("webcaf.middleware.AbstractAssessmentErrorHandlerMiddleware.logger")
    def test_unauthenticated_user_redirects_to_draft_assessments(self, mock_logger, mock_redirect):
        """Unauthenticated users should be redirected to view-draft-assessments."""
        mock_redirect.return_value = HttpResponse(status=302, headers={"Location": "/view-draft-assessments/"})

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)
        self.request.user = Mock(is_authenticated=False, is_staff=False)
        self.request.path = "/assessment/edit/objective/1/"

        response = middleware.process_exception(self.request, AssessmentNotSelectedException())

        # Verify logging occurred with path
        mock_logger.warning.assert_called_once_with(
            "Handle assessment retrieval issue %s", "/assessment/edit/objective/1/"
        )

        # Verify redirect was called to view-draft-assessments
        mock_redirect.assert_called_once_with("view-draft-assessments")
        self.assertEqual(response.status_code, 302)

    @patch("webcaf.middleware.redirect")
    @patch("webcaf.middleware.AbstractAssessmentErrorHandlerMiddleware.logger")
    def test_authenticated_non_staff_user_redirects_to_draft_assessments(self, mock_logger, mock_redirect):
        """Authenticated non-staff users should be redirected to view-draft-assessments."""
        mock_redirect.return_value = HttpResponse(status=302, headers={"Location": "/view-draft-assessments/"})

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=42, is_authenticated=True, is_staff=False)
        self.request.path = "/assessment/system/123/"

        response = middleware.process_exception(self.request, AssessmentNotSelectedException())

        # Verify logging occurred with path
        mock_logger.warning.assert_called_once_with("Handle assessment retrieval issue %s", "/assessment/system/123/")

        # Verify redirect was called
        mock_redirect.assert_called_once_with("view-draft-assessments")
        self.assertEqual(response.status_code, 302)

    @patch("webcaf.middleware.AbstractAssessmentErrorHandlerMiddleware.logger")
    def test_staff_user_returns_none_for_default_handling(self, mock_logger):
        """Staff users should get None return to allow Django's default exception handling."""

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=99, is_authenticated=True, is_staff=True)
        self.request.path = "/assessment/edit/789/"

        response = middleware.process_exception(self.request, AssessmentNotSelectedException())

        # Verify logging still occurred
        mock_logger.warning.assert_called_once_with("Handle assessment retrieval issue %s", "/assessment/edit/789/")

        # Should return None to let Django handle it
        self.assertIsNone(response)

    @patch("webcaf.middleware.AbstractAssessmentErrorHandlerMiddleware.logger")
    def test_admin_path_returns_none_for_default_handling(self, mock_logger):
        """Requests to /admin/ paths should return None to allow Django's default exception handling."""

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)
        self.request.path = "/admin/webcaf/assessment/"
        self.request.user = Mock(id=55, is_authenticated=True, is_staff=False)

        response = middleware.process_exception(self.request, AssessmentNotSelectedException())

        # Verify logging occurred
        mock_logger.warning.assert_called_once_with("Handle assessment retrieval issue %s", "/admin/webcaf/assessment/")

        # Should return None to let Django handle it
        self.assertIsNone(response)

    @patch("webcaf.middleware.redirect")
    @patch("webcaf.middleware.AbstractAssessmentErrorHandlerMiddleware.logger")
    def test_request_without_user_attribute_redirects(self, mock_logger, mock_redirect):
        """When request lacks a user attribute, should redirect to draft assessments."""
        mock_redirect.return_value = HttpResponse(status=302, headers={"Location": "/view-draft-assessments/"})

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)
        # Remove user attribute from request
        if hasattr(self.request, "user"):
            delattr(self.request, "user")
        self.request.path = "/assessment/999/"

        response = middleware.process_exception(self.request, AssessmentNotSelectedException())

        # Verify logging occurred
        mock_logger.warning.assert_called_once_with("Handle assessment retrieval issue %s", "/assessment/999/")

        # Should redirect
        mock_redirect.assert_called_once_with("view-draft-assessments")
        self.assertEqual(response.status_code, 302)

    @patch("webcaf.middleware.redirect")
    @patch("webcaf.middleware.AbstractAssessmentErrorHandlerMiddleware.logger")
    def test_redirect_target_is_view_draft_assessments(self, mock_logger, mock_redirect):
        """Verify the exact redirect target name."""
        mock_redirect.return_value = HttpResponse(status=302, headers={"Location": "/view-draft-assessments/"})

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=100, is_authenticated=True, is_staff=False)
        self.request.path = "/assessment/111/"

        middleware.process_exception(self.request, AssessmentNotSelectedException())

        # Verify redirect was called with correct view name
        mock_redirect.assert_called_once_with("view-draft-assessments")

    @patch("webcaf.middleware.AbstractAssessmentErrorHandlerMiddleware.logger")
    def test_staff_status_takes_precedence_over_path(self, mock_logger):
        """When user is staff, should return None regardless of path."""

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)
        # Staff user making request to non-admin path
        self.request.user = Mock(id=200, is_authenticated=True, is_staff=True)
        self.request.path = "/assessment/view/"

        response = middleware.process_exception(self.request, AssessmentNotSelectedException())

        # Should return None for staff users
        self.assertIsNone(response)

        # Verify logging occurred
        mock_logger.warning.assert_called_once_with("Handle assessment retrieval issue %s", "/assessment/view/")

    @patch("webcaf.middleware.AbstractAssessmentErrorHandlerMiddleware.logger")
    def test_admin_path_variations_return_none(self, mock_logger):
        """Test various admin path patterns return None."""
        test_paths = [
            "/admin/",
            "/admin/webcaf/",
            "/admin/webcaf/assessment/123/",
            "/admin/auth/user/",
        ]

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=300, is_authenticated=False, is_staff=False)

        for path in test_paths:
            with self.subTest(path=path):
                self.request.path = path
                mock_logger.reset_mock()

                response = middleware.process_exception(self.request, AssessmentNotSelectedException())

                # Should return None for admin paths
                self.assertIsNone(response)

                # Verify logging occurred
                mock_logger.warning.assert_called_once_with("Handle assessment retrieval issue %s", path)

    @patch("webcaf.middleware.redirect")
    @patch("webcaf.middleware.AbstractAssessmentErrorHandlerMiddleware.logger")
    def test_non_admin_path_variations_redirect(self, mock_logger, mock_redirect):
        """Test various non-admin paths that should redirect."""
        mock_redirect.return_value = HttpResponse(status=302, headers={"Location": "/view-draft-assessments/"})

        test_paths = [
            "/assessment/",
            "/assessment/123/",
            "/dashboard/",
            "/user/profile/",
            "/not-admin/something/",
        ]

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=400, is_authenticated=False, is_staff=False)

        for path in test_paths:
            with self.subTest(path=path):
                self.request.path = path
                mock_logger.reset_mock()
                mock_redirect.reset_mock()

                response = middleware.process_exception(self.request, AssessmentNotSelectedException())

                self.assertEqual(response.status_code, 302)

                # Verify logging occurred
                mock_logger.warning.assert_called_once_with("Handle assessment retrieval issue %s", path)

                # Verify redirect was called
                mock_redirect.assert_called_once_with("view-draft-assessments")

    def test_other_exceptions_return_none(self):
        """Other exceptions should return None to let Django handle them."""

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=600, is_authenticated=False, is_staff=False)
        self.request.path = "/some/path/"

        response = middleware.process_exception(self.request, ValueError("Some other error"))

        # Should return None for non-AssessmentNotSelectedException exceptions
        self.assertIsNone(response)

    def test_assessment_does_not_exist_returns_none(self):
        """Assessment.DoesNotExist exceptions should return None (not handled by this middleware)."""
        from webcaf.webcaf.models import Assessment

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=700, is_authenticated=False, is_staff=False)
        self.request.path = "/some/path/"

        response = middleware.process_exception(self.request, Assessment.DoesNotExist("Assessment not found"))

        # Should return None - this middleware only handles AssessmentNotSelectedException
        self.assertIsNone(response)

    @patch("webcaf.middleware.redirect")
    @patch("webcaf.middleware.AbstractAssessmentErrorHandlerMiddleware.logger")
    def test_authenticated_staff_false_user_redirects(self, mock_logger, mock_redirect):
        """Authenticated users with is_staff=False should redirect."""
        mock_redirect.return_value = HttpResponse(status=302, headers={"Location": "/view-draft-assessments/"})

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=700, is_authenticated=True, is_staff=False)
        self.request.path = "/assessment/222/"

        response = middleware.process_exception(self.request, AssessmentNotSelectedException())

        mock_redirect.assert_called_once()
        self.assertEqual(response.status_code, 302)

    @patch("webcaf.middleware.AbstractAssessmentErrorHandlerMiddleware.logger")
    def test_unauthenticated_user_on_admin_path_returns_none(self, mock_logger):
        """Even unauthenticated users on /admin/ paths should return None."""

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)
        self.request.user = Mock(is_authenticated=False, is_staff=False)
        self.request.path = "/admin/login/"

        response = middleware.process_exception(self.request, AssessmentNotSelectedException())

        # Admin path should return None regardless of authentication
        self.assertIsNone(response)

    @patch("webcaf.middleware.AbstractAssessmentErrorHandlerMiddleware.logger")
    def test_logger_uses_warning_level(self, mock_logger):
        """Verify logger.warning is called."""

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=1000, is_authenticated=False, is_staff=False)
        self.request.path = "/assessment/555/"

        middleware.process_exception(self.request, AssessmentNotSelectedException())

        # Verify warning is called
        mock_logger.warning.assert_called_once()

    @patch("webcaf.middleware.redirect")
    @patch("webcaf.middleware.AbstractAssessmentErrorHandlerMiddleware.logger")
    def test_multiple_calls_with_different_paths(self, mock_logger, mock_redirect):
        """Test that path is correctly logged for multiple different calls."""
        mock_redirect.return_value = HttpResponse(status=302, headers={"Location": "/view-draft-assessments/"})

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=1100, is_authenticated=False, is_staff=False)

        paths = ["/assessment/1/", "/assessment/2/", "/assessment/3/"]

        for path in paths:
            with self.subTest(path=path):
                mock_logger.reset_mock()
                mock_redirect.reset_mock()
                self.request.path = path

                middleware.process_exception(self.request, AssessmentNotSelectedException())

                mock_logger.warning.assert_called_once_with("Handle assessment retrieval issue %s", path)
                mock_redirect.assert_called_once_with("view-draft-assessments")

    def test_is_handled_exception_returns_true_for_correct_exception(self):
        """Test that is_handled_exception correctly identifies AssessmentNotSelectedException."""

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)

        result = middleware.is_handled_exception(AssessmentNotSelectedException())

        self.assertTrue(result)

    def test_is_handled_exception_returns_false_for_other_exceptions(self):
        """Test that is_handled_exception returns False for other exceptions."""

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)

        test_exceptions = [
            ValueError("test"),
            KeyError("test"),
            AttributeError("test"),
            Exception("test"),
        ]

        for exception in test_exceptions:
            with self.subTest(exception=type(exception).__name__):
                result = middleware.is_handled_exception(exception)
                self.assertFalse(result)

    @patch("webcaf.middleware.redirect")
    def test_handle_exception_returns_redirect_response(self, mock_redirect):
        """Test that handle_exception returns the redirect response."""
        mock_redirect.return_value = HttpResponse(status=302, headers={"Location": "/view-draft-assessments/"})

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)

        response = middleware.handle_exception(self.request, AssessmentNotSelectedException())

        mock_redirect.assert_called_once_with("view-draft-assessments")
        self.assertEqual(response.status_code, 302)

    @patch("webcaf.middleware.AbstractAssessmentErrorHandlerMiddleware.logger")
    def test_authenticated_staff_on_admin_path_returns_none(self, mock_logger):
        """Staff users on admin paths should return None."""

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentNotSelectedHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=1200, is_authenticated=True, is_staff=True)
        self.request.path = "/admin/webcaf/assessment/"

        response = middleware.process_exception(self.request, AssessmentNotSelectedException())

        # Should return None for staff on admin path
        self.assertIsNone(response)

        # Verify logging occurred
        mock_logger.warning.assert_called_once_with("Handle assessment retrieval issue %s", "/admin/webcaf/assessment/")
