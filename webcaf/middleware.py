import contextvars
import hashlib
import hmac
import logging
from abc import abstractmethod

from django.shortcuts import redirect, render
from django.utils.deprecation import MiddlewareMixin

log_context: contextvars.ContextVar = contextvars.ContextVar("log_context", default={})


class RequestLoggingMiddleware:
    """
    Middleware for logging request context.

    Stores lightweight request metadata (user_id, session_id) in a
    contextvar to enable correlation of log entries with the current request.

    This is safe for both synchronous and asynchronous request processing.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Extract user/session info
        user = getattr(request, "user", None)
        session = getattr(request, "session", None)
        # Build context data
        context_data = {
            "user_id": str(user.id) if user and hasattr(user, "id") and user.is_authenticated else "-",
            "session_id": self.hash_session_key(session.session_key if session and session.session_key else "-"),
        }

        # Set context and keep token for safe reset
        token = log_context.set(context_data)
        response = None
        try:
            # Process the request (call next middleware/view)
            response = self.get_response(request)
            return response
        finally:
            # If there's a response, add header to be picked up by Gunicorn
            if response is not None and context_data and "session_id" in context_data:
                response["trace_id"] = context_data.get("session_id")
            elif response:
                response["trace_id"] = "-"
            # Always clean up context — even on exceptions
            if token:
                log_context.reset(token)

    def hash_session_key(self, session_key: str) -> str:
        """
        Hashes the given session key using the application secret key and truncates the
        result for readability. This method provides a secure way to hash session keys
        while maintaining brevity in the output. If the session key is invalid or not
        provided, it will return the key as is.

        :param session_key: The session key to be hashed
        :type session_key: str
        :return: The truncated hash of the session key or the session key itself if it
                 is invalid
        :rtype: str
        """
        if session_key and session_key != "-":
            from django.conf import settings

            return hmac.new(settings.SECRET_KEY.encode(), session_key.encode(), hashlib.sha256).hexdigest()[
                :8
            ]  # truncate for readability
        return session_key


class AbstractAssessmentErrorHandlerMiddleware(MiddlewareMixin):
    """
    Middleware to handle exceptions related to non-existent assessments and redirect users accordingly.

    This middleware is designed to catch `Assessment.DoesNotExist` exceptions that occur during the processing of
    requests. It logs detailed information about the error, including the user ID if available, and selectively
    redirects users to an informational page based on their authentication and request details. Staff and
    authenticated users in an admin-specific context are allowed to see the original error.

    :ivar logger: Logger instance for logging exceptions related to assessment errors.
    :type logger: logging.Logger
    """

    logger = logging.getLogger("AssessmentErrorHandlerMiddleware")

    def process_exception(self, request, exception):
        """
        Called automatically if a view raises an exception.
        """

        if not self.is_handled_exception(exception):
            return None  # Let Django handle other exceptions

        user = getattr(request, "user", None)
        self.logger.warning("Handle assessment retrieval issue %s", request.path)
        # Let admins/staff see real errors
        if request.path.startswith("/admin/") or (user and user.is_authenticated and user.is_staff):
            return None

        return self.handle_exception(request, exception)

    @abstractmethod
    def is_handled_exception(self, exception):
        pass

    @abstractmethod
    def handle_exception(self, request, exception):
        pass


class AssessmentDoesNotExistHandlerMiddleware(AbstractAssessmentErrorHandlerMiddleware):
    """
    Middleware to handle exceptions related to non-existent assessments and redirect users accordingly.

    This middleware is designed to catch `Assessment.DoesNotExist` exceptions that occur during the processing of
    requests. It logs detailed information about the error, including the user ID if available, and selectively
    redirects users to an informational page based on their authentication and request details. Staff and
    authenticated users in an admin-specific context are allowed to see the original error.

    :ivar logger: Logger instance for logging exceptions related to assessment errors.
    :type logger: logging.Logger
    """

    def is_handled_exception(self, exception):
        # Need to import locally to avoid initialisation errors
        from webcaf.webcaf.models import Assessment

        return isinstance(exception, Assessment.DoesNotExist)

    def handle_exception(self, request, exception):
        return render(
            request, "404.html", context={"assessment_not_found": "Assessment could not be found."}, status=404
        )


class AssessmentNotSelectedHandlerMiddleware(AbstractAssessmentErrorHandlerMiddleware):
    """
    Handles exceptions related to unselected assessments.

    This middleware is responsible for intercepting and handling exceptions
    specific to cases where an assessment has not been selected. It checks
    if the raised exception is of the type `AssessmentNotSelectedException`
    and processes it accordingly.

    :ivar _handled_exception: A flag or property indicating if the exception
        has been handled.
    :type _handled_exception: bool
    """

    def is_handled_exception(self, exception):
        from webcaf.webcaf.views.general import AssessmentNotSelectedException

        return isinstance(exception, AssessmentNotSelectedException)

    def handle_exception(self, request, exception):
        return redirect("view-draft-assessments")
