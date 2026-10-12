import datetime
from datetime import date
from typing import Any

from django.core.exceptions import ValidationError
from django.forms import (
    CharField,
    ChoiceField,
    EmailField,
    Form,
    HiddenInput,
    IntegerField,
    ModelForm,
    MultiValueField,
    MultiWidget,
    Textarea,
    TextInput,
)

from webcaf.webcaf.forms.factory import WordCountValidator
from webcaf.webcaf.models import Review


class RecommendationForm(Form):
    """
    Handles recommendation submissions.

    This class represents a form for submitting recommendations. It is designed to
    collect a title and detailed rationale for the recommendation.

    :ivar title: Title of the recommendation. This is a required field with a maximum
        length of 255 characters.
    :type title: CharField
    :ivar text: Detailed rationale or explanation for the recommendation. This is a
        required field that uses a Textarea widget for input.
    :type text: CharField
    """

    max_words = 200

    title = CharField(
        label="Risk",
        widget=Textarea(attrs={"rows": 3}),
        required=False,
    )
    text = CharField(
        label="Details and rationale",
        widget=Textarea(attrs={"rows": 10}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        validator = WordCountValidator(self.max_words)

        for field_name in ["title", "text"]:
            field = self.fields[field_name]
            field.validators = [validator]
            field.widget.attrs["max_words"] = self.max_words

    def clean(self):
        cleaned_data = self.cleaned_data
        # Don't validate if the recommendation is marked for deletion
        if not cleaned_data.get("DELETE"):
            super().clean()


class PeerReviewRecommendationForm(RecommendationForm):
    """
    Represents a peer review recommendation form.

    This class extends the base RecommendationForm and is specifically tailored
    for peer review scenarios. It includes constraints and attributes that ensure
    recommendations adhere to specific formatting or word count rules. Typically
    used in systems where peer assessment and structured feedback are required.

    :ivar max_words: The maximum number of words allowed for the recommendation.
    :type max_words: int
    """

    max_words = 100


class PreviewForm(Form):
    """
    Tracks if the user has confirmed the changes
    """

    preview_status = ChoiceField(
        required=True, choices=[("preview", ""), ("confirm", ""), ("change", "")], initial="preview", widget=HiddenInput
    )


class CommentsForm(ModelForm):
    """
    A form class for handling user comments.

    This class is used to create a form for submitting user comments. It provides
    a single field for text input and validates the input as required. This form
    is specifically tied to the `Review` model.

    *NOTE*: The empty `fields` attribute is required to ensure the form is not validated
    against any model fields as it is up to the views to store the comments in the
    required format.

    :ivar text: A field to input the comment text. Validation is enforced to ensure
                this field is required.
    :type text: CharField
    """

    max_words = 750
    text = CharField(
        widget=Textarea(
            attrs={
                "rows": 10,
            },
        ),
        label="Comment",
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        validator = WordCountValidator(self.max_words)
        for field_name in ["text"]:
            field = self.fields[field_name]
            field.validators = [validator]
            field.widget.attrs["max_words"] = self.max_words

    class Meta:
        model = Review
        fields: list[str] = []


class PeerReviewCommentsForm(CommentsForm):
    """
    Represents a form specifically designed for handling peer review comments.

    This class extends the base `CommentsForm` to include a maximum word count
    restriction for peer review comments, ensuring inputs remain concise and
    within the defined limit. It serves as a template for managing user
    feedback in peer review workflows. Developers can extend or adapt this
    class as needed for related use cases.

    :ivar max_words: Maximum allowed word count for a comment in the form.
    :type max_words: int
    """

    max_words = 1000


class PeerReviewCommentsFormMax300Words(PeerReviewCommentsForm):
    """
    Represents a form specifically designed for handling peer review comments.

    This class extends the base `PeerReviewCommentsForm` to include a maximum word count
    restriction for peer review comments, ensuring inputs remain concise and
    within the defined limit. It serves as a template for managing user
    feedback in peer review workflows. Developers can extend or adapt this
    class as needed for related use cases.

    :ivar max_words: Maximum allowed word count for a comment in the form.
    :type max_words: int
    """

    max_words = 300


class DateWidget(MultiWidget):
    def __init__(self, attrs=None):
        widgets = [
            TextInput(
                attrs={
                    "inputmode": "numeric",
                    "class": "govuk-input govuk-date-input__input govuk-input--width-2",
                }
            ),
            TextInput(
                attrs={
                    "inputmode": "numeric",
                    "class": "govuk-input govuk-date-input__input govuk-input--width-2",
                }
            ),
            TextInput(
                attrs={
                    "inputmode": "numeric",
                    "class": "govuk-input govuk-date-input__input govuk-input--width-4",
                }
            ),
        ]

        super().__init__(widgets, attrs)

    def decompress(self, value):
        if value is None:
            return [None, None, None]

        if isinstance(value, (list, tuple)) and len(value) == 3:
            return list(value)

        if isinstance(value, date):
            return [value.day, value.month, value.year]

        return [None, None, None]


class DateField(MultiValueField):
    def __init__(self, *args, **kwargs):
        fields = [
            IntegerField(
                required=True,
            ),
            IntegerField(
                required=True,
            ),
            IntegerField(
                required=True,
            ),
        ]

        super().__init__(
            fields=fields,
            widget=DateWidget,
            # error_messages={"required": "Enter a valid date","invalid": "Enter a valid date"},
            *args,
            **kwargs,
        )

    def compress(self, data_list):
        if not data_list:
            return None

        day, month, year = data_list

        if not all([day, month, year]):
            raise ValidationError(
                f"{self.label}: Enter a valid date",
                code="invalid_date",
            )
        try:
            return date(year, month, day)
        except ValueError:
            raise ValidationError(
                f"{self.label}: Enter a valid date",
                code="invalid_date",
            )


class ReviewPeriodForm(ModelForm):
    """
    A ReviewPeriodForm class to handle date inputs for review periods.

    This class is a form used to capture and validate review period start and end dates.
    It allows selecting dates through individual components (day, month, year) and ensures
    the start date occurs before the end date. Additionally, it provides mechanisms to
    process and format the date into a textual representation for use in views.
    """

    start_date = DateField(label="Start date", required=False)
    end_date = DateField(label="End date", required=False)

    def __init__(self, *args, **kwargs):
        text = kwargs.get("initial", {}).get("text", {})
        if text:
            kwargs["initial"]["start_date"] = text.get("start_date", "//").split("/")
            kwargs["initial"]["end_date"] = text.get("end_date", "//").split("/")
        super().__init__(*args, **kwargs)

    def clean(self) -> dict[str, Any] | None:
        cleaned = super().clean() or {}
        # Confirm we have correct value range
        if self.errors:
            return cleaned

        start_date = cleaned.get("start_date", "")
        end_date = cleaned.get("end_date", "")

        if not start_date or not end_date:
            raise ValidationError(
                (
                    {"start_date": "Start date: Enter the start and end dates of your assurance review"}
                    if not start_date
                    else {}
                )
                | (
                    {"end_date": "End date: Enter the start and end dates of your assurance review"}
                    if not end_date
                    else {}
                )
            )
        now_ = datetime.datetime.now().date()
        if start_date > now_ or end_date > now_:
            raise ValidationError(
                (
                    {"start_date": "Start date: The date of your assurance review must be in the past"}
                    if start_date > now_
                    else {}
                )
                | (
                    {"end_date": "End date: The date of your assurance review must be in the past"}
                    if end_date > now_
                    else {}
                )
            )

        if start_date > end_date:
            raise ValidationError({"start_date": "The start date of your assurance review must be before the end date"})

        # Set the text component to the formatted date. This is the attribute required in the view
        self.cleaned_data["text"] = {
            "start_date": start_date.strftime("%d/%m/%Y"),
            "end_date": end_date.strftime("%d/%m/%Y"),
        }
        return cleaned

    class Meta:
        model = Review
        fields: list[str] = []


class CompanyDetailsForm(ModelForm):
    company_name = CharField(
        label="Company name",
        max_length=255,
        required=True,
        error_messages={"required": "Add the trading name of the company "},
    )
    lead_assessor_name = CharField(
        label="Lead reviewer name",
        max_length=255,
        required=True,
        error_messages={"required": "Add the lead reviewer name"},
    )
    lead_assessor_email = EmailField(
        label="Lead reviewer email",
        max_length=255,
        required=True,
        error_messages={"required": "Enter an email address in the correct format, like name@example.com"},
    )
    company_address = CharField(label="Company address", max_length=500, required=False)
    company_phone = CharField(label="Company phone number", max_length=15, required=False)

    class Meta:
        model = Review
        fields: list[str] = []

    def __init__(self, *args, **kwargs):
        text = kwargs.pop("initial", {}).get("text", {})
        if text:
            initial = kwargs.get("initial", {})
            kwargs["initial"] = initial | text
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.is_valid():
            # Set the transformed data to be saved if the form is valid
            self.cleaned_data["text"] = {
                "company_name": self.cleaned_data["company_name"],
                "lead_assessor_name": self.cleaned_data["lead_assessor_name"],
                "lead_assessor_email": self.cleaned_data["lead_assessor_email"],
            }
