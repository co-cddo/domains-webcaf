import contextvars

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
            "session_id": session.session_key if session and session.session_key else "-",
        }

        # Set context and keep token for safe reset
        token = log_context.set(context_data)
        try:
            # Process the request (call next middleware/view)
            response = self.get_response(request)
            return response
        finally:
            # Always clean up context — even on exceptions
            if token:
                log_context.reset(token)
