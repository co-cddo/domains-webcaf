from django.contrib import auth
from django.shortcuts import render


def session_expired(request):
    """
    Logs out the user if they are authenticated and verified,
    then displays the session timeout message page.
    """
    # Check if the user is authenticated and verified
    if request.user.is_authenticated and request.user.is_verified():
        auth.logout(request)
        request.session.flush()

    # In all cases, render the session timeout page
    return render(request, "session-timeout.html")
