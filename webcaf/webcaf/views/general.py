from typing import Any

from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView


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
                "text": "Edit draft assessment",
                "url": reverse_lazy(
                    "edit-draft-assessment",
                    kwargs={"assessment_id": self.request.session["draft_assessment"]["assessment_id"]},
                ),
            }
        ]


def logout_view(request):
    """
    Handle any cleanup and redirect to the oidc cleanup.
    We cannot reset the session here as the OIDC logout depends on the session data
    :param request:
    :return:
    """
    return redirect("oidc_logout")  # redirect to OIDC logout
