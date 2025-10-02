import time

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class CafSessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            session_expired_url = reverse("session-expired")
            logout_session_expired = reverse("expire-session")
            if request.path not in [session_expired_url, logout_session_expired, "/"]:
                last_activity = request.session.get("last_activity")
                timeout_seconds = settings.USER_IDLE_TIMEOUT

                if last_activity and (time.time() - last_activity) > timeout_seconds:
                    return redirect("expire-session")

                request.session["last_activity"] = time.time()

        response = self.get_response(request)
        return response
