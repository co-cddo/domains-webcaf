"""
Tests for AssessmentDoesNotExistHandlerMiddleware.

This module verifies that Assessment.DoesNotExist exceptions are handled correctly,
with appropriate redirects for regular users and returning None for staff/admin users
to allow Django's default exception handling.
"""

from unittest.mock import Mock, patch

from django.http import HttpRequest, HttpResponse
from django.test import SimpleTestCase

from webcaf.middleware import AssessmentDoesNotExistHandlerMiddleware
from webcaf.webcaf.models import Assessment


class AssessmentDoesNotExistHandlerMiddlewareTest(SimpleTestCase):
    """Test suite for AssessmentDoesNotExistHandlerMiddleware."""

    def setUp(self):
        """Set up test fixtures."""
        self.request = HttpRequest()
        self.request.path = "/assessment/123/"
        self.request.META = {"HTTP_ACCEPT": "text/html"}

    def test_middleware_passes_through_successful_response(self):
        """When no exception occurs, the middleware should pass the response through."""

        def get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentDoesNotExistHandlerMiddleware(get_response)
        response = middleware(self.request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Success")

    @patch("webcaf.middleware.render")
    @patch("webcaf.middleware.AssessmentDoesNotExistHandlerMiddleware.logger")
    def test_authenticated_non_staff_user_receives_404_error_page(self, mock_logger, mock_render):
        """Authenticated non-staff users should see the 404 error page with custom message."""
        mock_render.return_value = HttpResponse("Error page", status=404)

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentDoesNotExistHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=42, is_authenticated=True, is_staff=False)
        self.request.path = "/edit-assessment/456/"

        response = middleware.process_exception(self.request, Assessment.DoesNotExist("Assessment not found"))

        # Verify logging occurred with path
        mock_logger.warning.assert_called_once_with("Handle assessment retrieval issue %s", "/edit-assessment/456/")

        # Verify render was called with correct parameters
        mock_render.assert_called_once_with(
            self.request, "404.html", context={"assessment_not_found": "Assessment could not be found."}, status=404
        )
        self.assertEqual(response.status_code, 404)

    @patch("webcaf.middleware.AssessmentDoesNotExistHandlerMiddleware.logger")
    def test_staff_user_returns_none_for_default_handling(self, mock_logger):
        """Staff users should get None return to allow Django's default exception handling."""

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentDoesNotExistHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=99, is_authenticated=True, is_staff=True)
        self.request.path = "/assessment/789/"

        response = middleware.process_exception(self.request, Assessment.DoesNotExist("Assessment not found"))

        # Verify logging still occurred
        mock_logger.warning.assert_called_once_with("Handle assessment retrieval issue %s", "/assessment/789/")

        # Should return None to let Django handle it
        self.assertIsNone(response)

    @patch("webcaf.middleware.AssessmentDoesNotExistHandlerMiddleware.logger")
    def test_admin_path_returns_none_for_default_handling(self, mock_logger):
        """Requests to /admin/ paths should return None to allow Django's default exception handling."""

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentDoesNotExistHandlerMiddleware(mock_get_response)
        self.request.path = "/admin/webcaf/assessment/"
        self.request.user = Mock(id=55, is_authenticated=True, is_staff=False)

        response = middleware.process_exception(self.request, Assessment.DoesNotExist("Assessment not found"))

        # Verify logging occurred
        mock_logger.warning.assert_called_once_with("Handle assessment retrieval issue %s", "/admin/webcaf/assessment/")

        # Should return None to let Django handle it
        self.assertIsNone(response)

    @patch("webcaf.middleware.render")
    @patch("webcaf.middleware.AssessmentDoesNotExistHandlerMiddleware.logger")
    def test_request_without_user_attribute_shows_error_page(self, mock_logger, mock_render):
        """When request lacks a user attribute, should show error page."""
        mock_render.return_value = HttpResponse("Error page", status=404)

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentDoesNotExistHandlerMiddleware(mock_get_response)
        # Remove user attribute from request
        if hasattr(self.request, "user"):
            delattr(self.request, "user")
        self.request.path = "/assessment/999/"

        response = middleware.process_exception(self.request, Assessment.DoesNotExist("Assessment not found"))

        # Verify logging occurred
        mock_logger.warning.assert_called_once_with("Handle assessment retrieval issue %s", "/assessment/999/")

        # Should show error page
        mock_render.assert_called_once_with(
            self.request, "404.html", context={"assessment_not_found": "Assessment could not be found."}, status=404
        )
        self.assertEqual(response.status_code, 404)

    @patch("webcaf.middleware.render")
    @patch("webcaf.middleware.AssessmentDoesNotExistHandlerMiddleware.logger")
    def test_error_message_content_in_context(self, mock_logger, mock_render):
        """Verify the exact error message passed to the template context."""
        mock_render.return_value = HttpResponse("Error page", status=404)

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentDoesNotExistHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=100, is_authenticated=True, is_staff=False)
        self.request.path = "/assessment/111/"

        middleware.process_exception(self.request, Assessment.DoesNotExist("Assessment not found"))

        # Extract the context argument from the render call
        call_args = mock_render.call_args
        context = call_args[1]["context"]

        self.assertEqual(context["assessment_not_found"], "Assessment could not be found.")

    @patch("webcaf.middleware.AssessmentDoesNotExistHandlerMiddleware.logger")
    def test_staff_status_takes_precedence(self, mock_logger):
        """When user is staff, should return None regardless of path."""

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentDoesNotExistHandlerMiddleware(mock_get_response)
        # Staff user making request to non-admin path
        self.request.user = Mock(id=200, is_authenticated=True, is_staff=True)
        self.request.path = "/assessment/view/"

        response = middleware.process_exception(self.request, Assessment.DoesNotExist("Assessment not found"))

        # Should return None for staff users
        self.assertIsNone(response)

        # Verify logging occurred
        mock_logger.warning.assert_called_once_with("Handle assessment retrieval issue %s", "/assessment/view/")

    @patch("webcaf.middleware.AssessmentDoesNotExistHandlerMiddleware.logger")
    def test_admin_path_variations(self, mock_logger):
        """Test various admin path patterns return None."""
        test_paths = [
            "/admin/",
            "/admin/webcaf/",
            "/admin/webcaf/assessment/123/",
            "/admin/auth/user/",
        ]

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentDoesNotExistHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=300, is_authenticated=False, is_staff=False)

        for path in test_paths:
            with self.subTest(path=path):
                self.request.path = path
                mock_logger.reset_mock()

                response = middleware.process_exception(self.request, Assessment.DoesNotExist("Assessment not found"))

                # Should return None for admin paths
                self.assertIsNone(response)

                # Verify logging occurred
                mock_logger.warning.assert_called_once_with("Handle assessment retrieval issue %s", path)

    @patch("webcaf.middleware.render")
    @patch("webcaf.middleware.AssessmentDoesNotExistHandlerMiddleware.logger")
    def test_non_admin_path_variations(self, mock_logger, mock_render):
        """Test various non-admin paths that should show error page."""
        mock_render.return_value = HttpResponse("Error page", status=404)

        test_paths = [
            "/assessment/",
            "/assessment/123/",
            "/dashboard/",
            "/user/profile/",
            "/not-admin/something/",
        ]

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentDoesNotExistHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=400, is_authenticated=False, is_staff=False)

        for path in test_paths:
            with self.subTest(path=path):
                self.request.path = path
                mock_logger.reset_mock()
                mock_render.reset_mock()

                response = middleware.process_exception(self.request, Assessment.DoesNotExist("Assessment not found"))

                self.assertEqual(response.status_code, 404)

                # Verify logging occurred
                mock_logger.warning.assert_called_once_with("Handle assessment retrieval issue %s", path)

    def test_other_exceptions_return_none(self):
        """Other exceptions should return None to let Django handle them."""

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentDoesNotExistHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=600, is_authenticated=False, is_staff=False)
        self.request.path = "/some/path/"

        response = middleware.process_exception(self.request, ValueError("Some other error"))

        # Should return None for non-Assessment.DoesNotExist exceptions
        self.assertIsNone(response)

    @patch("webcaf.middleware.render")
    @patch("webcaf.middleware.AssessmentDoesNotExistHandlerMiddleware.logger")
    def test_authenticated_staff_false_user_shows_error_page(self, mock_logger, mock_render):
        """Authenticated users with is_staff=False should see error page."""
        mock_render.return_value = HttpResponse("Error page", status=404)

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentDoesNotExistHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=700, is_authenticated=True, is_staff=False)
        self.request.path = "/assessment/222/"

        response = middleware.process_exception(self.request, Assessment.DoesNotExist("Assessment not found"))

        mock_render.assert_called_once()
        self.assertEqual(response.status_code, 404)

    @patch("webcaf.middleware.AssessmentDoesNotExistHandlerMiddleware.logger")
    def test_unauthenticated_staff_user_on_admin_path_returns_none(self, mock_logger):
        """Even unauthenticated users on /admin/ paths should return None."""

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentDoesNotExistHandlerMiddleware(mock_get_response)
        self.request.user = Mock(is_authenticated=False, is_staff=False)
        self.request.path = "/admin/login/"

        response = middleware.process_exception(self.request, Assessment.DoesNotExist("Assessment not found"))

        # Admin path should return None regardless of authentication
        self.assertIsNone(response)

    @patch("webcaf.middleware.render")
    @patch("webcaf.middleware.AssessmentDoesNotExistHandlerMiddleware.logger")
    def test_template_name_is_404_html(self, mock_logger, mock_render):
        """Verify the correct template name (404.html) is used."""
        mock_render.return_value = HttpResponse("Error page", status=404)

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentDoesNotExistHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=800, is_authenticated=False, is_staff=False)
        self.request.path = "/assessment/333/"

        middleware.process_exception(self.request, Assessment.DoesNotExist("Assessment not found"))

        # Check the template name
        call_args = mock_render.call_args
        template_name = call_args[0][1]
        self.assertEqual(template_name, "404.html")

    @patch("webcaf.middleware.render")
    @patch("webcaf.middleware.AssessmentDoesNotExistHandlerMiddleware.logger")
    def test_status_code_is_404(self, mock_logger, mock_render):
        """Verify the status code is 404, not 500."""
        mock_render.return_value = HttpResponse("Error page", status=404)

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentDoesNotExistHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=900, is_authenticated=False, is_staff=False)
        self.request.path = "/assessment/444/"

        middleware.process_exception(self.request, Assessment.DoesNotExist("Assessment not found"))

        # Check the status code parameter
        call_args = mock_render.call_args
        status = call_args[1]["status"]
        self.assertEqual(status, 404)

    @patch("webcaf.middleware.AssessmentDoesNotExistHandlerMiddleware.logger")
    def test_logger_uses_warning_not_exception(self, mock_logger):
        """Verify logger.warning is called, not logger.exception."""

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentDoesNotExistHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=1000, is_authenticated=False, is_staff=False)
        self.request.path = "/assessment/555/"

        middleware.process_exception(self.request, Assessment.DoesNotExist("Assessment not found"))

        # Verify warning is called, not exception
        mock_logger.warning.assert_called_once()
        mock_logger.exception.assert_not_called()

    @patch("webcaf.middleware.render")
    @patch("webcaf.middleware.AssessmentDoesNotExistHandlerMiddleware.logger")
    def test_multiple_calls_with_different_paths(self, mock_logger, mock_render):
        """Test that path is correctly logged for multiple different calls."""
        mock_render.return_value = HttpResponse("Error page", status=404)

        def mock_get_response(_req):
            return HttpResponse("Success", status=200)

        middleware = AssessmentDoesNotExistHandlerMiddleware(mock_get_response)
        self.request.user = Mock(id=1100, is_authenticated=False, is_staff=False)

        paths = ["/assessment/1/", "/assessment/2/", "/assessment/3/"]

        for path in paths:
            with self.subTest(path=path):
                mock_logger.reset_mock()
                self.request.path = path

                middleware.process_exception(self.request, Assessment.DoesNotExist("Assessment not found"))

                mock_logger.warning.assert_called_once_with("Handle assessment retrieval issue %s", path)
