from django.shortcuts import redirect


def logout_view(request):
    """
    Handle any cleanup and redirect to the oidc cleanup.
    We cannot reset the session here as the OIDC logout depends on the session data
    :param request:
    :return:
    """
    return redirect("oidc_logout")  # redirect to OIDC logout
