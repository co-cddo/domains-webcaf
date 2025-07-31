from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import TemplateView

from webcaf.webcaf.models import Assessment, UserProfile


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
            data["draft_systems"] = list(
                Assessment.objects.filter(system__organisation=data["current_profile"].organisation, status="draft")
                .values(
                    "id",
                    "system__name",
                    "caf_profile",
                    "system__organisation__name",
                    "created_on",
                    "assessment_period",
                    "created_by__username",
                )
                .all()
            )
            # Make swap the id to the label names
            profiles = dict(Assessment.PROFILE_CHOICES)
            for item in data["draft_systems"]:
                item["caf_profile"] = profiles.get(item["caf_profile"])
        return data

    def get(self, request, *args, **kwargs):
        """
        Initial page after logging in
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        data = self.get_context_data(**kwargs)
        # Set a draft assessment as empty as we are starting a new flow
        request.session["draft_assessment"] = {}
        if "current_profile" not in data:
            return render(self.request, "user-pages/no-profile-setup.html", status=403)
        return super().get(request, *args, **kwargs)
