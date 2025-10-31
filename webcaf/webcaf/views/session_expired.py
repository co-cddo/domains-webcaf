from django.contrib import auth
from django.shortcuts import render


def session_expired(request):
    """
    Logs out the user if they are authenticated,
    then displays the session timeout message page.
    """
    # Check if the user is authenticated
    if request.user.is_authenticated:
        auth.logout(request)
        request.session.flush()

    # In all cases, render the session timeout page
    return render(request, "session-timeout.html")
