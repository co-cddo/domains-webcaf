from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView

from webcaf.webcaf.models import UserProfile


class Index(TemplateView):
    """
    Landing page
    """

    template_name = "index.html"


class MyAccountView(LoginRequiredMixin, TemplateView):
    """
    Initial page after authentication
    """

    template_name = "user-pages/my-account.html"
    login_url = "/oidc/authenticate/"  # OIDC login route


class MyOrganisationView(LoginRequiredMixin, TemplateView):
    """
    Current users organisation details view screen.
    """

    template_name = "user-pages/my-organisation.html"
    login_url = "/oidc/authenticate/"  # OIDC login route

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        profile = UserProfile.objects.filter(user=self.request.user).first()
        data["breadcrumbs"] = [{"url": reverse("my-account"), "text": "back"}]
        if profile:
            data["profile"] = profile
        return data


def logout_view(request):
    """
    Handle any cleanup and redirect to the oidc cleanup.
    We cannot reset the session here as the OIDC logout depends on the session data
    :param request:
    :return:
    """
    return redirect("oidc_logout")  # redirect to OIDC logout
