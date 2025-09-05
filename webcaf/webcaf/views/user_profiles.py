import logging

from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import FormView, TemplateView

from webcaf.webcaf.forms.general import NextActionForm, UserProfileForm
from webcaf.webcaf.models import UserProfile
from webcaf.webcaf.utils.permission import PermissionUtil, UserRoleCheckMixin
from webcaf.webcaf.utils.session import SessionUtil


class UserProfilesView(UserRoleCheckMixin, TemplateView):
    template_name = "users/users.html"
    login_url = "/oidc/authenticate/"

    def get_allowed_roles(self) -> list[str]:
        return ["cyber_advisor", "organisation_lead"]

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        user_profile = SessionUtil.get_current_user_profile(self.request)
        data["current_profile"] = user_profile
        if not PermissionUtil.current_user_can_view_users(user_profile):
            raise PermissionError("You are not allowed to view this page")
        return data


class UserProfileView(UserRoleCheckMixin, FormView):
    template_name = "users/user.html"
    login_url = "/oidc/authenticate/"
    success_url = "/view-profiles/"
    form_class = UserProfileForm

    def get_allowed_roles(self) -> list[str]:
        return ["cyber_advisor", "organisation_lead"]

    def get_context_data(self, **kwargs):
        user_profile = SessionUtil.get_current_user_profile(request=self.request)
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
        current_profile = SessionUtil.get_current_user_profile(request=self.request)
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


class CreateOrSkipUserProfileView(UserRoleCheckMixin, FormView):
    """
    Utility action to decide to create a new user or go back to the
    home screen.
    """

    form_class = NextActionForm

    def get_allowed_roles(self) -> list[str]:
        return ["cyber_advisor", "organisation_lead"]

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

    form_class = NextActionForm
    template_name = "users/delete-user.html"
    logger = logging.getLogger("RemoveUserProfileView")

    def get_allowed_roles(self) -> list[str]:
        return ["cyber_advisor", "organisation_lead"]

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
            current_user_profile = SessionUtil.get_current_user_profile(self.request)
            if PermissionUtil.current_user_can_delete_user(current_user_profile):
                # Delete the given profile
                profile_to_delete = UserProfile.objects.get(
                    id=self.kwargs["user_profile_id"],
                )
                if profile_to_delete.organisation != current_user_profile.organisation:
                    self.logger.error(
                        f"User {self.request.user.username} is not allowed to delete this user profile {self.kwargs['user_profile_id']} in {profile_to_delete.organisation} organisation"
                    )
                    raise PermissionError("You are not allowed to delete this user profile in a different organisation")

                self.logger.info(
                    f"Deleting user profile {self.kwargs['user_profile_id']} by user {self.request.user.username}"
                )
                profile_to_delete.delete()
            else:
                self.logger.error(
                    f"User {self.request.user.username} is not allowed to delete this user profile {self.kwargs['user_profile_id']}"
                )
                raise PermissionError("You are not allowed to delete this user profile")
        return redirect(reverse("view-profiles"))

    def form_invalid(self, form):
        return redirect(reverse("view-profiles"))
