import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import TemplateView

from webcaf.webcaf.models import UserProfile


class MyOrganisationView(LoginRequiredMixin, TemplateView):
    """
    Present the read-only view of the user's organisation.

    The page only displays the organisation. It accepts GET (and HEAD and OPTIONS) only,
    so organisation details, including the type and GSS code, can only be changed in
    Django Admin.
    """

    template_name = "user-pages/my-organisation.html"
    http_method_names = ["get", "head", "options"]

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        # Ensure that the claimed profile belongs to the current user
        profile = UserProfile.objects.get(user=self.request.user, id=self.kwargs.get("id"))
        data["breadcrumbs"] = [{"url": reverse("my-account"), "text": "Back", "class": "govuk-back-link"}]
        data["profile"] = profile
        return data


class ChangeActiveProfileView(LoginRequiredMixin, TemplateView):
    """
    Organisation change screen.
    """

    template_name = "user-pages/change-organisation.html"
    logger = logging.getLogger("ChangeActiveProfileView")

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        # Using select_related to optimize the query for related organisation
        profiles = (
            UserProfile.objects.filter(user=self.request.user)
            .select_related("organisation")
            .order_by("organisation__name")
        )
        data["breadcrumbs"] = [{"url": reverse("my-account"), "text": "Back", "class": "govuk-back-link"}]
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
            self.logger.info(f"The user {self.request.user.id} switching to  profile_id: {profile_id}")
            profile = UserProfile.objects.filter(user=self.request.user, id=profile_id).first()
            if profile:
                self.request.session["current_profile_id"] = profile.id
                self.request.current_profile = profile
            else:
                self.logger.error(f"The user {self.request.user.id} could not switch profile as not found")
                return render(request, "user-pages/no-profile-setup.html", status=403)
        return redirect(reverse("my-account"))
