from datetime import date
from typing import Any

from django.core.exceptions import ValidationError
from django.forms import (
    CharField,
    ChoiceField,
    Form,
    HiddenInput,
    IntegerField,
    ModelForm,
    Textarea,
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

    title = CharField(label="Recommendation title", max_length=255, required=False, help_text="Optional.")
    text = CharField(
        validators=([WordCountValidator(750)]),
        widget=Textarea(
            attrs={"rows": 10, "max_words": 750},
        ),
        label="Details and rationale",
        required=False,
    )

    def clean(self):
        cleaned_data = self.cleaned_data
        # Don't validate if the recommendation is marked for deletion
        if not cleaned_data.get("DELETE"):
            super().clean()


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

    text = CharField(
        validators=([WordCountValidator(750)]),
        widget=Textarea(
            attrs={"rows": 10, "max_words": 750},
        ),
        label="Comment",
        required=True,
    )

    class Meta:
        model = Review
        fields: list[str] = []


class ReviewPeriodForm(ModelForm):
    """
    A ReviewPeriodForm class to handle date inputs for review periods.

    This class is a form used to capture and validate review period start and end dates.
    It allows selecting dates through individual components (day, month, year) and ensures
    the start date occurs before the end date. Additionally, it provides mechanisms to
    process and format the date into a textual representation for use in views.

    :ivar start_date_day: Integer field to capture the day component of the start date.
    :ivar start_date_month: Integer field to capture the month component of the start date.
    :ivar start_date_year: Integer field to capture the year component of the start date.
    :ivar end_date_day: Integer field to capture the day component of the end date.
    :ivar end_date_month: Integer field to capture the month component of the end date.
    :ivar end_date_year: Integer field to capture the year component of the end date.
    """

    start_date_day = IntegerField(min_value=1, max_value=31, label="Day")
    start_date_month = IntegerField(min_value=1, max_value=12, label="Month")
    start_date_year = IntegerField(min_value=date.today().year - 1, max_value=date.today().year, label="Year")

    end_date_day = IntegerField(min_value=1, max_value=31, label="Day")
    end_date_month = IntegerField(min_value=1, max_value=12, label="Month")
    end_date_year = IntegerField(min_value=date.today().year - 1, max_value=date.today().year, label="Year")

    def __init__(self, *args, **kwargs):
        text = kwargs.pop("initial", {}).get("text", "")
        if text:
            initial = kwargs.get("initial", {})
            date_parts = text.split("-")
            idx = 0
            for prefix in self.prefixes():
                date_part = date_parts[idx].split("/")
                if len(date_part) == 3:
                    initial = initial | {
                        f"{prefix}_date_day": int(date_part[0]),
                        f"{prefix}_date_month": int(date_part[1]),
                        f"{prefix}_date_year": int(date_part[2]),
                    }
                idx += 1
            kwargs["initial"] = initial
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        # Confirm we have correct value range
        if self.errors:
            return cleaned

        start_date = self.clean_components(cleaned, "start")
        end_date = self.clean_components(cleaned, "end")
        if not start_date or not end_date:
            return cleaned

        if start_date > end_date:
            raise ValidationError("The start date must be before the end date")
        # Set the text component to the formatted date. This is the attribute required in the view
        self.cleaned_data["text"] = start_date.strftime("%d/%m/%Y") + " - " + end_date.strftime("%d/%m/%Y")
        return cleaned

    def clean_components(self, cleaned: dict[str, Any], prefix: str):
        """
        Cleans and validates date components from a given set of inputs for a specific prefix. It constructs
        a `date` object if all the required components (day, month, year) are provided and valid. Raises a
        `ValidationError` when the components are missing or form an invalid date.

        :param cleaned: The dictionary containing date component values.
        :type cleaned: dict[str, Any] | None
        :param prefix: The prefix string used to extract date components from the `cleaned` dictionary.
        :type prefix: str
        :return: A `date` object if the components are valid.
        :rtype: date
        :raises ValidationError: If the date components are invalid or any component is missing.
        """
        d = cleaned.get(f"{prefix}_date_day")
        m = cleaned.get(f"{prefix}_date_month")
        y = cleaned.get(f"{prefix}_date_year")
        if d and m and y:
            try:
                return date(y, m, d)
            except ValueError:
                self.add_error(f"{prefix}_date_day", "Invalid date combination")
                self.add_error(f"{prefix}_date_month", "Invalid date combination")
                self.add_error(f"{prefix}_date_year", "Invalid date combination")
        return None

    def prefixes(self):
        """
        Generates and returns a list of predefined prefixes.

        This method returns a list containing specific string elements that can be used
        as prefixes for various purposes. The list of prefixes is predefined and does
        not depend on any external input or computation.

        :return: A list of predefined string prefixes.
        :rtype: list[str]
        """
        return ["start", "end"]

    class Meta:
        model = Review
        fields: list[str] = []
