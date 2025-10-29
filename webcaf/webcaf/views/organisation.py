from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import ModelForm
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import FormView, TemplateView

from webcaf.webcaf.models import Organisation, UserProfile


class OrganisationContactForm(ModelForm):
    """
    Update the contact details of an organisation
    """

    class Meta:
        model = Organisation
        fields = ["contact_name", "contact_role", "contact_email"]


class OrganisationTypeForm(ModelForm):
    """
    Update organisation type of organisation
    """

    class Meta:
        model = Organisation
        fields = ["organisation_type"]


class OrganisationForm(ModelForm):
    """
    Update all the information of an organisation
    """

    class Meta:
        model = Organisation
        fields = "__all__"


class OrganisationView(LoginRequiredMixin, FormView):
    """
    OrganisationView is responsible for handling the organisation form view for a
    logged-in user. It enforces authentication requirements and ensures that a user
    can only access and modify their own associated organisation.

    This view includes methods to retrieve user-specific context data, fetch the
    associated organisation object, and handle instance binding for forms. The
    primary use case revolves around ensuring secure and restricted access to
    profile and organisation data, enabling user-specific actions in a controlled
    manner.

    :ivar login_url: The URL used to redirect unauthenticated users for login.
    :type login_url: str
    """

    login_url = "/oidc/authenticate/"  # OIDC login route

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        profile_id = self.kwargs.get("id")
        # Ensure that the claimed profile belongs to teh current user
        profile = UserProfile.objects.get(user=self.request.user, id=profile_id)
        data["breadcrumbs"] = [{"url": reverse("my-account"), "text": "Back", "class": "govuk-back-link"}]
        data["profile"] = profile
        return data

    def get_object(self):
        """
        Get the object to be updated based on the current user profile and the selected
        profile id. This makes sure that the given user can only modify allowed profiles.
        :return:
        """
        return UserProfile.objects.get(user=self.request.user, id=self.kwargs.get("id")).organisation

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.get_object()
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class OrganisationTypeView(OrganisationView):
    """
    A Django view class for handling the organisation type page.

    This view is used to display and process forms related to the organisation
    type. It inherits from OrganisationView and includes additional
    functionality for handling success URLs.

    :ivar template_name: Path to the template used for rendering the page.
    :type template_name: str
    :ivar form_class: The form class associated with the view.
    :type form_class: type
    """

    template_name = "user-pages/organisation-type.html"
    form_class = OrganisationTypeForm

    def get_success_url(self):
        return reverse("edit-my-organisation-contact", kwargs={"id": self.kwargs["id"]})


class OrganisationContactView(OrganisationView):
    """
    Represents a view for handling the organisation contact form in a web
    application.

    This class provides functionality specific to the "organisation contact"
    page, such as rendering the contact form using a template and determining
    the URL to redirect to upon successful form submission. It extends the
    base class `OrganisationView` to include additional methods and attributes
    for contact-specific functionality.

    :ivar template_name: Path to the HTML template used for rendering the
        "organisation contact" page.
    :type template_name: str
    :ivar form_class: The Django form class used for handling contact
        information in the organisation contact page.
    :type form_class: type
    """

    template_name = "user-pages/organisation-contact.html"
    form_class = OrganisationContactForm

    def get_success_url(self):
        return reverse("my-organisation", kwargs={"id": self.kwargs["id"]})


class MyOrganisationView(OrganisationView):
    """
    Present the read-only view of the organisation.
    """

    template_name = "user-pages/my-organisation.html"
    form_class = OrganisationForm


class ChangeActiveProfileView(LoginRequiredMixin, TemplateView):
    """
    Organisation change screen.
    """

    template_name = "user-pages/change-organisation.html"
    login_url = "/oidc/authenticate/"  # OIDC login route

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        profiles = UserProfile.objects.filter(user=self.request.user)
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
            profile = UserProfile.objects.filter(user=self.request.user, id=profile_id).first()
            if profile:
                self.request.session["current_profile_id"] = profile.id
            else:
                return render(request, "user-pages/no-profile-setup.html", status=403)
        return redirect(reverse("my-account"))
