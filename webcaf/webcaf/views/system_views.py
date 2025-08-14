from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import ModelForm
from django.http import HttpResponseRedirect
from django.views.generic import FormView, TemplateView

from webcaf.webcaf.models import System, UserProfile


class SystemForm(ModelForm):
    class Meta:
        model = System
        fields = ["name", "description"]


class SystemView(LoginRequiredMixin, FormView):
    template_name = "system/system.html"
    login_url = "/oidc/authenticate/"
    success_url = "/view-systems/"
    form_class = SystemForm

    def get_context_data(self, **kwargs):
        current_profile_id = self.request.session.get("current_profile_id")
        data = super().get_context_data(**kwargs)
        user_profile = UserProfile.objects.filter(user=self.request.user, id=current_profile_id).get()
        data["current_profile"] = user_profile
        if user_profile.role != UserProfile.ROLE_CHOICES[0][0]:
            raise Exception("You are not allowed to view this page")
        return data

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


class EditSystemView(SystemView):
    def get_object(self):
        current_profile_id = self.request.session.get("current_profile_id")
        current_profile = UserProfile.objects.filter(user=self.request.user, id=current_profile_id).get()
        system = System.objects.get(id=self.kwargs["system_id"], organisation=current_profile.organisation)
        return system

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.get_object()
        return kwargs

    def form_valid(self, form):
        current_profile_id = self.request.session.get("current_profile_id")
        current_profile = UserProfile.objects.filter(user=self.request.user, id=current_profile_id).get()
        if not System.objects.filter(
            organisation=current_profile.organisation, name=form.cleaned_data["name"]
        ).exists():
            form.add_error("name", "You are not allowed to edit this system")
            return self.form_invalid(form)
        form.save()
        return HttpResponseRedirect(self.get_success_url())


class ViewSystemsView(LoginRequiredMixin, TemplateView):
    template_name = "system/systems.html"
    login_url = "/oidc/authenticate/"
    success_url = "/systems/"

    def get_context_data(self, **kwargs):
        current_profile_id = self.request.session.get("current_profile_id")
        data = super().get_context_data(**kwargs)
        user_profile = UserProfile.objects.filter(user=self.request.user, id=current_profile_id).get()
        if user_profile.role != UserProfile.ROLE_CHOICES[0][0]:
            raise Exception("You are not allowed to view this page")

        data["current_profile"] = user_profile
        data["systems"] = System.objects.filter(organisation=data["current_profile"].organisation)
        return data
