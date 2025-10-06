import logging
import random
import string
from collections import namedtuple
from datetime import datetime
from typing import Any

from django.forms import Form
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic import FormView, TemplateView

from webcaf.webcaf.models import Assessment
from webcaf.webcaf.templatetags.form_extras import (
    get_assessment,
    is_all_objectives_complete,
)
from webcaf.webcaf.utils.permission import UserRoleCheckMixin
from webcaf.webcaf.utils.session import SessionUtil


class SectionConfirmationView(UserRoleCheckMixin, FormView):
    """
    Represents a view to handle the confirmation page for a main section
    of an assessment.

    For the purpose of the Cyber Assessment Framework (CAF), a main section
    is an 'Objective'.

    :ivar template_name: Path to the template used to render the objective
        confirmation page.
    :type template_name: str
    """

    template_name = "assessment/objective-confirmation.html"
    form_class = Form
    logger = logging.Logger("ObjectiveConfirmationView")

    def get_allowed_roles(self) -> list[str]:
        return ["organisation_lead"]

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        assessment = get_assessment(self.request)
        # Come back to this.
        if assessment:
            data["objectives"] = assessment.get_router().get_sections()
        data["user_profile"] = SessionUtil.get_current_user_profile(self.request)
        return data

    def generate_reference(self) -> str:
        """
        Generate application reference with the following format:
        CAF + date in DDMMYYYY + random 4 letter alphabetical characters ( which don't have vowels and Y )
        e.g. 'CAF12042024TRFT'

        Returns:
            str: application reference.
        """

        random_letters = [letter for letter in string.ascii_uppercase if letter not in "AEIOUY"]
        random_string = "".join(random.choices(random_letters, k=4))
        return ("CAF") + datetime.today().strftime("%d%m%Y") + random_string

    def form_valid(self, form):
        """
        Validates the submitted form and handles assessment processing.

        If a current assessment exists in the session, checks whether all sections
        of the assessment are completed. If completed and the assessment is in
        draft status, updates the assessment status to 'submitted', generates a
        reference for it, sets the user who last updated it, and saves the updated
        assessment. Logs the actions performed. Redirects to the submission
        confirmation page if successful.

        If the assessment sections are not completed, logs the unauthorized
        submission attempt and redirects back to the account page. If no assessment
        is found in the session, logs the absence and redirects to the account page.

        :param form: The submitted form object that is validated.
        :type form: Form
        :return: A redirect response to the appropriate page based on the validation outcome.
        :rtype: HttpResponseRedirect
        """
        assessment = SessionUtil.get_current_assessment(self.request)
        if assessment:
            if is_all_objectives_complete(assessment.id):
                if assessment.status == "draft":
                    assessment.reference = self.generate_reference()
                    assessment.last_updated_by = self.request.user
                    assessment.status = "submitted"
                    assessment.save()
                    self.logger.info(f"Assessment {assessment.id} reference {assessment.reference} generated")
                else:
                    self.logger.info(f"Assessment {assessment.id} already submitted")
                return redirect(reverse("show-submission-confirmation"))
            else:
                # User has not completed all objectives and should not have reached this page
                self.logger.info(
                    f"User {self.request.user.username} has not completed all objectives, but tried to submit {assessment.id}"
                )
        else:
            self.logger.info(f"No assessment found in session {self.request.user.username}")

        return redirect(reverse("my-account"))


class ShowSubmissionConfirmationView(UserRoleCheckMixin, TemplateView):
    """
    Handles the display of a confirmation page upon completion of a specific assessment action.

    This class-based view renders a template that provides confirmation that an assessment
    process has been successfully completed. The purpose of this view is to present the
    user with a visual acknowledgment and any additional relevant information associated
    with the successful completion.

    :ivar template_name: The path to the template used for confirmation display.
    :type template_name: str
    """

    template_name = "assessment/completed-confirmation.html"

    def get_allowed_roles(self) -> list[str]:
        return ["organisation_lead"]

    def get_context_data(self, **kwargs):
        assessment = get_assessment(self.request, "submitted")
        if assessment:
            return {"assessment_ref": assessment.reference}
        return {}


class ViewSubmittedAssessmentsView(UserRoleCheckMixin, TemplateView):
    """
    Represents a view for displaying submitted assessments in the user's account.

    This class inherits from `MyAccountView` and sets the template for displaying
    submitted assessments. It is used for rendering user-specific submitted assessments
    on the corresponding user interface.

    :ivar template_name: The path to the HTML template file used for rendering
        the submitted assessments page.
    :type template_name: str
    """

    template_name = "user-pages/submitted-assessments.html"
    logger = logging.Logger("ViewSubmittedAssessmentsView")

    def get_allowed_roles(self) -> list[str]:
        return [
            "organisation_lead",
            "cyber_advisor",
        ]

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        submitted_assessments = list(
            Assessment.objects.filter(
                system__organisation=SessionUtil.get_current_user_profile(self.request).organisation,
                status__in=["submitted"],
            )
            .only(
                "id",
                "system__name",
                "caf_profile",
                "system__organisation__name",
                "created_on",
                "last_updated",
                "assessment_period",
                "created_by__username",
                "assessments_data",
            )
            .all()
        )

        # Check the history table of the assessment to see when the status was changed to submitted
        submitted_date_map = first_submitted_changes([assessment.id for assessment in submitted_assessments])
        data["submitted_assessments"] = []
        for assessment in submitted_assessments:
            if assessment.id in submitted_date_map:
                data["submitted_assessments"].append((assessment, submitted_date_map[assessment.id]))
            else:
                self.logger.warning(f"Assessment {assessment.id} has no submitted date")
                data["submitted_assessments"].append((assessment,))
        data["breadcrumbs"] = [{"url": reverse("my-account"), "text": "back", "class": "govuk-back-link"}]
        return data


class ViewSubmittedAssessment(UserRoleCheckMixin, TemplateView):
    template_name = "caf/assessment/completed-assessment.html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.Logger(self.__class__.__name__)

    def get_allowed_roles(self) -> list[str]:
        return [
            "organisation_lead",
            "cyber_advisor",
        ]

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        user_profile = SessionUtil.get_current_user_profile(self.request)
        if not user_profile:
            raise PermissionError("You are not allowed to view this page")
        assessment = Assessment.objects.get(
            id=kwargs["assessment_id"], status="submitted", system__organisation=user_profile.organisation
        )
        submitted_changes = first_submitted_changes(
            [
                assessment.id,
            ]
        )
        first_submitted_on = submitted_changes[assessment.id] if assessment.id in submitted_changes else None
        data: dict[str, Any] = {
            "assessment": assessment,
            "objectives": assessment.get_router().get_sections(),
            "breadcrumbs": [{"url": reverse("my-account"), "text": "back", "class": "govuk-back-link"}],
            "first_submitted": first_submitted_on,
        }
        return data


class DownloadSubmittedAssessmentPdf(ViewSubmittedAssessment):
    template_name = "caf/assessment/completed-assessment.html"

    def get(self, request, *args, **kwargs):
        self.logger.info(f"Downloading assessment {kwargs['assessment_id']} for user {request.user.username}")
        # Local import to avoid crashing the app if the dependency is not installed
        # on the developer machines
        from django.conf import settings
        from weasyprint import HTML

        # Render the template as HTML
        context = self.get_context_data(**kwargs)
        html_string = render_to_string(self.template_name, context, request=request)

        # Generate PDF
        # Need to set the absolute path to the static files as pdf generation does not work with relative paths
        html_string = html_string.replace(
            "/assets/govuk-frontend-5.11.1.min.css", f"file://{settings.STATIC_ROOT}/govuk-frontend-5.11.1.min.css"
        )
        html_string = html_string.replace("/assets/application.css", f"file://{settings.STATIC_ROOT}/application.css")
        pdf = HTML(
            string=html_string,
        ).write_pdf()
        pdf_file = pdf

        # Return as PDF response
        response = HttpResponse(pdf_file, content_type="application/pdf")
        assessment_ = context["assessment"]
        response["Content-Disposition"] = f'inline; filename="{assessment_.reference}.pdf"'
        return response


# Type for history records of assessments
SubmittedTime = namedtuple("SubmittedTime", ["date", "user"])


def first_submitted_changes(assessment_ids: list[int]) -> dict[int, SubmittedTime]:
    """
    Determines the earliest submission date for assessments that transitioned from
    'draft' to 'submitted' within the given list of assessment IDs.

    This function examines the historical records of assessments to identify the
    first date when each assessment changed its status from 'draft' to 'submitted'.
    The result is a dictionary mapping each assessment ID to this first occurrence
    date.

    :param assessment_ids: List of assessment IDs to analyze.
    :type assessment_ids: list[int]
    :return: A dictionary where the keys are assessment IDs and the values are
        their respective first submission dates.
    :rtype: dict[int, datetime]
    """
    results = {}
    HistoricalAssessment = Assessment.history.model
    # Get all history rows for those assessments, ordered by time
    histories = (
        HistoricalAssessment.objects.filter(id__in=assessment_ids)
        .order_by("id", "history_date")
        .only("id", "status", "history_date")
    )

    prev_status: dict[int, str] = {}
    for h in histories:
        aid = h.id
        current = h.status
        prev = prev_status.get(aid)

        # detect transition draft -> submitted
        if prev == "draft" and current == "submitted" and aid not in results:
            results[aid] = SubmittedTime(h.history_date, h.last_updated_by.email)

        prev_status[aid] = current

    return results
