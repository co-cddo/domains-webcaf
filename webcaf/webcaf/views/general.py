import logging
from typing import Any

from django.conf import settings
from django.contrib.auth import logout as django_logout
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import FormView, TemplateView


@method_decorator(never_cache, name="dispatch")
class Index(TemplateView):
    """
    Landing page
    """

    template_name = "index.html"


class FormViewWithBreadcrumbs(FormView):
    """
    Extension of the standard FormView class to include breadcrumb functionality.

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


def logout_view(request):
    """
    Handle any cleanup and redirect to the oidc cleanup.
    We cannot reset the session here as the OIDC logout depends on the session data
    :param request:
    :return:
    """
    logout_view_logger.info(f"Logging out user {request.user.pk}")
    id_token = request.session.get("oidc_id_token")  # make sure you store it at login
    # 1. Log out Django session
    django_logout(request)
    oidc_logout_url = settings.OIDC_OP_LOGOUT_ENDPOINT
    client_id = settings.OIDC_RP_CLIENT_ID
    redirect_url = settings.LOGOUT_REDIRECT_URL
    logout_url = f"{oidc_logout_url}?id_token_hint={id_token}&client_id={client_id}&redirect_uri={redirect_url}"
    return redirect(logout_url)
