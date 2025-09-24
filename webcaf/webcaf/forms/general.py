from django import forms
from django.forms import ChoiceField, Form

from webcaf.webcaf.models import UserProfile


class ContinueForm(forms.Form):
    """
    A simple navigation form with just a button that submits no data.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class NextActionForm(Form):
    """
    Represents a form for selecting the next action.

    This class is a specialized form used to present choices for the next step a user
    can take. The options available include changing a previous choice, confirming the
    selection, or skipping to proceed without making any changes. Ensures that a valid
    choice is always selected by the user before proceeding.

    :ivar action: Represents the selected action the user wants to take. The options
                  available are "change", "confirm", and "skip". By default, it is set
                  to "confirm".
    :type action: ChoiceField
    """

    action = ChoiceField(
        choices=[("change", "Change"), ("confirm", "Confirm"), ("skip", "Skip")], required=True, initial="confirm"
    )


class UserProfileForm(forms.ModelForm):
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
