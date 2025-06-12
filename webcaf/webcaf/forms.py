from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Button, HTML, Layout
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


class TutorialForm(forms.Form):
    name = forms.CharField(
        label="Name",
        help_text="Your full name.",
        error_messages={"required": "Enter your name as it appears on your passport"},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout("name", Button("submit", "Submit"), HTML.details("<h1>hello</h1><img src=1 onerror=alert(8)>", "123"))
