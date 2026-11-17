import logging

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import CreateView, FormView, TemplateView, UpdateView

from webcaf.webcaf.forms.general import NextActionForm
from webcaf.webcaf.forms.system import SystemForm
from webcaf.webcaf.models import Configuration, System, UserProfile
from webcaf.webcaf.notification import send_notify_email
from webcaf.webcaf.utils import mask_email
from webcaf.webcaf.utils.permission import PermissionUtil, UserRoleCheckMixin
from webcaf.webcaf.utils.session import SessionUtil


class SystemContextDataMixin:
    def get_context_data(self, **kwargs):
        data = FormView.get_context_data(self, **kwargs)
        data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        data["current_assessment_period"] = Configuration.objects.get_default_config().get_current_assessment_period()
        data["breadcrumbs"] = [{"url": reverse("my-account"), "text": "Back", "class": "govuk-back-link"}]
        return data


class SystemViewMixin(UserRoleCheckMixin, SystemContextDataMixin):
    """
    Base utility methods for adding and editing systems.
    Only cyber_advisors can maintain systems
    """

    logger = logging.getLogger("SystemView")

    def get_allowed_roles(self) -> list[str]:
        return ["cyber_advisor"]

    def form_valid(self, form):
        current_profile_id = self.request.session.get("current_profile_id")
        current_profile = UserProfile.objects.filter(user=self.request.user, id=current_profile_id).get()
        if form.cleaned_data["action"] == "change":
            return self.form_invalid(form)

        if System.objects.filter(organisation=current_profile.organisation, name=form.cleaned_data["name"]).exists():
            form.add_error("name", f"A system with this name {form.cleaned_data['name']} already exists.")
            return self.form_invalid(form)

        form.instance.organisation = current_profile.organisation
        response = super().form_valid(form)
        self.send_new_system_email(form.instance)
        return response

    def send_new_system_email(self, system: System) -> None:
        """
        Sends a notification email when a new system is created to organisation leads
        and the GovAssure mailbox.
        :param system: newly created system
        :return: None
        """
        if template_id := settings.NOTIFY_NEW_SYSTEM_TEMPLATE_ID:
            try:
                if email_addresses := system.organisation.default_email_recipients():
                    send_notify_email(
                        email_addresses=email_addresses,
                        personalisation_data={
                            "system_name": system.name,
                            "organisation_name": system.organisation.name,
                        },
                        template_id=template_id,
                    )
            except Exception as ex:  # type: ignore
                self.logger.exception(mask_email(f"GOV.UK Notify: Failed to send new system email {ex}"))
        else:
            self.logger.info("GOV.UK Notify: No template ID provided for new system email")

    def form_invalid(self, form):
        # Capture the first user input, which may later be flagged
        # if there are unconfirmed changes.
        if len(form.errors) == 1 and "action" in form.errors:
            current_profile = SessionUtil.get_current_user_profile(self.request)
            return render(
                self.request, "system/system-confirm.html", {"form": form, "current_profile": current_profile}
            )
        return FormView.form_invalid(self, form)


class CreateSystemView(SystemViewMixin, CreateView):
    form_class = SystemForm
    model = System
    template_name = "system/system.html"
    login_url = "/oidc/authenticate/"
    success_url = "/view-systems/"
    """
    Provide create system view
    """


class EditSystemView(SystemViewMixin, UpdateView):
    slug_field = "uid"
    slug_url_kwarg = "system_uid"
    template_name = "system/system.html"
    login_url = "/oidc/authenticate/"
    success_url = "/view-systems/"
    form_class = SystemForm
    model = System

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

    def get_queryset(self):
        queryset = super().get_queryset()
        current_profile = SessionUtil.get_current_user_profile(self.request)
        return queryset.filter(organisation=current_profile.organisation)


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
        data["breadcrumbs"] = [{"url": reverse("my-account"), "text": "Back", "class": "govuk-back-link"}]
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
