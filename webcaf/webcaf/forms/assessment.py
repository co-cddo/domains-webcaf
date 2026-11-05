from django import forms
from django.forms import ModelChoiceField

from webcaf.webcaf.models import (
    Assessment,
    System,
)


class BaseAssessmentForm(forms.ModelForm):
    """
    Blank form for the base FormView classes
    """

    class Meta:
        model = Assessment
        fields: list = []

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        # We expect the organisation to be passed in as a keyword argument
        self.organisation = kwargs.pop("organisation")
        super().__init__(*args, **kwargs)


class ImportAssessmentExcelForm(forms.Form):
    """
    Form for importing a CAF Excel file.
    """

    excel_file = forms.FileField(
        label="Excel file",
        widget=forms.FileInput(attrs={"class": "govuk-file-upload", "accept": ".xlsx"}),
    )


class AssessmentProfileForm(BaseAssessmentForm):
    """
    Represents a ModelForm for the `Assessment` model to handle the input and
    validation of the `caf_profile` field.

    This form is specifically designed to link to the `Assessment` model and manage
    the `caf_profile` field for creation or update purposes.

    :ivar model: Specifies the model class associated with this form.
    :type model: Type[Model]
    :ivar fields: Defines a list of fields to be included in the form.
    :type fields: List[str]
    """

    class Meta:
        model = Assessment
        fields = ["caf_profile", "review_type"]
        labels = {"caf_profile": "CAF profile"}
        error_messages = {"caf_profile": {"required": "Select a profile for this system"}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # We do not expect to have the review type field from the UI
        self.fields["review_type"].required = False


class AssessmentSystemForm(BaseAssessmentForm):
    """
    Form for handling assessment system data.

    This class is used to represent a form for the `Assessment` model. It allows
    manipulating and validating the `system` field of the corresponding model.
    Typically, it is utilized in contexts where users need to submit or edit
    information related to the system attribute of an assessment.

    :ivar Meta.model: Links `Assessment` model with this form. Defines the model
        this form is associated with.
    :type Meta.model: Model
    :ivar Meta.fields: Specifies the fields to include in the form. Ensures only
        the `system` field from the `Assessment` model is used in this form.
    :type Meta.fields: list
    """

    system: ModelChoiceField = ModelChoiceField(
        queryset=None,
        label="System",
        widget=forms.Select(attrs={"class": "govuk-select", "id": "system_uid"}),
        error_messages={"required": "Select a system for this assessment"},
        to_field_name="uid",
    )

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        # We expect the organisation to be passed in as a keyword argument
        self.fields["system"].queryset = System.objects.filter(organisation=self.organisation).order_by("name")

    class Meta:
        model = Assessment
        fields = ["system"]


class AssessmentReviewTypeForm(BaseAssessmentForm):
    """
    Form for handling the assessment review type data
    """

    class Meta:
        model = Assessment

        fields = ["review_type"]
        widgets = {
            "review_type": forms.RadioSelect(
                attrs={
                    "class": "govuk-radios__input",
                    "form": "assessmentreviewtypeForm",
                }
            ),
        }
        error_messages = {"review_type": {"required": "Select a review type for your self-assessment"}}
