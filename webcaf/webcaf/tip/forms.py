from enum import StrEnum
from typing import Any

from django import forms
from django.core.validators import MaxLengthValidator
from django.forms import BooleanField, CharField, ChoiceField, ModelForm

from webcaf.webcaf.forms.factory import WordCountValidator
from webcaf.webcaf.models import RecommendationAction, Tip


class RecommendationActionChoices(StrEnum):
    """
    List of possible actions to perform upon
    the submission of the RecommendationActionForm
    """

    VALIDATE_AND_BACK_TO_ANSWERS = "validate_and_back_to_answers"
    VALIDATE_AND_BACK_TO_SUMMARY = "validate_and_back_to_summary"
    VALIDATE_AND_NEXT_RECOMMENDATION = "validate_and_next_recommendation"
    SAVE_AND_BACK_TO_SUMMARY = "save_and_back_to_summary"
    SAVE_AND_NEXT_RECOMMENDATION = "save_and_next_recommendation"


class RecommendationActionForm(forms.ModelForm):
    """
    Manages the structure and validation of a recommendation action form used for capturing
    user input regarding actions planned or taken based on a recommendation.

    This class serves as a Django ModelForm for handling data related to recommendations,
    validating input fields, and preparing the data to be saved into the database. It also
    ensures that the required constraints for specific conditions are adhered to. The form
    supports scenarios including planning actions, providing target dates, and detailing
    unplanned actions.

    :ivar PLANNED_ACTION_REQUIRED_FIELDS: A mapping of fields required when an action is
        planned and their corresponding error messages.
    :type PLANNED_ACTION_REQUIRED_FIELDS: dict[str, str]
    :ivar TARGET_DATE_REQUIRED_FIELDS: A mapping of fields required when a target date is
        provided and their corresponding error messages.
    :type TARGET_DATE_REQUIRED_FIELDS: dict[str, str]
    :ivar PLANNED_ACTION_DETAIL_FIELDS: A tuple defining fields required for detailing
        planned actions when recommendation actions are set as planned.
    :type PLANNED_ACTION_DETAIL_FIELDS: tuple[str]
    :ivar recommendation_id: A required field for capturing the recommendation identifier.
    :type recommendation_id: CharField
    :ivar recommendation_category: A required field for capturing the category of the
        recommendation.
    :type recommendation_category: CharField
    :ivar recommendation_actioned: An optional choice field to determine whether an
        action will be added for a recommendation.
    :type recommendation_actioned: ChoiceField
    :ivar action_owner: An optional field specifying the owner of the planned action.
    :type action_owner: CharField
    :ivar resources_available: An optional choice field indicating the availability of
        resources for the action.
    :type resources_available: ChoiceField
    :ivar budget_available: An optional choice field indicating whether a budget is
        approved to deliver the action.
    :type budget_available: ChoiceField
    :ivar action_taken_description: An optional text field for describing the action to
        be taken, with a limit of 500 words.
    :type action_taken_description: CharField
    :ivar target_date_provided: An optional choice field specifying whether a target date
        is provided for the planned action.
    :type target_date_provided: ChoiceField
    :ivar target_day_day: An optional field for the day component of the target date,
        ranging from 1 to 31.
    :type target_day_day: forms.IntegerField
    :ivar target_day_month: An optional field for the month component of the target date,
        ranging from 1 to 12.
    :type target_day_month: forms.IntegerField
    :ivar target_day_year: An optional field for the year component of the target date,
        constrained between 2026 and 2100.
    :type target_day_year: forms.IntegerField
    :ivar target_date_unavailable_reason: An optional text field for providing a reason
        when no target date is available, with a maximum of 500 words.
    :type target_date_unavailable_reason: CharField
    :ivar action_not_planned_reason: An optional text field specific to scenarios where
        no action is planned, with a word limit of 500.
    :type action_not_planned_reason: CharField
    """

    PLANNED_ACTION_REQUIRED_FIELDS = {
        "action_owner": "Enter the action owner.",
        "resources_available": "Enter available resources.",
        "action_taken_description": "Enter the action to be taken.",
        "target_date_provided": "Please indicate whether a target date has been provided.",
        "budget_available": "Is budget available for the action?",
    }
    TARGET_DATE_REQUIRED_FIELDS = {
        "target_day_day": "Enter a target day.",
        "target_day_month": "Enter a target month.",
        "target_day_year": "Enter a target year.",
    }
    PLANNED_ACTION_DETAIL_FIELDS = (
        "target_date_provided",
        "target_day_day",
        "target_day_month",
        "target_day_year",
        "target_date_unavailable_reason",
        "resources_available",
        "budget_available",
        "action_taken_description",
        "action_owner",
    )

    # The main required field to continue with the form processing
    recommendation_id = CharField(required=True)
    recommendation_category = CharField(required=True)
    submit_action = ChoiceField(
        required=True,
        choices=(
            (RecommendationActionChoices.VALIDATE_AND_BACK_TO_ANSWERS, "Back to answers"),
            (RecommendationActionChoices.VALIDATE_AND_BACK_TO_SUMMARY, "Back to summary"),
            (RecommendationActionChoices.VALIDATE_AND_NEXT_RECOMMENDATION, "Next recommendation"),
            # Non-validating options
            (RecommendationActionChoices.SAVE_AND_BACK_TO_SUMMARY, "Back to summary"),
            (RecommendationActionChoices.SAVE_AND_NEXT_RECOMMENDATION, "Next recommendation"),
        ),
        widget=forms.RadioSelect,
        label="Action to perform",
    )

    # Path to decide if this is actioned or not
    recommendation_actioned = ChoiceField(
        required=True,
        choices=[("action_planned", "Yes"), ("action_not_planned", "No")],
        label="Will you add an action for this recommendation",
    )

    # If action planed we need the following
    action_owner = CharField(required=False, label="Who owns this action")
    resources_available = ChoiceField(
        required=False,
        choices=[("yes", "Yes"), ("no", "No"), ("unknown", "Unknown")],
        label="Are the resources available to deliver this action",
    )
    budget_available = ChoiceField(
        required=False,
        choices=[("yes", "Yes"), ("no", "No"), ("unknown", "Unknown")],
        label="Is the budget approved to deliver this action",
    )
    action_taken_description = CharField(
        required=False,
        validators=[WordCountValidator(500)],
        widget=forms.Textarea(attrs={"rows": 10, "cols": 40, "max_words": 500}),
        label="What action will you take",
    )

    # Action completion target date information
    target_date_provided = ChoiceField(
        required=False,
        choices=(
            ("yes", "Yes"),
            ("no", "No"),
        ),
        widget=forms.RadioSelect,
    )
    target_day_day = forms.IntegerField(required=False, min_value=1, max_value=31, label="Estimated target Day")
    target_day_month = forms.IntegerField(required=False, min_value=1, max_value=12, label="Estimated target Month")
    target_day_year = forms.IntegerField(required=False, min_value=2026, max_value=2100, label="Estimated target Year")
    target_date_unavailable_reason = CharField(
        required=False,
        validators=[WordCountValidator(500)],
        widget=forms.Textarea(attrs={"rows": 10, "cols": 40, "max_words": 500}),
        label="Reason for target date unavailability",
    )

    # If action is not planned, we need this field
    action_not_planned_reason = CharField(
        required=False,
        validators=[WordCountValidator(500)],
        label="Reason for not planning an action",
        widget=forms.Textarea(attrs={"rows": 10, "cols": 40, "max_words": 500}),
    )

    class Meta:
        model = Tip
        fields: list[str] = []

    def save(self, commit: bool = True) -> Tip:
        """
        Saves the current state of the instance with necessary modifications based on
        the review status of the recommendation. If the recommendation has not been
        reviewed, it resets the associated recommendation action with the provided
        recommendation ID. If reviewed, it creates and sets a new recommendation action
        with relevant details provided in the cleaned data.

        :param commit: Specifies whether the changes should be committed to the database.
                       If True, saves the instance to the database. Default is True.
        :type commit: bool

        :return: The saved instance after applying the changes and validating the data.
        :rtype: Tip
        """
        action = RecommendationAction(
            # We will only set the recommendation_reviewed to yes if the submit_action is one of the validate options
            recommendation_reviewed="yes"
            if self.cleaned_data["submit_action"]
            in {
                RecommendationActionChoices.VALIDATE_AND_NEXT_RECOMMENDATION,
                RecommendationActionChoices.VALIDATE_AND_BACK_TO_ANSWERS,
                RecommendationActionChoices.VALIDATE_AND_BACK_TO_SUMMARY,
            }
            else "no",
            recommendation_category=self.cleaned_data["recommendation_category"],
            action_type=self.cleaned_data.get("recommendation_actioned"),
            recommendation_id=self.cleaned_data["recommendation_id"],
            action_details=self._build_action_details(),
            actioned_by=self.cleaned_data["actioned_by"],
            actioned_time=self.cleaned_data.get("actioned_time", ""),
        )
        self.instance.set_recommendation_action(action=action)
        return super().save(commit)

    def _build_action_details(self) -> dict[str, Any]:
        if self.cleaned_data.get("recommendation_actioned", "") in ["action_not_planned"]:
            # Only populate the action_not_planned_reason if we have chosen action_not_planned
            # otherwise store all available information from the screen
            return {"action_not_planned_reason": self.cleaned_data.get("action_not_planned_reason")}
        return {field: self.cleaned_data.get(field) for field in self.PLANNED_ACTION_DETAIL_FIELDS}

    def clean(self) -> dict[str, Any] | None:
        """
        Cleans the form data and validates specific fields based on custom logic. This method overrides the
        base `clean` method to provide additional validation rules for specific fields in the form. If the
        data passes all validation, the cleaned data is returned. If there are validation errors, they are
        added to the form errors.

        :return: Cleaned form data as a dictionary if validation passes, or None if data does not meet
            validation criteria or contains errors.
        :rtype: dict[str, Any] | None
        """
        cleaned_data = super().clean()
        if cleaned_data:
            # Basic validation check and skip detailed validation if the form contains errors or the
            # submit action is SAVE_AND_NEXT_RECOMMENDATION or SAVE_AND_BACK_TO_SUMMARY
            if self.errors or cleaned_data.get("submit_action") in (
                RecommendationActionChoices.SAVE_AND_NEXT_RECOMMENDATION,
                RecommendationActionChoices.SAVE_AND_BACK_TO_SUMMARY,
            ):
                return cleaned_data

            recommendation_actioned = cleaned_data.get("recommendation_actioned")
            if recommendation_actioned == "action_not_planned":
                if cleaned_data["recommendation_category"] == "priority":
                    # Only need a reason for priority recommendations
                    self._require(
                        cleaned_data, "action_not_planned_reason", "Enter a reason why no action will be planned."
                    )
            elif recommendation_actioned == "action_planned":
                self._validate_action_planned(cleaned_data)

        return cleaned_data

    def _validate_action_planned(self, cleaned_data: dict[str, Any]) -> None:
        for field, message in self.PLANNED_ACTION_REQUIRED_FIELDS.items():
            self._require(cleaned_data, field, message)

        is_target_date_provided = cleaned_data.get("target_date_provided")
        if is_target_date_provided == "yes":
            for field, message in self.TARGET_DATE_REQUIRED_FIELDS.items():
                self._require(cleaned_data, field, message)
        elif is_target_date_provided == "no":
            # Only need a reason for priority recommendations
            if cleaned_data["recommendation_category"] == "priority":
                self._require(
                    cleaned_data,
                    "target_date_unavailable_reason",
                    "Enter a reason why no target date has been provided.",
                )

    def _require(self, cleaned_data: dict[str, Any], field: str, message: str) -> None:
        """
        Checks if a specific field exists in the provided dictionary. If the field is
        missing or has a falsy value, an error message is added for the field.

        :param cleaned_data: The dictionary containing data to validate.
        :param field: The key in the dictionary to check for a valid value.
        :param message: The error message to associate with the field if validation fails.
        :return: None
        """
        if not cleaned_data.get(field):
            self.add_error(field, message)


class TipReviewAnswersForm(ModelForm):
    """
    Handles the form functionality for reviewing and confirming answers within a TIP.

    This class is responsible for creating and managing a form that allows users to either confirm the
    information within a TIP or return to the summary page if the information cannot be confirmed.

    :ivar submit_action: A field that represents the user's action to confirm or return to the summary.
    :type submit_action: ChoiceField
    """

    submit_action = ChoiceField(
        required=True,
        choices=(
            ("yes", "Confirm and continue"),
            ("no", "Return to summary"),
        ),
        label="Do you confirm that the information in this TIP is correct",
    )

    class Meta:
        model = Tip
        fields: list[str] = []

    def save(self, commit: bool = True):
        """
        Saves the provided data to the instance and confirms the answers based on
        specified confirmation details. Ensures that the answers cannot be confirmed
        without a proper submission action.

        :param commit: Boolean flag indicating whether to commit the changes to the
            database. Defaults to True.
        :type commit: bool
        :return: The saved instance.
        :rtype: Any
        """
        if self.cleaned_data["submit_action"] != "yes":
            raise ValueError("Cannot confirm answers without submitting")

        confirmation: dict[str, Any] = {
            "confirmed_by": self.cleaned_data["confirmed_by"],
            "confirmed_at": self.cleaned_data["confirmed_at"],
            "confirmation_role": self.cleaned_data["confirmation_role"],
        }
        self.instance.confirm_answers(confirmation)
        return super().save(commit)


class TipBulkReviewForm(ModelForm):
    """
    Represents a form for bulk reviewing tips, providing functionality to either review
    or bypass actions for multiple recommendations at once.

    The form allows users to provide a reason for bulk reviewing and confirm the
    reviewing process. It integrates with the Tip model to mark recommendations as
    reviewed based on user input, ensuring consistent updates with proper validation.

    :ivar bulk_review_reason: A text field enabling users to explain their reason
        for not taking actions on recommendations during the bulk review process.
    :type bulk_review_reason: str
    :ivar confirm_bulk_review: A choice field requiring users to confirm if they
        want to mark all remaining recommendations as reviewed.
    :type confirm_bulk_review: str
    """

    bulk_review_reason = CharField(
        label="Explain why you will not add an action",
        help_text="Provide a reason for bulk reviewing these tips.",
        required=False,
        validators=[MaxLengthValidator(500)],
        widget=forms.Textarea(attrs={"rows": 10, "cols": 40, "max_words": 500}),
    )
    confirm_bulk_review = ChoiceField(
        required=True,
        widget=forms.RadioSelect,
        choices=(
            ("yes", "Yes"),
            ("no", "No"),
        ),
        label="Do you want to mark all remaining other recommendations as reviewed",
    )

    class Meta:
        model = Tip
        fields: list[str] = []

    def clean(self) -> dict[str, Any] | None:
        cleaned_data = super().clean()
        if self.errors or not cleaned_data:
            return cleaned_data

        confirm = cleaned_data.get("confirm_bulk_review", "no")
        if confirm == "yes":
            cleaned_data["bulk_review_reason"] = "Not provided"
        return cleaned_data

    def save(self, commit=True):
        """
        Saves the form instance and handles the bulk processing of recommendations when commit is True.

        This method performs the following operations:
        - Iterates through filtered recommendation data.
        - Checks if a recommendation is already reviewed.
        - If not reviewed, applies the recommendation action based on user inputs.
        - Updates the instance accordingly.

        :param commit: A boolean flag indicating whether to commit the changes to the database. If True,
            the method processes the recommendations and saves the instance. Defaults to True.
        :type commit: bool
        :return: The form instance, after optionally committing the changes.
        """
        if commit:
            reason = self.cleaned_data["bulk_review_reason"]
            for recommendation, _, action in self.cleaned_data["filtered_recommendations_with_group"]:
                # If there is no action set for the recommendation,
                # then we go ahead and set the action as action_not_planned
                if self.instance.get_action(recommendation.id):
                    continue
                self.instance.set_recommendation_action(
                    RecommendationAction(
                        recommendation_reviewed="yes",
                        action_type="action_not_planned",
                        recommendation_id=recommendation.id,
                        recommendation_category="other",
                        action_details={"action_not_planned_reason": reason},
                        actioned_by=self.cleaned_data["actioned_by"],
                        actioned_time=self.cleaned_data["actioned_time"],
                    )
                )
        return super().save(commit=commit)


class TipSubmitForm(ModelForm):
    """
    Handles the creation and validation of the form for submitting tips after confirmation, requiring a
    user confirmation before proceeding.

    This class extends the `ModelForm` class, designed to include a boolean confirmation
    field. It is linked with the `Tip` model and uses the fields specified in its `Meta`
    class for form generation. The confirmation checkbox ensures that the user explicitly
    agrees before submitting the form.

    :ivar confirm: A boolean field requiring user confirmation with a checkbox.
    :type confirm: bool
    """

    confirm = BooleanField(required=True, widget=forms.CheckboxInput, label="Confirm before continuing")

    class Meta:
        model = Tip
        fields: list[str] = []

    def save(self, commit=True):
        """
        Save the form instance after processing the current profile.

        This method extracts the `current_profile` key from the cleaned data, uses it to submit
        a report for the instance, and then proceeds to save the form instance. The save operation
        can either commit changes to the database or only prepare them based on the `commit` parameter.

        :param commit: Indicates whether to commit the save operation to the database.
                       Defaults to True.
        :type commit: bool
        :return: The saved instance of the form or model.
        :rtype: Any
        """
        current_profile = self.cleaned_data.pop("current_profile")
        self.instance.submit_report(current_profile)
        return super().save(commit)
