import contextvars
import hashlib
import hmac

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
