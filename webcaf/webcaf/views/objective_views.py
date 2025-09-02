import logging
import random
import string
from datetime import datetime

from django import forms
from django.forms import Form
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView, TemplateView

from webcaf.webcaf.templatetags.form_extras import (
    get_assessment,
    is_all_objectives_complete,
)
from webcaf.webcaf.views.session_utils import SessionUtil
from webcaf.webcaf.views.util import UserRoleCheckMixin


class ObjectiveConfirmationForm(Form):
    """
    A form to confirm whether an objective has been completed on time.

    This form is used to collect user input for verifying if the objective
    was completed within the intended deadline. It includes a single field
    for this purpose.

    :ivar completed_on_time: A field indicating whether the objective was
        completed on time.
    :type completed_on_time: forms.BooleanField
    """

    completed_on_time = forms.BooleanField(
        required=True,
    )


class ObjectiveConfirmationView(UserRoleCheckMixin, FormView):
    """
    Represents a view to handle the objective confirmation page.

    This view is responsible for rendering the template associated with the
    objective confirmation process. It provides the necessary context data,
    including the objectives fetched using an external helper class. The
    primary responsibility of this view is to render the template with all
    required data, ensuring seamless user interaction.

    :ivar template_name: Path to the template used to render the objective
        confirmation page.
    :type template_name: str
    """

    template_name = "assessment/objective-confirmation.html"
    form_class = ObjectiveConfirmationForm
    logger = logging.Logger("ObjectiveConfirmationView")

    def get_allowed_roles(self) -> list[str]:
        return ["organisation_lead"]

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        assessment = get_assessment(self.request)
        # Come back to this.
        if assessment:
            data["objectives"] = assessment.get_router().get_main_headings()
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

        If a current assessment exists in the session, checks whether all objectives
        of the assessment are completed. If completed and the assessment is in
        draft status, updates the assessment status to 'submitted', generates a
        reference for it, sets the user who last updated it, and saves the updated
        assessment. Logs the actions performed. Redirects to the submission
        confirmation page if successful.

        If the assessment objectives are not completed, logs the unauthorized
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
        assessment = get_assessment(self.request)
        if assessment:
            return {"assessment_ref": assessment.reference}
        return {}
