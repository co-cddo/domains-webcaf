import logging
from datetime import datetime
from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.db.models import Subquery
from django.urls import reverse
from django.views.generic.edit import UpdateView

from webcaf.webcaf.forms.assessment import (
    AssessmentProfileForm,
    AssessmentReviewTypeForm,
    AssessmentSystemForm,
    BaseAssessmentForm,
)
from webcaf.webcaf.models import Assessment, Configuration, System, UserProfile
from webcaf.webcaf.utils.permission import AssessmentProfileCheckMixin, PermissionUtil
from webcaf.webcaf.utils.session import SessionUtil


class EditAssessmentView(AssessmentProfileCheckMixin, UpdateView):
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
    logger = logging.getLogger("EditAssessmentView")
    form_class = BaseAssessmentForm
    model = Assessment

    def get_allowed_roles(self) -> list[str]:
        return ["organisation_lead", "organisation_user", "cyber_advisor"]

    def get_queryset(self):
        queryset = super().get_queryset()
        current_profile = SessionUtil.get_current_user_profile(self.request)
        return queryset.filter(
            system__organisation=current_profile.organisation,
            status="draft",
        )

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs) or {}
        current_profile = UserProfile.objects.get(id=self.request.session["current_profile_id"])
        current_organisation = current_profile.organisation
        draft_assessment = {
            "assessment_uid": str(self.object.uid),
            "assessment_id": self.object.id,
            "system": self.object.system.id,
            "caf_profile": self.object.caf_profile,
            "framework": self.object.framework,
            "review_type": self.object.review_type,
        }
        # We need to access this information later in the assessment editing stages.
        self.request.session["draft_assessment"] = draft_assessment
        user_profile = SessionUtil.get_current_user_profile(self.request)
        configuration = Configuration.objects.get_default_config()

        display_until = configuration.get_banner_display_until()
        display_until = datetime.strptime(display_until, "%d %B %Y %I:%M%p")
        data.update(
            {
                "draft_assessment": draft_assessment,
                "assessment": self.object,
                "progress": True,
                "objectives": self.object.get_router().get_sections(),
                "breadcrumbs": [
                    {"url": reverse("my-account"), "text": "My account"},
                ]
                + self.breadcrumbs(self.object.uid),
                "systems": (
                    System.objects.filter(organisation=current_organisation)
                    .exclude(
                        # Exclude any systems that already have assessments assigned for the current year
                        id__in=[
                            Subquery(
                                Assessment.objects.filter(
                                    status__in=["draft", "submitted", "completed"],
                                    assessment_period__in=[configuration.get_current_assessment_period()],
                                ).values("system_id")
                            )
                        ]
                    )
                    .union(System.objects.filter(id=self.object.system_id))
                ).order_by("name"),
                "current_profile": user_profile,
                "current_assessment_period": configuration.get_current_assessment_period(),
                "cutoff_time": display_until.strftime("%I:%M%p").lower(),
                "cutoff_date": display_until.strftime("%d %B %Y"),
            }
        )

        return data

    def breadcrumbs(self, assessment_uid: UUID):
        return [{"url": "#", "text": "Edit draft self-assessment"}]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs | {"organisation": SessionUtil.get_current_user_profile(self.request).organisation}

    def form_valid(self, form):
        """
        Handle a valid form submission.
        Confirm that the current user has permission to edit assessments before proceeding with form processing.

        :param form: The valid form instance containing cleaned data.
        :type form: BaseAssessmentForm
        :return: An HTTP response indicating successful processing of the form.
        :rtype: HttpResponse
        """
        current_user = SessionUtil.get_current_user_profile(self.request)
        if not PermissionUtil.current_user_can_edit_assessments(current_user):
            raise PermissionDenied("You do not have permission to edit assessments.")
        return super().form_valid(form)


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

    template_name = "caf/assessment/assessment-profile.html"
    form_class = AssessmentProfileForm

    def form_valid(self, form):
        draft_assessment = self.request.session["draft_assessment"]
        draft_assessment["caf_profile"] = form.cleaned_data["caf_profile"]
        if form.cleaned_data["caf_profile"] == "enhanced":
            # We force change the review type to independent if the profile is enhanced
            draft_assessment["review_type"] = "independent"

        form.instance.review_type = draft_assessment["review_type"]
        # Save the data
        return super().form_valid(form)

    def get_success_url(self):
        draft_assessment = self.request.session["draft_assessment"]
        if draft_assessment["caf_profile"] == "enhanced":
            return reverse(
                "edit-draft-assessment-choose-review-type",
                kwargs={"assessment_uid": draft_assessment["assessment_uid"]},
            )
        return reverse("edit-draft-assessment", kwargs={"assessment_uid": draft_assessment["assessment_uid"]})

    def breadcrumbs(self, assessment_uid: UUID):
        return [
            {
                "url": reverse(
                    "edit-draft-assessment",
                    kwargs={
                        "assessment_uid": str(assessment_uid),
                    },
                ),
                "text": "Edit draft self-assessment",
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

    template_name = "caf/assessment/system-details.html"
    form_class = AssessmentSystemForm

    def form_valid(self, form):
        draft_assessment = self.request.session["draft_assessment"]
        current_user_profile = SessionUtil.get_current_user_profile(self.request)
        if form.cleaned_data["system"].organisation != current_user_profile.organisation:
            # Just to make sure that the user is sending back the correct system
            # From the allowed systems for the organisation.
            raise PermissionDenied("You do not have access to this system")
        draft_assessment["system"] = form.cleaned_data["system"].id
        return super().form_valid(form)

    def form_invalid(self, form):
        """
        Handle invalid form submissions.
        The systems fiiis can only be invalid if the suer chooses a system that is not in the list of available systems for the organisation.
        :param form:
        :return:
        """
        if (
            form.errors["system"]
            and "Select a valid choice. That choice is not one of the available choices." in form.errors["system"]
        ):
            raise PermissionDenied("You do not have access to this system")
        return super().form_invalid(form)

    def get_success_url(self):
        draft_assessment = self.request.session["draft_assessment"]
        return reverse("edit-draft-assessment", kwargs={"assessment_uid": draft_assessment["assessment_uid"]})

    def breadcrumbs(self, assessment_uid: UUID):
        return [
            {
                "url": reverse(
                    "edit-draft-assessment",
                    kwargs={
                        "assessment_uid": str(assessment_uid),
                    },
                ),
                "text": "Edit draft self-assessment",
            },
            {"url": "#", "text": "Choose system"},
        ]


class EditAssessmentReviewTypeView(EditAssessmentView):
    """
    View for editing the assessment review type.

    This class is responsible for rendering and managing the form used to edit
    the review type of an assessment. It provides the necessary data and
    behavior to facilitate modification of review type information for an
    assessment entry.

    :ivar template_name: Path to the HTML template used for rendering the view.
    :type template_name: str
    :ivar form_class: Form class used for managing the review type form.
    :type form_class: Type[forms.Form]
    """

    form_class = AssessmentReviewTypeForm
    template_name = "assessment/choose-review-type.html"

    def form_valid(self, form):
        draft_assessment = self.request.session["draft_assessment"]
        draft_assessment["review_type"] = form.cleaned_data["review_type"]
        self.request.session.save()
        return super().form_valid(form)

    def breadcrumbs(self, assessment_uid: UUID):
        return [
            {
                "url": reverse(
                    "edit-draft-assessment",
                    kwargs={
                        "assessment_uid": str(assessment_uid),
                    },
                ),
                "text": "Edit draft self-assessment",
            },
            {"url": "#", "text": "Choose review type"},
        ]

    def get_success_url(self):
        return reverse("edit-draft-assessment", kwargs={"assessment_uid": self.kwargs["assessment_uid"]})
