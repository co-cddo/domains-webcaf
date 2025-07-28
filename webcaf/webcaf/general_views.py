from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
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

    def get_context_data(self, **kwargs):
        """
        Get the current user's profile and set the session variables.
        also set the request context for rendering.
        :param kwargs:
        :return:
        """
        data = super().get_context_data(**kwargs)
        profile_id = self.request.session.get("current_profile_id")
        if not profile_id:
            profiles = list(UserProfile.objects.filter(user=self.request.user).order_by("id").all())
            if profiles:
                self.request.session["current_profile_id"] = profiles[0].id
                self.request.session["profile_count"] = len(profiles)
        current_profile_id = self.request.session.get("current_profile_id")
        if current_profile_id:
            data["current_profile"] = UserProfile.objects.filter(user=self.request.user, id=current_profile_id).get()
            data["profile_count"] = self.request.session.get("profile_count", 1)
        return data

    def get(self, request, *args, **kwargs):
        data = self.get_context_data(**kwargs)
        if "current_profile" not in data:
            return render(self.request, "user-pages/no-profile-setup.html", status=403)
        return super().get(request, *args, **kwargs)


class MyOrganisationView(LoginRequiredMixin, TemplateView):
    """
    Provide the organisation details for the current user.
    this allows the user to change the organisation details based on the user permission.
    """

    login_url = "/oidc/authenticate/"  # OIDC login route

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        profile_id = kwargs.get("id")
        profile = UserProfile.objects.filter(user=self.request.user, id=profile_id).first()
        data["breadcrumbs"] = [{"url": reverse("my-account"), "text": "back", "class": "govuk-back-link"}]
        data["profile"] = profile
        return data

    def get_template_names(self):
        mode_to_html = {
            "view": "user-pages/my-organisation.html",
            "type": "user-pages/organisation-type.html",
            "contact": "user-pages/organisation-contact.html",
        }
        view_mode = self.kwargs.get("mode", "view")
        return [mode_to_html[view_mode]]

    def post(self, request, *args, **kwargs):
        # Mode and Id needs to exist for the request to come here
        view_mode = kwargs["mode"]
        profile_id = kwargs["id"]
        profile = UserProfile.objects.get(user=self.request.user, id=profile_id)
        match view_mode:
            case "type":
                #  Change organisation type
                profile.organisation.organisation_type = request.POST["organisation_type"]
                profile.organisation.save()
                return redirect("edit-my-organisation", id=profile_id, mode="contact")
            case "contact":
                profile.organisation.contact_name = request.POST["contact_name"]
                profile.organisation.contact_role = request.POST["contact_role"]
                profile.organisation.contact_email = request.POST["contact_email"]
                profile.organisation.save()
                return redirect("my-organisation", id=profile_id)
            case "_":
                return redirect("my-organisation", id=profile_id)


class ChangeOrganisationView(LoginRequiredMixin, TemplateView):
    """
    Organisation change screen.
    """

    template_name = "user-pages/change-organisation.html"
    login_url = "/oidc/authenticate/"  # OIDC login route

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        profiles = UserProfile.objects.filter(user=self.request.user)
        data["breadcrumbs"] = [{"url": reverse("my-account"), "text": "back", "class": "govuk-back-link"}]
        data["profiles"] = profiles
        return data

    def post(self, request, *args, **kwargs):
        """
        Set the current profile to the one selected in the form.
        Since the profile is attached to the organisation, this dictates what the current organisation is.
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        profile_id = request.POST.get("profile_id")
        if profile_id:
            profile = UserProfile.objects.filter(user=self.request.user, id=profile_id).first()
            if profile:
                self.request.session["current_profile_id"] = profile.id
            else:
                return render(request, "user-pages/no-profile-setup.html", status=403)
        return redirect(reverse("view-organisations"))


def logout_view(request):
    """
    Handle any cleanup and redirect to the oidc cleanup.
    We cannot reset the session here as the OIDC logout depends on the session data
    :param request:
    :return:
    """
    return redirect("oidc_logout")  # redirect to OIDC logout
