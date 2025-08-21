from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import TemplateView

from webcaf.webcaf.models import Assessment, System, UserProfile


class Index(TemplateView):
    """
    Landing page
    """

    template_name = "index.html"


class MyAccountView(LoginRequiredMixin, TemplateView):
    """
    Handles the user account view which provides user account management and displays specific
    profile-related data. It is accessible only to authenticated users and serves as an entry point
    for rendering user-specific data upon successful login.

    :ivar template_name: Path to the HTML template used for rendering the user account page.
    :type template_name: str
    :ivar login_url: URL to redirect unauthenticated users for login.
    :type login_url: str
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
            # On the landing of the very first time, select the first profile to be displayed
            # The user is allowed to change this later through the screen
            profiles = list(UserProfile.objects.filter(user=self.request.user).order_by("id").all())
            if profiles:
                self.request.session["current_profile_id"] = profiles[0].id
                self.request.session["profile_count"] = len(profiles)
        current_profile_id = self.request.session.get("current_profile_id")
        if current_profile_id:
            # Data used by the page.
            data["current_profile"] = UserProfile.objects.filter(user=self.request.user, id=current_profile_id).get()
            data["profile_count"] = self.request.session.get("profile_count", 1)
            data["system_count"] = System.objects.filter(organisation=data["current_profile"].organisation).count()
            data["draft_systems"] = list(
                Assessment.objects.filter(system__organisation=data["current_profile"].organisation, status="draft")
                .values(
                    "id",
                    "system__name",
                    "caf_profile",
                    "system__organisation__name",
                    "created_on",
                    "last_updated",
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


class MyAccountViewAssessmentsView(MyAccountView):
    """
    Represents a view for displaying draft assessments in the user's account.

    This class inherits from `MyAccountView` and sets the template for displaying
    draft assessments. It is used for rendering user-specific draft assessments
    on the corresponding user interface.

    :ivar template_name: The path to the HTML template file used for rendering
        the draft assessments page.
    :type template_name: str
    """

    template_name = "user-pages/draft-assessments.html"
