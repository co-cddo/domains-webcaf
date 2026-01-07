import logging

from django import forms
from django.contrib.auth.models import User

from webcaf.webcaf.models import UserProfile
from webcaf.webcaf.utils import mask_email


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.CharField(max_length=150, required=True)
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, required=True)
    # By default we do not pass the action field in the initial form, which makes the validation failure
    # and we capture that ant and redirect the user to the confirmation page.
    action = forms.ChoiceField(choices=[("change", "Change"), ("confirm", "Confirm")], required=True)

    logger = logging.getLogger("UserProfileForm")

    class Meta:
        model = UserProfile
        fields = ["first_name", "last_name", "email", "role"]

    def __init__(self, *args, **kwargs):
        """
        :param instance: Instance of userprofile object containing user information.
        :type instance: UserInstance

        :param initial: Initial data dictionary to be used for initialization.
        :type initial: dict
        """
        instance = kwargs.get("instance")
        if instance:
            # Set the initial values for the form fields
            initial = kwargs.setdefault("initial", {})
            initial["first_name"] = instance.user.first_name
            initial["last_name"] = instance.user.last_name
            initial["email"] = instance.user.email
        super().__init__(*args, **kwargs)

    def clean_role(self):
        role = self.cleaned_data["role"]
        if role == "cyber_advisor":
            raise PermissionError("You are not allowed to change this role")
        return role

    def clean_email(self):
        email = self.cleaned_data["email"]
        return email.lower()

    def save(self, commit=True):
        """
        Summary
        -------
        Method to save role and related user details.

        Details
        -------
        This method saves the current instance of a Role model to the UserProfile
        and updates the associated User model with new first name, last name, and email if they have changed.
        The changes are committed to the database if `commit` is True.

        :param commit: Optional boolean indicating whether to save the changes to the database. Default is True.
        :return: UserProfile object representing the saved user profile.
        """

        user_email = self.cleaned_data["email"]
        user, created = User.objects.get_or_create(
            email=user_email,
            defaults={
                "username": user_email,
            },
        )

        # Save any updated information on the user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.username = user_email
        self.instance.user = user
        self.instance.user.save()

        log_message = (
            f"Created new user {user_email} {user.id} for profile {self.instance.id if self.instance.id else 'new profile'}"
            if created
            else f"User {user_email} {user.id} already exists, associating with the profile {self.instance.id if self.instance.id else 'new profile'}"
        )
        self.logger.info(mask_email(log_message))
        return super().save(commit)
