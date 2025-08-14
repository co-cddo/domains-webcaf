"""
NOTE:
    It is vital that this module is loaded before the view factory is started.
    This is done by including this in the __init__.py file
"""
from abc import abstractmethod
from textwrap import shorten
from typing import cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import CharField, ChoiceField
from django.forms.forms import BaseForm, Form
from django.urls import reverse
from django.views.generic import FormView

from webcaf.webcaf.caf_loader.caf32_field_providers import (
    FieldProvider,
    OutcomeIndicatorsFieldProvider,
)
from webcaf.webcaf.form_factory import create_form
from webcaf.webcaf.models import Assessment, UserProfile
from webcaf.webcaf.views.status_calculator import (
    calculate_outcome_status,
    outcome_status_to_text,
)


class BaseAssessmentMixin:
    """Mixin to eliminate code duplication across assessment views."""

    def get_assessment(self):
        """Retrieve assessment with shared logic."""
        id_ = self.request.session["draft_assessment"]["assessment_id"]
        user_profile_id = self.request.session["current_profile_id"]
        user_profile = UserProfile.objects.get(id=user_profile_id)
        assessment = Assessment.objects.get(
            status="draft", id=id_, system__organisation_id=user_profile.organisation.id
        )
        return assessment

    def _extract_framework_ids(self, indicator_id):
        """Extract framework IDs from indicator_id."""
        outcome_id = indicator_id.replace("indicators_", "")
        objective_id = outcome_id[0]
        principle_id = outcome_id.split(".")[0]
        return outcome_id, objective_id, principle_id

    def _get_framework_stage(self, indicator_id):
        """Get framework stage data."""
        from webcaf import settings

        outcome_id, objective_id, principle_id = self._extract_framework_ids(indicator_id)
        return settings.framework_router.framework["objectives"][objective_id]["principles"][principle_id]["outcomes"][
            outcome_id
        ]

    def _build_breadcrumbs(self, indicator_id, objective_data, outcome_data):
        """Build breadcrumb navigation."""
        assessment_id = self.request.session["draft_assessment"]["assessment_id"]
        _, objective_id, _ = self._extract_framework_ids(indicator_id)

        return [
            {
                "url": reverse("my-account", kwargs={}),
                "text": "Home",
            },
            {
                "url": reverse("edit-draft-assessment", kwargs={"version": "v3.2", "assessment_id": assessment_id}),
                "text": "Edit draft assessment",
            },
            {
                "url": reverse(
                    "objective-overview", kwargs={"version": "v3.2", "objective_id": f"objective_{objective_id}"}
                ),
                "text": f"Objective {objective_data['code']} -  {objective_data['title']}",
            },
            {"text": f"Objective {outcome_data['code']} -  {outcome_data['title']}"},
        ]


class OutcomeHandlerView(LoginRequiredMixin, FormView, BaseAssessmentMixin):
    @abstractmethod
    def get_assessment_section(self):
        """
        Needs to implement this method to return the section of the assessment
        """

    def form_valid(self, form):
        assessment = self.get_assessment()
        assessment.assessments_data[self.get_assessment_section()] = form.cleaned_data
        assessment.save()
        return cast(FormView, super()).form_valid(form)

    def form_invalid(self, form):
        return cast(FormView, super()).form_invalid(form)

    def get_context_data(self, **kwargs):
        from webcaf import settings

        data = super().get_context_data(**kwargs)
        indicator_id = self.kwargs["indicator_id"]
        outcome_id, objective_id, principle_id = self._extract_framework_ids(indicator_id)
        indicators_stage = self._get_framework_stage(indicator_id)

        objective_data = settings.framework_router.framework["objectives"][objective_id]
        principle_data = objective_data["principles"][principle_id]

        data.update(
            {
                "objective": objective_data,
                "principle": principle_data,
                "outcome": indicators_stage,
                "achieved": indicators_stage["indicators"]["achieved"],
                "not_achieved": indicators_stage["indicators"]["not-achieved"],
                "partially_achieved": indicators_stage["indicators"]["partially-achieved"],
                "breadcrumbs": self._build_breadcrumbs(indicator_id, objective_data, indicators_stage),
            }
        )
        return data


class OutcomeIndicatorsHandlerView(OutcomeHandlerView):
    """Handler for outcome indicators forms."""

    template_name = "assessment/indicator-overview.html"

    def get_form_class(self) -> type[BaseForm]:
        indicator_id = self.kwargs["indicator_id"]
        indicators_stage = self._get_framework_stage(indicator_id)
        provider: FieldProvider = OutcomeIndicatorsFieldProvider(indicators_stage)
        form = create_form(provider)
        return form

    def get_success_url(self):
        indicator_id = self.kwargs["indicator_id"]
        return reverse("indicator-confirmation-view", kwargs={"version": "v3.2", "indicator_id": indicator_id})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Load the initial data from the assessment
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        assessment = self.get_assessment()
        assessment_section = self.get_assessment_section()
        initial.update(assessment.assessments_data.get(assessment_section, {}))
        return initial

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        initial_data = data["form"].cleaned_data if hasattr(data["form"], "cleaned_data") else data["form"].initial
        for field_name, initial_value in initial_data.items():
            if field_name in data["form"].fields:
                data["form"].fields[field_name].initial = initial_value
        return data

    def get_assessment_section(self):
        return "indicator_" + self.kwargs["indicator_id"]

    def form_valid(self, form):
        assessment = self.get_assessment()
        current_section = self.get_assessment_section()
        needs_confirmation_reset = assessment.assessments_data.get(current_section, {}) != form.cleaned_data
        assessment.assessments_data[current_section] = form.cleaned_data
        if needs_confirmation_reset:
            # OutcomeConfirmationView_A1.a
            # Wipe out the confirmation section as the data may have changed
            assessment.assessments_data[current_section.replace("indicator_", "confirmation_")] = {}
        assessment.save()
        return cast(FormView, super()).form_valid(form)

    def form_invalid(self, form):
        friendly_errors = set()
        for error_field in form.errors.keys():
            friendly_errors.add("Need an input for : " + shorten(form.fields[error_field].label, 50, placeholder="..."))
        form.errors.clear()
        for message in friendly_errors:
            form.add_error(None, message)
        return cast(FormView, super()).form_invalid(form)


class OutcomeConfirmationForm(Form):
    confirm_outcome = ChoiceField(
        choices=[
            ("confirm", "Confirm"),
            ("change_to_achieved", "Change to Achieved"),
            ("change_to_not_achieved", "Change to Not achieved"),
            ("change_to_partially_achieved", "Change to Partially Achieved"),
        ],
        required=True,
        initial="confirm",
    )
    change_to_achieved_detail = CharField(required=False)
    change_to_not_achieved_detail = CharField(required=False)
    change_to_partially_achieved_detail = CharField(required=False)
    summary_outline = CharField(required=True)


class OutcomeConfirmationHandlerView(LoginRequiredMixin, FormView, BaseAssessmentMixin):
    """Handler for outcome confirmation forms."""

    view_prefix = "OutcomeConfirmationView_"
    template_name = "assessment/indicator-confirmation.html"
    form_class = OutcomeConfirmationForm

    def get_assessment_section(self):
        return "confirmation_" + self.kwargs["indicator_id"]

    def form_valid(self, form):
        assessment = self.get_assessment()
        # Add the outcome status to the assessment data
        assessment.assessments_data[self.get_assessment_section()] = form.cleaned_data
        assessment.save()
        return cast(FormView, super()).form_valid(form)

    def get_success_url(self):
        from webcaf import settings

        indicator_id = self.kwargs["indicator_id"]
        parent = settings.framework_router.parent_map[indicator_id]["parent"]
        siblings = [
            entry[0]
            for entry in settings.framework_router.parent_map.items()
            if entry[1]["parent"] == parent and entry[0].startswith("indicators")
        ]
        current_index = siblings.index(indicator_id)

        if current_index > len(siblings) - 2:
            # Get the next parent indicator and go to next section
            parent_siblings = [
                entry[0] for entry in settings.framework_router.parent_map.items() if entry[0].startswith("principle")
            ]
            current_parent_index = parent_siblings.index(parent)
            if current_parent_index > len(parent_siblings) - 2:
                # Flow is complete, go back to the overview page
                assessment_id = self.request.session["draft_assessment"]["assessment_id"]
                return reverse("edit-draft-assessment", kwargs={"version": "v3.2", "assessment_id": assessment_id})
            else:
                outcome_id = indicator_id.replace("indicators_", "")
                objective_id = outcome_id[0]
                return reverse(
                    "objective-overview", kwargs={"version": "v3.2", "objective_id": f"objective_{objective_id}"}
                )
        else:
            return reverse("indicator-view", kwargs={"version": "v3.2", "indicator_id": siblings[current_index + 1]})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        assessment = self.get_assessment()
        assessment_section = self.get_assessment_section()
        kwargs["initial"] = assessment.assessments_data.get(assessment_section, {})
        return kwargs

    def get_context_data(self, **kwargs):
        from webcaf import settings

        data = super().get_context_data(**kwargs)
        assessment = self.get_assessment()
        confirmation = assessment.assessments_data.get(self.get_assessment_section(), {})
        indicators = assessment.assessments_data[self.get_assessment_section().replace("confirmation_", "indicator_")]
        outcome_status = calculate_outcome_status(confirmation, indicators)
        indicator_id = self.kwargs["indicator_id"]
        indicators_stage = self._get_framework_stage(indicator_id)
        outcome_id, objective_id, principle_id = self._extract_framework_ids(indicator_id)

        objective_data = settings.framework_router.framework["objectives"][objective_id]
        principle_data = objective_data["principles"][principle_id]

        data.update(
            {
                "outcome_status": outcome_status,
                "outcome_status_text": outcome_status_to_text(outcome_status["outcome_status"]),
                "indicator_id": indicator_id,
                "objective": objective_data,
                "principle": principle_data,
                "outcome": indicators_stage,
                "achieved": indicators_stage["indicators"]["achieved"],
                "breadcrumbs": self._build_breadcrumbs(indicator_id, objective_data, indicators_stage)
                + [{"text": f"Objective {indicators_stage['code']} -  {indicators_stage['title']} outcome"}],
            }
        )
        return data
