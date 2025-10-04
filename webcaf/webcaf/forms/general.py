from django import forms
from django.forms import ChoiceField, Form


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
