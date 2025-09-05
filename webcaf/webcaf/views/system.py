from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.forms import ChoiceField, ModelForm
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import FormView, TemplateView, UpdateView

from webcaf.webcaf.forms.general import NextActionForm
from webcaf.webcaf.models import System, UserProfile
from webcaf.webcaf.utils.permission import PermissionUtil, UserRoleCheckMixin
from webcaf.webcaf.utils.session import SessionUtil


class SystemForm(ModelForm):
    action = ChoiceField(
        choices=[("change", "Change"), ("confirm", "Confirm")],
        required=True,
    )

    class Meta:
        model = System
        fields = [
            "name",
            "description",
            "system_owner",
            "system_type",
            "hosting_type",
            "internet_facing",
            "last_assessed",
        ]
        labels = {
            "name": "System name",
            "system_type": "System type",
            "description": "Essential services",
            "system_owner": "System ownership",
            "hosting_type": "Hosting and connectivity",
            "internet_facing": "Internet facing",
            "last_assessed": "GovAssure year",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True


class SystemContextDataMixin:
    def get_context_data(self, **kwargs):
        data = FormView.get_context_data(self, **kwargs)
        data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        data["system_types"] = System.SYSTEM_TYPES
        data["owner_types"] = System.OWNER_TYPES
        data["hosting_types"] = System.HOSTING_TYPES
        data["assessed_periods"] = System.ASSESSED_CHOICES
        data["internet_facing"] = System.INTERNET_FACING
        return data

    def form_invalid(self, form):
        # Capture the first instance of the user input, where we would get flagged
        # for unconfirmed changes.
        if len(form.errors) == 1 and "action" in form.errors:
            current_profile = SessionUtil.get_current_user_profile(self.request)
            return render(
                self.request, "system/system-confirm.html", {"form": form, "current_profile": current_profile}
            )
        return FormView.form_invalid(self, form)


class SystemView(UserRoleCheckMixin, SystemContextDataMixin, FormView):
    template_name = "system/system.html"
    login_url = "/oidc/authenticate/"
    success_url = "/view-systems/"
    form_class = SystemForm

    def get_allowed_roles(self) -> list[str]:
        return ["cyber_advisor", "organisation_lead"]

    def form_valid(self, form):
        current_profile_id = self.request.session.get("current_profile_id")
        current_profile = UserProfile.objects.filter(user=self.request.user, id=current_profile_id).get()
        if System.objects.filter(organisation=current_profile.organisation, name=form.cleaned_data["name"]).exists():
            form.add_error("name", f"A system with this name {form.cleaned_data['name']} already exists.")
            return self.form_invalid(form)
        instance = form.save(commit=False)
        instance.organisation = current_profile.organisation
        instance.save()
        return super().form_valid(form)


class EditSystemView(SystemContextDataMixin, UserRoleCheckMixin, UpdateView):
    model = System
    form_class = SystemForm
    template_name = "system/system.html"
    pk_url_kwarg = "system_id"
    success_url = "/view-systems/"

    def get_allowed_roles(self) -> list[str]:
        return ["cyber_advisor"]

    def get_object(self, queryset=None):
        current_profile = SessionUtil.get_current_user_profile(self.request)
        system = super().get_object(queryset)
        if system.organisation != current_profile.organisation:
            raise PermissionDenied("You are not allowed to edit this system")
        return system

    def form_valid(self, form):
        # Forward the user back to the edit page as the action is not confirmed.
        if form.cleaned_data["action"] == "change":
            return self.form_invalid(form)

        current_profile = SessionUtil.get_current_user_profile(self.request)
        if form.instance.organisation != current_profile.organisation:
            form.add_error("name", "You are not allowed to edit this system")
            return self.form_invalid(form)
        form.save()
        return HttpResponseRedirect(self.get_success_url())


class ViewSystemsView(LoginRequiredMixin, TemplateView):
    template_name = "system/systems.html"
    login_url = "/oidc/authenticate/"
    success_url = "/systems/"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        user_profile = SessionUtil.get_current_user_profile(self.request)
        if not PermissionUtil.current_user_can_view_systems(user_profile):
            raise PermissionDenied("You are not allowed to view this page")

        data["current_profile"] = user_profile
        data["systems"] = System.objects.filter(organisation=data["current_profile"].organisation)
        return data


class CreateOrSkipSystemView(UserRoleCheckMixin, FormView):
    """
    Utility action to decide to create a new system or go back to the
    home screen.
    """

    def get_allowed_roles(self) -> list[str]:
        return ["cyber_advisor"]

    form_class = NextActionForm

    def form_valid(self, form):
        action = self.request.POST.get("action")
        if action == "confirm":
            return redirect(reverse("create-new-system"))

        return redirect(reverse("my-account"))

    def form_invalid(self, form):
        return redirect(reverse("view-systems"))
