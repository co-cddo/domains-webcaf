from django import forms
from django.contrib.auth.models import User
from django.forms import Form, ModelForm
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import FormView, TemplateView

from webcaf.webcaf.models import UserProfile
from webcaf.webcaf.views.util import UserRoleCheckMixin, get_current_user_profile


class UserProfilesView(UserRoleCheckMixin, TemplateView):
    template_name = "users/users.html"
    login_url = "/oidc/authenticate/"

    def get_allowed_roles(self) -> list[str]:
        return ["cyber_advisor"]

    def get_context_data(self, **kwargs):
        current_profile_id = self.request.session.get("current_profile_id")
        user_profile = UserProfile.objects.filter(user=self.request.user, id=current_profile_id).get()
        data = super().get_context_data(**kwargs)
        data["current_profile"] = user_profile
        if user_profile.role != UserProfile.ROLE_CHOICES[0][0]:
            raise Exception("You are not allowed to view this page")
        return data


class UserProfileForm(ModelForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.CharField(max_length=150, required=True)
    # By default we do not pass the action field in the initial form, which makes the validation failure
    # and we capture that ant and redirect the user to the confirmation page.
    action = forms.ChoiceField(choices=[("change", "Change"), ("confirm", "Confirm")], required=True)

    class Meta:
        model = UserProfile
        fields = ["first_name", "last_name", "email", "role"]

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        if instance:
            initial = kwargs.setdefault("initial", {})
            initial["first_name"] = instance.user.first_name
            initial["last_name"] = instance.user.last_name
            initial["email"] = instance.user.email
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        # Save role to UserProfile and names to related User
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
            profile.save()
        return profile


class UserProfileView(UserRoleCheckMixin, FormView):
    template_name = "users/user.html"
    login_url = "/oidc/authenticate/"
    success_url = "/view-profiles/"
    form_class = UserProfileForm

    def get_allowed_roles(self) -> list[str]:
        return ["cyber_advisor"]

    def get_context_data(self, **kwargs):
        user_profile = get_current_user_profile(request=self.request)
        data = super().get_context_data(**kwargs)
        data["current_profile"] = user_profile
        # Remove cyber advisor role from the list of roles.
        # We only create that role through the admin interface.
        data["roles"] = [
            (*role, UserProfile.ROLE_ACTIONS[role[0]])
            for role in UserProfile.ROLE_CHOICES
            if role[0] != "cyber_advisor"
        ]
        return data

    def get_object(self):
        current_profile = get_current_user_profile(request=self.request)
        user_profile = UserProfile.objects.get(
            id=self.kwargs["user_profile_id"], organisation=current_profile.organisation
        )
        return user_profile

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.get_object()
        return kwargs

    def form_valid(self, form):
        if form.cleaned_data["action"] == "change":
            # Send the user back to edit form
            return self.form_invalid(form)
        form.save()
        return super().form_valid(form)

    def form_invalid(self, form):
        # Capture the first instance of the user input, where we would get flagged
        # for unconfirmed changes.
        if len(form.errors) == 1 and "action" in form.errors:
            current_profile_id = self.request.session.get("current_profile_id")
            current_profile = UserProfile.objects.filter(user=self.request.user, id=current_profile_id).get()
            return render(self.request, "users/user-confirm.html", {"form": form, "current_profile": current_profile})
        return super().form_invalid(form)


class CreateUserProfileView(UserProfileView):
    def get_object(self):
        return None

    def form_valid(self, form):
        action = self.request.POST.get("action")
        if action == "change":
            form.errors.clear()
            return super().form_invalid(form)

        user_email = form.cleaned_data["email"]
        user, created = User.objects.get_or_create(
            email=user_email,
            defaults={"username": user_email},
        )

        form.instance.user = user
        current_profile_id = self.request.session.get("current_profile_id")
        current_profile = UserProfile.objects.filter(user=self.request.user, id=current_profile_id).get()
        form.instance.organisation = current_profile.organisation

        return super().form_valid(form)


class ActionForm(Form):
    action = forms.ChoiceField(
        choices=[("change", "Change"), ("confirm", "Confirm"), ("skip", "Skip")], required=True, initial="confirm"
    )


class CreateOrSkipUserProfileView(UserRoleCheckMixin, FormView):
    """
    Utility action to decide to create a new user or go back to the
    home screen.
    """

    def get_allowed_roles(self) -> list[str]:
        return ["cyber_advisor"]

    form_class = ActionForm

    def form_valid(self, form):
        action = self.request.POST.get("action")
        if action == "confirm":
            return redirect(reverse("create-new-profile"))

        return redirect(reverse("my-account"))

    def form_invalid(self, form):
        return redirect(reverse("view-profiles"))


class RemoveUserProfileView(UserRoleCheckMixin, FormView):
    """
    View to confirm the user profile deletion and action it.
    This only removes the profile (user association with the organisation) and not the user from the system
    """

    form_class = ActionForm
    template_name = "users/delete-user.html"

    def get_allowed_roles(self) -> list[str]:
        return ["cyber_advisor"]

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        current_profile_id = self.request.session.get("current_profile_id")
        user_profile = UserProfile.objects.filter(user=self.request.user, id=current_profile_id).get()
        user_profile_to_delete = UserProfile.objects.get(
            id=self.kwargs["user_profile_id"], organisation=user_profile.organisation
        )
        data["user_profile_to_delete"] = user_profile_to_delete
        return data

    def form_valid(self, form):
        action = self.request.POST.get("action")
        if action == "confirm":
            # Delete the given profile
            UserProfile.objects.get(
                id=self.kwargs["user_profile_id"],
            ).delete()

        return redirect(reverse("view-profiles"))

    def form_invalid(self, form):
        return redirect(reverse("view-profiles"))
