# from django.conf import settings
from django.contrib import auth
from django.shortcuts import redirect, render


def session_expired_logout_user(request):
    """
    View to clear session, logout user and redirect to the session timeout page
    """
    if request.user.is_authenticated:
        auth.logout(request)
        request.session.flush()
        # # This will signout of the sso but we cannot rerdirect to a custom session expired page
        # # and will be redirected to the login page as configured in the sso client
        # return redirect(settings.SESSION_EXPIRED_LOGOUT_URL)

        # So can just load the session expired page
        return redirect("session-expired")

    else:
        return redirect("session-expired")


def session_expired_page(request):
    """A public page that displays the session timeout message."""
    return render(request, "session-timeout.html")
