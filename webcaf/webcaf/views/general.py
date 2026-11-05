import logging
from functools import wraps
from typing import Any
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import logout as django_logout
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.generic import FormView, TemplateView
from govuk_onelogin_django.utils import get_one_login_logout_url
from requests import RequestException

from webcaf.auth import EMAIL_DOMAIN_REJECTED_SESSION_KEY
from webcaf.webcaf.utils.session import SessionUtil


@method_decorator(never_cache, name="dispatch")
class Index(TemplateView):
    """
    Landing page
    """

    template_name = "index.html"


class AuthenticationErrorView(TemplateView):
    """Show a safe sign-in error without exposing authentication-provider details."""

    template_name = "authentication-error.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["email_domain_rejected"] = self.request.session.pop(EMAIL_DOMAIN_REJECTED_SESSION_KEY, False)
        return context


class AssessmentNotSelectedException(Exception):
    """
    Exception raised when an assessment is not selected.

    This exception is used to indicate that a required assessment has not
    been selected during an operation or process where it is mandatory.
    """

    pass


def assessment_required(func):
    """
    Decorator that ensures an assessment is selected before invoking the decorated function. It checks whether
    the "draft_assessment" session data contains a valid "assessment_id". If "assessment_id" is missing, an
    `AssessmentNotSelectedException` is raised.

    :param func: The function to be decorated.
    :return: The decorated function wrapped with the assessment validation logic.
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.request.session.get("draft_assessment", {}).get("assessment_id"):
            raise AssessmentNotSelectedException
        return func(self, *args, **kwargs)

    return wrapper


class FormViewWithBreadcrumbs(FormView):
    """
    Extension of the standard FormView class to include breadcrumb functionality.
    NOTE: Intended to be used in views where an assessment is being edited or created.

    This class provides additional support for dynamically appending breadcrumb
    links to the context data for rendering in templates. It is particularly useful
    for enhancing user navigation in views where step-by-step progress or a hierarchy
    is represented.

    :ivar breadcrumbs: List of breadcrumb dictionaries specifying the navigation
        links for the view.
    :type breadcrumbs: list[dict]
    """

    def get_context_data(self, **kwargs: Any):
        context_data = FormView.get_context_data(self, **kwargs)
        context_data["breadcrumbs"] = context_data["breadcrumbs"] + self.build_breadcrumbs()
        context_data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        return context_data

    def build_breadcrumbs(self):
        """
        Generate breadcrumb links for navigating to the draft assessment edit view.

        This method constructs a list of dictionaries where each dictionary represents
        a breadcrumb link with its display text and URL. It is primarily used for
        rendering navigation links in the user interface.

        :return: A list containing breadcrumb dictionaries. Each dictionary includes a
            'text' key for the display name of the breadcrumb and a 'url' key for the
            corresponding hyperlink.
        :rtype: list[dict[str, str]]
        """
        if not self.request.session.get("draft_assessment", {}).get("assessment_id"):
            raise AssessmentNotSelectedException

        return [
            {
                "text": "Edit draft self-assessment",
                "url": reverse_lazy(
                    "edit-draft-assessment",
                    kwargs={"assessment_id": self.request.session["draft_assessment"]["assessment_id"]},
                ),
            }
        ]


logout_view_logger = logging.getLogger("logout_view")


@require_POST
def logout_view(request):
    """End the local session and, where possible, the active provider session."""
    logout_view_logger.info("Logging out user %s", request.user.pk)
    logout_url = None

    if settings.SSO_MODE == "one-login":
        try:
            post_logout_redirect_uri = request.build_absolute_uri(reverse("index"))
            logout_url = get_one_login_logout_url(request, post_logout_redirect_uri)
        except (KeyError, RequestException, ValueError):
            logout_view_logger.exception("Unable to create the GOV.UK One Login logout URL")
    elif settings.SSO_MODE == "internal-access":
        # IA selects the return URL from the registered client's app_url.
        # Its sign-out endpoint does not use generic OIDC logout parameters.
        if settings.OIDC_OP_LOGOUT_ENDPOINT:
            query = urlencode({"to_client": settings.OIDC_RP_CLIENT_ID})
            logout_url = f"{settings.OIDC_OP_LOGOUT_ENDPOINT}?{query}"
    else:
        id_token = request.session.get("oidc_id_token")
        if id_token and settings.OIDC_OP_LOGOUT_ENDPOINT:
            query = urlencode(
                {
                    "id_token_hint": id_token,
                    "client_id": settings.OIDC_RP_CLIENT_ID,
                    "redirect_uri": settings.LOGOUT_REDIRECT_URL,
                }
            )
            logout_url = f"{settings.OIDC_OP_LOGOUT_ENDPOINT}?{query}"

    django_logout(request)
    return redirect(logout_url or "index")
