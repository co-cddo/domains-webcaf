import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Subquery
from django.forms import ModelForm
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView

from webcaf.webcaf.models import Assessment, System, UserProfile
from webcaf.webcaf.utils.session import SessionUtil


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

    login_url = "/oidc/authenticate/"
    template_name = "assessment/draft-assessment.html"
    logger = logging.Logger("EditAssessmentView")

    def get_context_data(self, **kwargs):
        assessment_id = self.kwargs.get("assessment_id")
        current_profile = UserProfile.objects.get(id=self.request.session["current_profile_id"])
        current_organisation = current_profile.organisation
        assessment = Assessment.objects.get(
            id=assessment_id, status="draft", system__organisation_id=current_organisation.id
        )
        draft_assessment = {
            "assessment_id": assessment.id,
            "system": assessment.system.id,
            "caf_profile": assessment.caf_profile,
            "framework": assessment.framework,
        }
        # We need to access this information later in the assessment editing stages.
        self.request.session["draft_assessment"] = draft_assessment
        user_profile = SessionUtil.get_current_user_profile(self.request)
        data = {
            "draft_assessment": draft_assessment,
            "objectives": assessment.get_router().get_sections(),
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
            "current_profile": user_profile,
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
            self.logger.error(
                f"The user {self.request.user} does not have access to this assessment {assessment_to_modify}"
            )
            raise PermissionError("You are not allowed to edit this assessment")
        kwargs["instance"] = assessment_to_modify
        return kwargs

    def get_success_url(self):
        return reverse("edit-draft-assessment", kwargs={"assessment_id": self.kwargs["assessment_id"]})

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

    template_name = "assessment-profile.html"
    form_class = AssessmentProfileForm

    def breadcrumbs(self, assessment_id: int):
        return [
            {
                "url": reverse(
                    "edit-draft-assessment",
                    kwargs={
                        "assessment_id": assessment_id,
                    },
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

    template_name = "system/system-details.html"
    form_class = AssessmentSystemForm

    def breadcrumbs(self, assessment_id: int):
        return [
            {
                "url": reverse(
                    "edit-draft-assessment",
                    kwargs={
                        "assessment_id": assessment_id,
                    },
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
    logger = logging.Logger("CreateAssessmentView")

    def get_context_data(self, **kwargs):
        from webcaf.webcaf.frameworks import routers

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
        # Hard code the router class version for now
        router = routers["caf32"]
        data["objectives"] = router.get_sections()
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
            draft_assessment["framework"] = assessment.framework
            assessment.last_updated_by = self.request.user
            assessment.save()
            self.logger.info(f"Assessment {assessment.id} created by {self.request.user.username}")
            # Forward to editing the draft now.
            return redirect(reverse("edit-draft-assessment", kwargs={"assessment_id": assessment.id}))
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
    template_name = "assessment-profile.html"

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
    template_name = "system/system-details.html"

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
