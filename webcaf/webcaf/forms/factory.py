from django import forms
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

from webcaf.webcaf.caf.field_providers import FieldProvider


@deconstructible
class WordCountValidator:
    """
    A custom validator to validate the word count against the max
    allowed wordcount and raise a validationError if the user word
    count in a field exceeds the given maximum allowed word count.
    """

    def __init__(self, max_words):
        self.max_words = max_words
        self.message = f"Ensure this value has at most {self.max_words} words (it has "

    def __call__(self, words):
        word_count = len(words.split())
        if word_count > self.max_words:
            raise ValidationError(f"{self.message} {word_count}).")

    def __eq__(self, other):
        return (
            isinstance(other, WordCountValidator)
            and self.max_words == other.max_words
            and self.message == other.message
        )


def create_form(provider: FieldProvider) -> type[forms.Form]:  # noqa: C901
    """
    Creates a Django form class based on the fields specified by the
    FieldProvider. This decouples the form creation from the
    specifics of the assessment framework (or other document) being
    represented.
    """
    metadata = provider.get_metadata() or {}
    field_defs = provider.get_field_definitions()

    form_fields = {}
    for field_def in field_defs:
        if field_def["type"] == "boolean":
            form_fields[field_def["name"]] = forms.BooleanField(
                label=field_def["label"], required=field_def.get("required", False), widget=forms.CheckboxInput()
            )
        elif field_def["type"] == "choice":
            widget = None
            if field_def.get("widget") == "radio":
                widget = forms.RadioSelect
            form_fields[field_def["name"]] = forms.ChoiceField(  # type: ignore
                label=field_def["label"],
                choices=field_def["choices"],
                required=field_def.get("required", True),
                initial=field_def.get("initial"),
                widget=widget,
            )
        elif field_def["type"] == "choice_with_justifications":
            form_fields[field_def["name"]] = forms.ChoiceField(  # type: ignore
                label=field_def["label"],
                choices=[(choice.value, choice.label) for choice in field_def["choices"]],
                required=field_def.get("required", True),
                initial=field_def.get("initial"),
            )
            for choice in field_def["choices"]:
                # Needs justification field
                if choice.needs_justification_text:
                    form_fields[f"{field_def['name']}_{choice.value}_comment"] = forms.CharField(  # type: ignore
                        label="Extra information",
                        # This will be validated in the form's clean method'
                        required=False,
                    )
        elif field_def["type"] == "text":
            widget_attrs = field_def.get("widget_attrs", {})
            form_fields[field_def["name"]] = forms.CharField(  # type: ignore
                label=field_def["label"],
                required=field_def.get("required", True),
                widget=forms.Textarea(attrs=widget_attrs) if widget_attrs else None,
                validators=[WordCountValidator(widget_attrs["maxlength"])],
            )
        elif field_def["type"] == "hidden":
            widget_attrs = field_def.get("widget_attrs", {})
            form_fields[field_def["name"]] = forms.CharField(  # type: ignore
                widget=forms.HiddenInput(attrs=widget_attrs) if widget_attrs else None,
            )

    form_class_name = f"Form_{metadata.get('code', '').replace('.', '_')}"
    FormClass = type(form_class_name, (forms.Form,), form_fields)

    def form_init(self, *args, **kwargs) -> None:
        """
        The __init__ method of the form class created in create_form is set to
        this function. It instanitates a FormHelper and uses the arguments
        passed to create_form to generate the form's layout (hence it's
        declared within it).
        """
        super(FormClass, self).__init__(*args, **kwargs)  # type: ignore

    FormClass.__init__ = form_init  # type: ignore

    return FormClass
