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


class OutcomeHandlerView(LoginRequiredMixin, FormView):
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
        from webcaf import settings

        data = super().get_context_data(**kwargs)
        indicator_id = self.kwargs["indicator_id"]
        outcome_id = indicator_id.replace("indicators_", "")
        objective_id = outcome_id[0]
        principle_id = outcome_id.split(".")[0]
        indicators_stage = settings.framework_router.framework["objectives"][objective_id]["principles"][principle_id][
            "outcomes"
        ][outcome_id]
        data["objective"] = settings.framework_router.framework["objectives"][objective_id]
        data["principle"] = settings.framework_router.framework["objectives"][objective_id]["principles"][principle_id]
        data["outcome"] = indicators_stage
        data["achieved"] = indicators_stage["indicators"]["achieved"]
        data["not_achieved"] = indicators_stage["indicators"]["not-achieved"]
        data["partially_achieved"] = indicators_stage["indicators"]["partially-achieved"]
        assessment_id = self.request.session["draft_assessment"]["assessment_id"]
        data["breadcrumbs"] = [
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
                "text": f"Objective {data['objective']['code']} -  {data['objective']['title']}",
            },
            {"text": f"Objective {indicators_stage['code']} -  {indicators_stage['title']}"},
        ]
        return data


class OutcomeIndicatorsHandlerView(OutcomeHandlerView):
    """ """

    template_name = "assessment/indicator-overview.html"

    def get_form_class(self) -> type[BaseForm]:
        from webcaf import settings

        indicator_id = self.kwargs["indicator_id"]
        outcome_id = indicator_id.replace("indicators_", "")
        objective_id = outcome_id[0]
        principle_id = outcome_id.split(".")[0]
        indicators_stage = settings.framework_router.framework["objectives"][objective_id]["principles"][principle_id][
            "outcomes"
        ][outcome_id]

        provider: FieldProvider = OutcomeIndicatorsFieldProvider(indicators_stage)
        form = create_form(provider)
        return form

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

        if current_index > len(siblings) - 1:
            # Go to next section
            pass
        else:
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
        for initial_data in initial_data.items():
            setattr(data["form"].fields[initial_data[0]], "initial", initial_data[1])
        return data

    def get_assessment_section(self):
        return "indicator_" + self.kwargs["indicator_id"]

    def form_valid(self, form):
        assessment = self.get_assessment()
        needs_confirmation_reset = (
            assessment.assessments_data.get(self.get_assessment_section(), {}) != form.cleaned_data
        )
        assessment.assessments_data[self.get_assessment_section()] = form.cleaned_data
        if needs_confirmation_reset:
            # OutcomeConfirmationView_A1.a
            # Wipe out the confirmation section as the data may have changed
            assessment.assessments_data[self.get_assessment_section().replace("indicator_", "confirmation_")] = {}
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


class OutcomeConfirmationHandlerView(FormView):
    """ """

    view_prefix = "OutcomeConfirmationView_"
    template_name = "assessment/indicator-confirmation.html"
    form_class = OutcomeConfirmationForm

    def get_assessment_section(self):
        return "confirmation_" + self.kwargs["indicator_id"]

    def get_assessment(self):
        id_ = self.request.session["draft_assessment"]["assessment_id"]
        user_profile_id = self.request.session["current_profile_id"]
        user_profile = UserProfile.objects.get(id=user_profile_id)
        assessment = Assessment.objects.get(
            status="draft", id=id_, system__organisation_id=user_profile.organisation.id
        )
        return assessment

    def form_valid(self, form):
        assessment = self.get_assessment()
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
                assessment_id = self.request.session["draft_assessment"]["assessment_id"]
                return reverse("edit-draft-assessment", kwargs={"version": "v3.2", "assessment_id": assessment_id})
            else:
                next_parent = parent_siblings[current_parent_index + 1]
                siblings = [
                    entry[0]
                    for entry in settings.framework_router.parent_map.items()
                    if entry[1]["parent"] == next_parent and entry[0].startswith("indicators")
                ]
                return reverse("indicator-view", kwargs={"version": "v3.2", "indicator_id": siblings[0]})

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
        outcome_status = self.calculate_outcome_status()
        data["outcome_status"] = outcome_status
        data["outcome_status_text"] = self.outcome_status_to_text(outcome_status)
        indicator_id = self.kwargs["indicator_id"]
        outcome_id = indicator_id.replace("indicators_", "")
        objective_id = outcome_id[0]
        principle_id = outcome_id.split(".")[0]
        indicators_stage = settings.framework_router.framework["objectives"][objective_id]["principles"][principle_id][
            "outcomes"
        ][outcome_id]
        data["objective"] = settings.framework_router.framework["objectives"][objective_id]
        data["principle"] = settings.framework_router.framework["objectives"][objective_id]["principles"][principle_id]
        data["outcome"] = indicators_stage
        data["indicator_id"] = indicator_id
        data["achieved"] = indicators_stage["indicators"]["achieved"]
        assessment_id = self.request.session["draft_assessment"]["assessment_id"]
        data["breadcrumbs"] = [
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
                "text": f"Objective {data['objective']['code']} -  {data['objective']['title']}",
            },
            {"text": f"Objective {indicators_stage['code']} -  {indicators_stage['title']} outcome"},
        ]
        return data

    def calculate_outcome_status(self):
        assessment = self.get_assessment()
        indicators = assessment.assessments_data[self.get_assessment_section().replace("confirmation_", "indicator_")]
        achieved_responses = set(
            map(
                lambda x: x[1],
                filter(lambda x: not x[0].endswith("_comment") and x[0].startswith("achieved_"), indicators.items()),
            )
        )
        return (
            "not achieved" if len(achieved_responses) != 1 or "agreed" not in achieved_responses else "achieved"
        ).capitalize()

    def outcome_status_to_text(self, outcome_status):
        return {
            "Achieved": "Achieved",
            "Not achieved": """You selected 'not true' to at least one of the achieved or partially achieved statements.
Please confirm you agree with this status, or you can choose to change the outcome.""",
        }[outcome_status]
