from django import forms


class ContinueForm(forms.Form):
    """
    A simple navigation form with just a button that submits no data.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
