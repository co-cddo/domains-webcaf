"""
Tests for RequestLoggingMiddleware.

This module verifies that request context is set using contextvars and that
session IDs are hashed securely and truncated for readability.
"""

import hashlib
import hmac

from django.http import HttpRequest, HttpResponse
from django.test import SimpleTestCase, override_settings

from webcaf.middleware import RequestLoggingMiddleware, log_context


@override_settings(DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}})
class RequestLoggingMiddlewareTest(SimpleTestCase):
    def setUp(self):
        self.request = HttpRequest()

    @override_settings(SECRET_KEY="test-secret-key")  # pragma: allowlist secret
    def test_session_id_hashed_when_session_key_present(self):
        """Session key should be hashed using SECRET_KEY and truncated to 8 chars."""

        class Session:
            session_key = "abc123-session-key"

        # Middleware that captures the context during processing
        captured_context = {}

        def get_response(_req):
            nonlocal captured_context
            captured_context = log_context.get()
            return HttpResponse("OK")

        middleware = RequestLoggingMiddleware(get_response)
        self.request.session = Session()
        self.request.user = type("U", (), {"is_authenticated": False})()

        response = middleware(self.request)
        self.assertEqual(response.status_code, 200)

        # Expected HMAC-SHA256 digest (truncate to 8 hex chars)
        expected = hmac.new(
            b"test-secret-key",
            b"abc123-session-key",
            hashlib.sha256,
        ).hexdigest()[:8]

        self.assertIn("session_id", captured_context)
        self.assertEqual(captured_context["session_id"], expected)
        # user_id should be "-" for unauthenticated users
        self.assertEqual(captured_context["user_id"], "-")

        # After the request finishes, context must be reset to default
        self.assertEqual(log_context.get(), {})

    @override_settings(SECRET_KEY="another-secret")  # pragma: allowlist secret
    def test_session_id_dash_when_no_session_or_key(self):
        """When no session or key provided, session_id should be '-' and returned as-is."""
        captured_context = {}

        def get_response(_req):
            nonlocal captured_context
            captured_context = log_context.get()
            return HttpResponse("OK")

        middleware = RequestLoggingMiddleware(get_response)

        # No session attached
        self.request.user = type("U", (), {"is_authenticated": False})()
        response = middleware(self.request)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(captured_context["session_id"], "-")
        self.assertEqual(captured_context["user_id"], "-")
        self.assertEqual(log_context.get(), {})

    @override_settings(SECRET_KEY="secret")  # pragma: allowlist secret
    def test_context_is_set_during_request_and_reset_after(self):
        """log_context should be populated during request and reset after processing."""

        class Session:
            session_key = "key"

        seen_during_request = None

        def get_response(_req):
            nonlocal seen_during_request
            seen_during_request = log_context.get()
            # Ensure it contains expected keys
            assert "user_id" in seen_during_request
            assert "session_id" in seen_during_request
            return HttpResponse("OK")

        middleware = RequestLoggingMiddleware(get_response)
        self.request.session = Session()
        self.request.user = type("U", (), {"is_authenticated": True, "id": 123})()

        response = middleware(self.request)
        self.assertEqual(response.status_code, 200)

        # During request, context should have the user_id and session_id populated
        self.assertIsNotNone(seen_during_request)
        self.assertEqual(seen_during_request["user_id"], "123")
        self.assertIsInstance(seen_during_request["session_id"], str)
        self.assertEqual(len(seen_during_request["session_id"]), 8)

        # After request, the context must be reset
        self.assertEqual(log_context.get(), {})
