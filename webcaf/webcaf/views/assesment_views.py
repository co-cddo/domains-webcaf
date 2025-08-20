import re
from collections import namedtuple
from typing import Any, Dict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Subquery
from django.forms import ModelForm
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView

from webcaf.webcaf.models import Assessment, System, UserProfile

# List of keys expected in the assessment data, So that the 'objective' section can be considered complete.
OBJECTIVE_A_KEYS = {
    "indicator_indicators_A1.a",
    "indicator_indicators_A1.b",
    "indicator_indicators_A1.c",
    "indicator_indicators_A2.a",
    "indicator_indicators_A2.b",
    "indicator_indicators_A3.a",
    "indicator_indicators_A4.a",
    "confirmation_indicators_A1.a",
    "confirmation_indicators_A1.b",
    "confirmation_indicators_A1.c",
    "confirmation_indicators_A2.a",
    "confirmation_indicators_A2.b",
    "confirmation_indicators_A3.a",
    "confirmation_indicators_A4.a",
}

OBJECTIVE_B_KEYS = {
    "confirmation_indicators_B1.a",
    "confirmation_indicators_B1.b",
    "confirmation_indicators_B2.a",
    "confirmation_indicators_B2.b",
    "confirmation_indicators_B2.c",
    "confirmation_indicators_B2.d",
    "confirmation_indicators_B3.a",
    "confirmation_indicators_B3.b",
    "confirmation_indicators_B3.c",
    "confirmation_indicators_B3.d",
    "confirmation_indicators_B3.e",
    "confirmation_indicators_B4.a",
    "confirmation_indicators_B4.b",
    "confirmation_indicators_B4.c",
    "confirmation_indicators_B4.d",
    "confirmation_indicators_B5.a",
    "confirmation_indicators_B5.b",
    "confirmation_indicators_B5.c",
    "confirmation_indicators_B6.a",
    "confirmation_indicators_B6.b",
    "indicator_indicators_B1.a",
    "indicator_indicators_B1.b",
    "indicator_indicators_B2.a",
    "indicator_indicators_B2.b",
    "indicator_indicators_B2.c",
    "indicator_indicators_B2.d",
    "indicator_indicators_B3.a",
    "indicator_indicators_B3.b",
    "indicator_indicators_B3.c",
    "indicator_indicators_B3.d",
    "indicator_indicators_B3.e",
    "indicator_indicators_B4.a",
    "indicator_indicators_B4.b",
    "indicator_indicators_B4.c",
    "indicator_indicators_B4.d",
    "indicator_indicators_B5.a",
    "indicator_indicators_B5.b",
    "indicator_indicators_B5.c",
    "indicator_indicators_B6.a",
    "indicator_indicators_B6.b",
}

OBJECTIVE_C_KEYS = {
    "confirmation_indicators_C1.a",
    "confirmation_indicators_C1.b",
    "confirmation_indicators_C1.c",
    "confirmation_indicators_C1.d",
    "confirmation_indicators_C1.e",
    "confirmation_indicators_C2.a",
    "confirmation_indicators_C2.b",
    "indicator_indicators_C1.a",
    "indicator_indicators_C1.b",
    "indicator_indicators_C1.c",
    "indicator_indicators_C1.d",
    "indicator_indicators_C1.e",
    "indicator_indicators_C2.a",
    "indicator_indicators_C2.b",
}

OBJECTIVE_D_KEYS = {
    "confirmation_indicators_D1.a",
    "confirmation_indicators_D1.b",
    "confirmation_indicators_D1.c",
    "confirmation_indicators_D2.a",
    "confirmation_indicators_D2.b",
    "indicator_indicators_D1.a",
    "indicator_indicators_D1.b",
    "indicator_indicators_D1.c",
    "indicator_indicators_D2.a",
    "indicator_indicators_D2.b",
}

ObjectiveRecord = namedtuple("ObjectiveRecord", ["id", "is_complete", "label"])


class EditAssessmentView(LoginRequiredMixin, FormView):
    """
    This view allows users to edit a draft assessment. It handles the retrieval of
    the assessment, renders the form for editing, and processes the updates. The
    view is restricted to logged-in users with appropriate permissions, and it
    validates that the user’s organization has access to the assessment being edited.

    It extends functionality from `LoginRequiredMixin` to enforce login requirements
    and `FormView` to leverage its form handling utilities.

    :ivar login_url: URL to redirect users to if they are not authenticated.
    :type login_url: str
    :ivar template_name: Path to the HTML template used for rendering the page.
    :type template_name: str
    """

    login_url = "/oidc/authenticate/"  #
    template_name = "assessment/draft-assessment.html"

    def get_context_data(self, **kwargs):
        assessment_id = self.kwargs.get("assessment_id")
        current_profile = UserProfile.objects.get(id=self.request.session["current_profile_id"])
        current_organisation = current_profile.organisation
        assessment = Assessment.objects.get(
            id=assessment_id, status="draft", assessment_period="25/26", system__organisation_id=current_organisation.id
        )

        assessment_keys = set(assessment.assessments_data.keys())
        objective_a_complete = OBJECTIVE_A_KEYS == set(
            filter(lambda key: re.match(r".*_A\d{1,}\.[a-z]", key), assessment_keys)
        )
        objective_b_complete = OBJECTIVE_B_KEYS == set(
            filter(lambda key: re.match(r".*_B\d{1,}\.[a-z]", key), assessment_keys)
        )
        objective_c_complete = OBJECTIVE_C_KEYS == set(
            filter(lambda key: re.match(r".*_C\d{1,}\.[a-z]", key), assessment_keys)
        )
        objective_d_complete = OBJECTIVE_D_KEYS == set(
            filter(lambda key: re.match(r".*_D\d{1,}\.[a-z]", key), assessment_keys)
        )
        draft_assessment = {
            "assessment_id": assessment.id,
            "system": assessment.system.id,
            "caf_profile": assessment.caf_profile,
        }
        # We need to access this information later in the assessment editing stages.
        self.request.session["draft_assessment"] = draft_assessment
        from webcaf.webcaf.views.util import get_parent_map

        parent_map: Dict[str, Any] = get_parent_map()

        data = {
            "objectives": [
                ObjectiveRecord("objective_A", objective_a_complete, parent_map["objective_A"]["text"]),
                ObjectiveRecord("objective_B", objective_b_complete, parent_map["objective_B"]["text"]),
                ObjectiveRecord("objective_C", objective_c_complete, parent_map["objective_C"]["text"]),
                ObjectiveRecord("objective_D", objective_d_complete, parent_map["objective_D"]["text"]),
            ],
            "all_complete": objective_a_complete
            and objective_b_complete
            and objective_c_complete
            and objective_d_complete,
            "draft_assessment": draft_assessment,
            "breadcrumbs": [
                {"url": reverse("my-account"), "text": "My account"},
            ]
            + self.breadcrumbs(assessment.id),
            "systems": (
                System.objects.filter(organisation=current_organisation)
                .exclude(
                    # Exclude any systems that already have draft assessments assigned
                    id__in=[Subquery(Assessment.objects.filter(status="draft").values("system_id"))]
                )
                .union(System.objects.filter(id=assessment.system_id))
            ),
        }

        return data

    def get_form_kwargs(self):
        """
        Add the form instance to the kwargs.
        :return:
        """
        kwargs = super().get_form_kwargs()
        assessment_to_modify = Assessment.objects.get(id=self.kwargs.get("assessment_id"), status="draft")
        curren_organisation = UserProfile.objects.get(id=self.request.session["current_profile_id"]).organisation
        if assessment_to_modify.system.id not in curren_organisation.systems.values_list("id", flat=True):
            raise Exception("You are not allowed to edit this assessment")
        kwargs["instance"] = assessment_to_modify
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "edit-draft-assessment", kwargs={"assessment_id": self.kwargs["assessment_id"], "version": "v3.2"}
        )

    def breadcrumbs(self, assessment_id: int):
        return [{"url": "#", "text": "Edit draft assessment"}]


class AssessmentProfileForm(ModelForm):
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
        fields = ["caf_profile"]


class AssessmentSystemForm(ModelForm):
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

    class Meta:
        model = Assessment
        fields = ["system"]


class EditAssessmentProfileView(EditAssessmentView):
    """
    Handles the view for editing the assessment profile.

    This class is responsible for rendering the profile-editing page of an
    assessment. It specifies the template and the form to be used for editing
    the assessment profile. It also provides breadcrumb navigation for the
    editing process.

    :ivar template_name: Path to the HTML template used for rendering the
        profile-editing page.
    :type template_name: str
    :ivar form_class: The form class used for handling the profile-editing
        input.
    :type form_class: type
    """

    template_name = "assessment/caf-profile.html"
    form_class = AssessmentProfileForm

    def breadcrumbs(self, assessment_id: int):
        return [
            {
                "url": reverse(
                    "edit-draft-assessment",
                    kwargs={"assessment_id": assessment_id, "version": "v3.2"},
                ),
                "text": "Edit draft assessment",
            },
            {"url": "#", "text": "Choose Profile"},
        ]


class EditAssessmentSystemView(EditAssessmentView):
    """
    View for editing the assessment system.

    This class is responsible for rendering and managing the form used to edit
    the system details of an assessment. It provides the necessary data and
    behavior to facilitate modification of system-related information for an
    assessment entry.

    :ivar template_name: Path to the HTML template used for rendering the view.
    :type template_name: str
    :ivar form_class: Form class used for managing the system details form.
    :type form_class: Type[forms.Form]
    """

    template_name = "assessment/system-details.html"
    form_class = AssessmentSystemForm

    def breadcrumbs(self, assessment_id: int):
        return [
            {
                "url": reverse(
                    "edit-draft-assessment",
                    kwargs={"assessment_id": assessment_id, "version": "v3.2"},
                ),
                "text": "Edit draft assessment",
            },
            {"url": "#", "text": "Choose System"},
        ]


class CreateAssessmentView(LoginRequiredMixin, FormView):
    """
    Handles the creation of draft assessments by authenticated users.

    Provides functionality to create, manage, and navigate draft assessments
    linked to a user's organisation and selected system. This view ensures that
    only authenticated users can access this feature and handles specific
    workflows related to draft assessments.

    :ivar login_url: URL path for unauthenticated users to be redirected to login.
    :type login_url: str
    :ivar template_name: Path to the HTML template for rendering the view.
    :type template_name: str
    """

    login_url = "/oidc/authenticate/"  # OIDC login route
    template_name = "assessment/draft-assessment.html"

    def get_context_data(self, **kwargs):
        data = {}
        profile_id = self.request.session["current_profile_id"]
        profile = UserProfile.objects.get(user=self.request.user, id=profile_id)
        data["breadcrumbs"] = [
            {"url": reverse("my-account"), "text": "My account"},
        ] + self.breadcrumbs()
        data["profile"] = profile
        data["draft_assessment"] = self.request.session.get("draft_assessment", {})
        # Show only the systems needing new drafts
        data["systems"] = System.objects.filter(organisation=profile.organisation).exclude(
            id__in=[Subquery(Assessment.objects.filter(status="draft").values("system_id"))]
        )
        return data

    def get_success_url(self):
        return reverse("create-draft-assessment")

    def form_valid(self, form):
        """
        Handles the validation of the form and processes the draft assessment session data.
        It attempts to create or retrieve an existing draft assessment for a system within the
        current user's organisation, sets the necessary attributes, and forwards to edit
        the draft assessment upon successful operation.

        :param form: The form instance that has been validated.
        :type form: Form
        :return: Response following the validation of the form.
        :rtype: HttpResponse
        """
        draft_assessment = self.request.session["draft_assessment"]
        current_organisation = UserProfile.objects.get(id=self.request.session["current_profile_id"]).organisation
        if "system" in draft_assessment and "caf_profile" in draft_assessment:
            # If both the mandatory fields are provided, then we can go ahead and
            # create the assessment instance in the database. This enables us to
            # forward the user to the editing screen with an known assessment id.
            system = System.objects.get(id=draft_assessment["system"], organisation=current_organisation)
            assessment, _ = Assessment.objects.get_or_create(
                status="draft",
                assessment_period="25/26",
                system=system,
                version="v3.2",
                defaults={
                    "created_by": self.request.user,
                    "caf_profile": draft_assessment["caf_profile"],
                    "last_updated_by": self.request.user,
                },
            )
            draft_assessment["assessment_id"] = assessment.id
            assessment.last_updated_by = self.request.user
            assessment.save()
            # Forward to editing the draft now.
            return redirect(
                reverse("edit-draft-assessment", kwargs={"assessment_id": assessment.id, "version": "v3.2"})
            )
        return super().form_valid(form)

    def breadcrumbs(self):
        return [{"url": "#", "text": "Start a draft assessment"}]


class CreateAssessmentProfileView(CreateAssessmentView):
    """
    Handles the creation of an assessment profile through a web form interface.

    This class provides functionality for rendering a CAF profile selection form, processing the
    form submission, and updating the draft assessment stored in the session. It also generates
    breadcrumbs used for navigation on the interface.

    Inherits from:
        CreateAssessmentView

    :ivar form_class: The Django form class used for CAF profile selection.
    :type form_class: type
    :ivar template_name: The path to the template used for rendering the CAF profile selection page.
    :type template_name: str
    """

    form_class = AssessmentProfileForm
    template_name = "assessment/caf-profile.html"

    def form_valid(self, form):
        draft_assessment = self.request.session["draft_assessment"]
        draft_assessment["caf_profile"] = form.cleaned_data["caf_profile"]
        self.request.session.save()
        return super().form_valid(form)

    def breadcrumbs(self):
        return [
            {"url": reverse("create-draft-assessment"), "text": "Start a draft assessment"},
            {"url": "#", "text": "Choose a CAF profile"},
        ]


class CreateAssessmentSystemView(CreateAssessmentView):
    """
    CreateAssessmentSystemView class.

    Handles the process of selecting and managing the system details for an assessment,
    using the provided form class. The class is responsible for rendering the system
    detail template and processing valid form submissions to update the draft assessment.

    Inherits from CreateAssessmentView.

    :ivar form_class: Specifies the form class used for creating or updating the system
        details in the assessment.
    :type form_class: type
    :ivar template_name: Path to the template used to render the system details page.
    :type template_name: str
    """

    form_class = AssessmentSystemForm
    template_name = "assessment/system-details.html"

    def form_valid(self, form):
        draft_assessment = self.request.session["draft_assessment"]
        draft_assessment["system"] = form.cleaned_data["system"].id
        self.request.session.save()
        return super().form_valid(form)

    def breadcrumbs(self):
        return [
            {"url": reverse("create-draft-assessment"), "text": "Start a draft assessment"},
            {"url": "#", "text": "Choose System"},
        ]
