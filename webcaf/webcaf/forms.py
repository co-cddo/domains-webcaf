from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Button, Layout
from django import forms


class ContinueForm(forms.Form):
    """
    A simple navigation form with just a button that submits no data.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = True

        self.helper.layout = Layout(Button("submit", "Continue", css_class="govuk-button"))
