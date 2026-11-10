import logging
from abc import ABC, abstractmethod

from django.core.exceptions import PermissionDenied
from django.db.models import Subquery
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView, TemplateView

from webcaf.webcaf.forms.assessment import (
    AssessmentProfileForm,
    AssessmentReviewTypeForm,
    AssessmentSystemForm,
)
from webcaf.webcaf.models import (
    Assessment,
    Configuration,
    System,
    UserProfile,
)
from webcaf.webcaf.utils.permission import AssessmentProfileCheckMixin
from webcaf.webcaf.utils.session import SessionUtil


class CreateAssessmentMixin(AssessmentProfileCheckMixin, CreateView, ABC):

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

        if (
            draft_assessment.get("caf_profile")
            and draft_assessment.get("review_type")
            and draft_assessment.get("system")
        ):
            # Extra check to confirm the system belongs to the organisation
            system = System.objects.get(id=draft_assessment["system"], organisation=current_organisation)
            if not system:
                raise PermissionDenied("You do not have access to this system")
            configuration = Configuration.objects.get_default_config()

            assessment, _ = Assessment.objects.get_or_create(
                status="draft",
                assessment_period=configuration.get_current_assessment_period(),
                system=system,
                framework=configuration.get_default_framework(),
                defaults={
                    "created_by": self.request.user,
                    "caf_profile": draft_assessment["caf_profile"],
                    "last_updated_by": self.request.user,
                    "review_type": draft_assessment["review_type"],
                    "submission_due_date": configuration.get_submission_due_date(),
                },
            )
            draft_assessment["assessment_id"] = assessment.id
            draft_assessment["framework"] = assessment.framework
            # Set the manually created instance as the object attribute to continue the flow
            self.object = assessment
            self.logger.info(f"Assessment {assessment.id} created by {self.request.user.pk}")
        return redirect(self.get_success_url())

    @abstractmethod
    def get_success_url(self) -> str: ...

    @property
    def logger(self):
        return logging.getLogger(self.__class__.__name__)

    def get_context_data(self, **kwargs):
        from webcaf.webcaf.frameworks import routers

        data = super().get_context_data(**kwargs)
        profile = SessionUtil.get_current_user_profile(self.request)
        data["breadcrumbs"] = [
            {"url": reverse("my-account"), "text": "My account"},
        ] + self.breadcrumbs()
        data["profile"] = profile
        data["progress"] = True
        data["draft_assessment"] = self.request.session.get("draft_assessment", {})

        configuration = Configuration.objects.get_default_config()
        # Hard code the router class version for now
        router = routers[configuration.get_default_framework()]
        data["objectives"] = router.get_sections()

        current_assessment_period = configuration.get_current_assessment_period()
        data["current_assessment_period"] = current_assessment_period
        data["cutoff_time"] = configuration.get_submission_due_date().strftime("%I:%M%p").lower()
        data["cutoff_date"] = configuration.get_submission_due_date().strftime("%d %B %Y")

        data["systems"] = (
            System.objects.filter(organisation=profile.organisation)
            .exclude(
                # Exclude any systems that already have assessments assigned for the current year
                id__in=[
                    Subquery(
                        Assessment.objects.filter(
                            status__in=["draft", "submitted", "completed"],
                            assessment_period__in=[current_assessment_period],
                        ).values("system_id")
                    )
                ]
            )
            .order_by("name")
        )
        return data

    def get_allowed_roles(self) -> list[str]:
        """
        Only org leads can start an assessment
        :return:
        """
        return ["organisation_lead"]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs | {"organisation": SessionUtil.get_current_user_profile(self.request).organisation}


class CreateAssessmentView(AssessmentProfileCheckMixin, TemplateView):
    """
    Initial page for creating an assessment. This view is responsible for rendering the initial
    page where users can start the process of creating a draft assessment.

    :ivar login_url: URL path for unauthenticated users to be redirected to login.
    :type login_url: str
    :ivar template_name: Path to the HTML template for rendering the view.
    :type template_name: str
    """

    login_url = "/oidc/authenticate/"  # OIDC login route
    template_name = "assessment/draft-assessment.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["breadcrumbs"] = self.breadcrumbs()
        data["draft_assessment"] = self.request.session["draft_assessment"]
        configuration = Configuration.objects.get_default_config()
        from webcaf.webcaf.frameworks import routers

        router = routers[configuration.get_default_framework()]
        data["objectives"] = router.get_sections()
        current_assessment_period = configuration.get_current_assessment_period()
        data["current_assessment_period"] = current_assessment_period
        data["cutoff_time"] = configuration.get_submission_due_date().strftime("%I:%M%p").lower()
        data["cutoff_date"] = configuration.get_submission_due_date().strftime("%d %B %Y")
        return data

    def breadcrumbs(self):
        return [{"url": reverse("my-account"), "text": "My account"}, {"url": "#", "text": "Start a draft assessment"}]

    def get_allowed_roles(self) -> list[str]:
        """
        Only org leads can start an assessment
        :return:
        """
        return ["organisation_lead"]


class CreateAssessmentSystemView(CreateAssessmentMixin):
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
        current_user_profile = SessionUtil.get_current_user_profile(self.request)
        if form.cleaned_data["system"].organisation != current_user_profile.organisation:
            # Just to make sure that the user is sending back the correct system
            # From the allowed systems for the organisation.
            raise PermissionDenied("You do not have access to this system")
        draft_assessment["system"] = form.cleaned_data["system"].id
        # We store the data in the session and redirect to the next step
        return redirect(self.get_success_url())

    def breadcrumbs(self):
        return [
            {"url": reverse("create-draft-assessment"), "text": "Start a draft assessment"},
            {"url": "#", "text": "Choose system"},
        ]

    def get_success_url(self) -> str:
        return reverse("create-draft-assessment")


class CreateAssessmentProfileView(CreateAssessmentMixin):
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
        if form.cleaned_data["caf_profile"] == "enhanced":
            draft_assessment["review_type"] = "independent"
        return super().form_valid(form)

    def get_success_url(self) -> str:
        draft_assessment = self.request.session["draft_assessment"]
        if self.object:
            if draft_assessment["caf_profile"] == "enhanced":
                return reverse("edit-draft-assessment-choose-review-type", kwargs={"assessment_id": self.object.id})
            return reverse("edit-draft-assessment", kwargs={"assessment_id": self.object.id})
        return reverse("create-draft-assessment")

    def breadcrumbs(self):
        return [
            {"url": reverse("create-draft-assessment"), "text": "Start a draft assessment"},
            {"url": "#", "text": "Choose a CAF profile"},
        ]


class CreateAssessmentReviewTypeView(CreateAssessmentMixin):
    """
    CreateAssessmentReviewTypeView class.

    Handles the process of selecting and managing the review type for an assessment,
    using the provided form class. The class is responsible for rendering the review type
    template and processing valid form submissions to update the draft assessment.

    Inherits from CreateAssessmentView.

    :ivar template_name: Path to the HTML template used for rendering the view.
    :type template_name: str
    :ivar form_class: Form class used for managing the review type form.
    :type form_class: Type[forms.Form]
    """

    form_class = AssessmentReviewTypeForm
    template_name = "assessment/choose-review-type.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        return data

    def form_valid(self, form):
        draft_assessment = self.request.session["draft_assessment"]
        draft_assessment["review_type"] = form.cleaned_data["review_type"]
        return super().form_valid(form)

    def get_success_url(self):
        if self.object:
            return reverse("edit-draft-assessment", kwargs={"assessment_id": self.object.id})
        return reverse("create-draft-assessment")

    def form_invalid(self, form) -> HttpResponse:
        return super().form_invalid(form)

    def breadcrumbs(self):
        return [
            {"url": reverse("create-draft-assessment"), "text": "Start a draft assessment"},
            {"url": "#", "text": "Choose review type"},
        ]
