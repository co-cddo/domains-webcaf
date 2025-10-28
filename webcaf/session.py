"""
Django middleware to automatically log out users after a period of inactivity.

This middleware checks if a user is authenticated and verified. If they are,
it tracks their last activity time stored in the session. If the time since
their last activity exceeds the `USER_IDLE_TIMEOUT` setting, the user is
redirected to an "expire-session" URL, effectively logging them out.

Key behaviors:
- Only applies to users who pass the `is_verified()` check.
- Resets the `last_activity` timestamp in the session on each request.
- Excludes the session expiration URL (`session-expired`) and the logout
  URL (`expire-session`) from the timeout logic to prevent redirect loops.
- Includes a special case for the root path (`/`): if a user times out
  on the root path (e.g., from a closed tab), their session is flushed
  without a redirect to avoid unnecessary page loads.
"""

import logging
import time

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

# Get an instance of the logger
logger = logging.getLogger(__name__)


class CafSessionTimeoutMiddleware:
    """
    Implements session timeout logic based on user inactivity.

    Checks the time since the user's last activity against the
    `USER_IDLE_TIMEOUT` setting. If the user is verified and has been
    idle for too long, they are redirected to the session expiration page.
    """

    def __init__(self, get_response):
        """
        Initializes the middleware.

        Args:
            get_response: The next middleware or view in the Django chain.
        """
        self.get_response = get_response

    def __call__(self, request):
        """
        Processes the request to check for session timeout.

        Args:
            request: The HttpRequest object.

        Returns:
            The HttpResponse object.
        """
        # Check if the user is authenticated and verified
        if request.user.is_authenticated:
            session_expired_url = reverse("session-expired")

            # Avoid processing timeout logic on the expiry/logout pages
            if request.path not in [session_expired_url]:
                last_activity = request.session.get("last_activity")
                timeout_seconds = settings.USER_IDLE_TIMEOUT

                if last_activity and (time.time() - last_activity) > timeout_seconds:
                    user_id = request.user.pk
                    # Special case: If the user times out on the root path,
                    # likely from a closed tab, just flush the session
                    # without redirecting.
                    if request.path == "/":
                        logger.info("User %s timed out on root path. Flushing session.", user_id)
                        request.session.flush()
                        # Continue processing the request (now as an anonymous user)
                        response = self.get_response(request)
                        return response
                    else:
                        # For all other pages, redirect to the explicit
                        # session expiration page.
                        logger.info("User %s timed out. Redirecting to expire-session.", user_id)
                        return redirect("session-expired")

                # Update the last activity time for the current request
                # Use debug level for this as it's frequent
                logger.debug("Updating last_activity for user %s.", request.user.pk)
                request.session["last_activity"] = time.time()

        # Continue processing the request
        response = self.get_response(request)
        return response
