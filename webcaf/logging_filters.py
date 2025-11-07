import logging

from webcaf.middleware import log_context


class RequestLogFilter(logging.Filter):
    """
    Custom logging filter for enriching log records with contextual information.

    This class is designed to inject user and session-related information
    into log records. It retrieves context from a predefined source and
    attaches relevant details, such as user ID and session ID, enhancing
    the log entry for improved debugging and tracing purposes.

    :ivar user_id: Represents the user ID extracted from the logging context.
    :type user_id: str
    :ivar session_id: Represents the session ID extracted from the logging context.
    :type session_id: str
    """

    def filter(self, record):
        ctx = log_context.get() or {}
        user_id = ctx.get("user_id", "-")
        session_id = ctx.get("session_id", "-")
        record.user_id = user_id
        record.session_id = session_id
        return True
