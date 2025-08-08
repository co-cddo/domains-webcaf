"""
NOTE:
    It is vital that this module is loaded before the view factory is started.
    This is done by including this in the __init__.py file
"""

from abc import abstractmethod
from typing import cast

from django.views.generic import FormView

from webcaf.webcaf.models import Assessment, UserProfile
from webcaf.webcaf.views.view_registry import FormHandlingMixin


class OutcomeHandlerView(FormHandlingMixin):
    @abstractmethod
    def get_assessment_section(self):
        """
        Needs to implement this method to return the section of the assessment
        """

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        assessment = self.get_assessment()
        assessment_section = self.get_assessment_section()
        kwargs["initial"] = assessment.assessments_data.get(assessment_section, {})
        return kwargs

    def form_valid(self, form):
        assessment = self.get_assessment()
        assessment.assessments_data[self.get_assessment_section()] = form.cleaned_data
        assessment.save()
        return cast(FormView, super()).form_valid(form)

    def get_assessment(self):
        id_ = self.request.session["draft_assessment"]["assessment_id"]
        user_profile_id = self.request.session["current_profile_id"]
        user_profile = UserProfile.objects.get(id=user_profile_id)
        assessment = Assessment.objects.get(
            status="draft", id=id_, system__organisation_id=user_profile.organisation.id
        )
        return assessment

    def form_invalid(self, form):
        return cast(FormView, super()).form_invalid(form)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        # Class id comes from the base framework that generates this view
        data["section_id"] = self.class_id
        return data


class OutcomeIndicatorsHandlerView(OutcomeHandlerView):
    """ """

    view_prefix = "OutcomeIndicatorsView_"

    def get_assessment_section(self):
        return type(self).__name__

    def form_valid(self, form):
        assessment = self.get_assessment()
        needs_confirmation_reset = (
            assessment.assessments_data.get(self.get_assessment_section(), {}) != form.cleaned_data
        )
        assessment.assessments_data[self.get_assessment_section()] = form.cleaned_data
        if needs_confirmation_reset:
            # OutcomeConfirmationView_A1.a
            # Wipe out the confirmation section as the data may have changed
            assessment.assessments_data[self.get_assessment_section().replace("Indicators", "Confirmation")] = {}
        assessment.save()
        return cast(FormView, super()).form_valid(form)


class OutcomeConfirmationHandlerView(OutcomeHandlerView):
    """ """

    view_prefix = "OutcomeConfirmationView_"

    def get_assessment_section(self):
        return type(self).__name__

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        assessment = self.get_assessment()
        assessment_section = self.get_assessment_section()
        outcome_status = self.calculate_outcome_status()
        kwargs["initial"] = assessment.assessments_data.get(assessment_section, {})
        kwargs["outcome_status"] = outcome_status
        return kwargs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        outcome_status = self.calculate_outcome_status()
        data["outcome_status"] = outcome_status
        return data

    def calculate_outcome_status(self):
        assessment = self.get_assessment()
        indicators = assessment.assessments_data[self.get_assessment_section().replace("Confirmation", "Indicators")]
        return (
            "not achieved"
            if False in set(map(lambda x: x[1], filter(lambda x: x[0].startswith("achieved"), indicators.items())))
            else "achieved"
        ).title()
