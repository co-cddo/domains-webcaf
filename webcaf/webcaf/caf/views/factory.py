import logging
import uuid
from collections import defaultdict
from typing import Any, Optional, Tuple, Type

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import CharField, Form
from django.http import HttpResponseNotFound
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.safestring import mark_safe
from django.views.generic import FormView

from webcaf.webcaf.caf.util import IndicatorStatusChecker
from webcaf.webcaf.forms.general import ContinueForm, NextActionForm
from webcaf.webcaf.utils.caf import CafFormUtil
from webcaf.webcaf.utils.session import SessionUtil
from webcaf.webcaf.views.general import FormViewWithBreadcrumbs


class NextObjectiveForm(NextActionForm):
    """
    Decides whether to go to the next objective or to the main page.
    """

    next_objective = CharField()


class ObjectiveView(FormViewWithBreadcrumbs):
    """
    Representation of a view with breadcrumbs for an objective.

    This class extends functionality to provide breadcrumb navigation
    specific to objectives. It integrates additional context data from
    objective-related information to enhance breadcrumb display.

    """

    def build_breadcrumbs(self):
        objective_data_ = self.extra_context["objective_data"]
        return super().build_breadcrumbs() + [
            {
                "text": f'Objective {objective_data_["code"]} - {objective_data_["title"]}',
            }
        ]

    def form_valid(self, form):
        # Redirect to the appropriate destination
        assessment = SessionUtil.get_current_assessment(self.request)
        if form.cleaned_data["action"] == "confirm":
            return redirect(reverse(f"{assessment.framework}_objective_{form.cleaned_data['next_objective']}"))
        return redirect(reverse("edit-draft-assessment", kwargs={"assessment_id": assessment.id}))

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        assessment = SessionUtil.get_current_assessment(self.request)
        data["progress"] = True
        data["assessment"] = assessment
        return data


class BaseIndicatorsFormView(FormViewWithBreadcrumbs):
    """
    BaseIndicatorsFormView class inherits from FormView and provides functionality
    to manage form data for specific class-related assessments with proper handling of initial
    data, context, and form validation. It integrates assessment data retrieval and saving
    mechanisms, provides the base functionality for saving form data under the correct context.

    :ivar class_id: Identifier of the class related to the assessment.
    :type class_id: str
    :ivar stage: Stage of the assessment.
    :type stage: str
    :ivar logger: Logger instance for logging activities associated with the form view.
    :type logger: logging.Logger
    """

    class_id: str
    stage: str
    logger: logging.Logger

    def get_initial(self):
        """
        Get the initial data for the form.

        This method retrieves the initial data for the form by combining the base initial
        data from the parent class with specific assessment data, if available. It utilizes
        the `SessionUtil.get_current_assessment` method to retrieve the current assessment
        related to the request. If valid assessment data linked to the provided `unique_queue_id`
        is found, it updates the initial form data accordingly.

        :param self: Instance of the class calling the method.
        :return: A dictionary containing the initial data for the form.
        """
        initial = super().get_initial()
        if current_assessment := SessionUtil.get_current_assessment(self.request):
            initial.update(self._get_init_data(current_assessment))
        return initial

    def _get_init_data(self, current_assessment):
        return current_assessment.assessments_data.get(self.class_id, {}).get(self.stage, {})

    def build_breadcrumbs(self):
        """
        Builds breadcrumbs with additional information regarding objectives.

        This method extends the breadcrumbs created by the superclass by including
        an extra breadcrumb entry that contains details about a specific objective.
        The objective details are accessed from the extra context dictionary provided
        by the class.

        :return: A list of breadcrumb dictionaries including the additional
            objective-specific breadcrumb entry.
        :rtype: list
        """
        objective_data_ = self.extra_context["objective_data"]
        assessment = SessionUtil.get_current_assessment(self.request)
        return super().build_breadcrumbs() + [
            {
                "text": f'Objective {objective_data_["code"]} - {objective_data_["title"]}',
                "url": reverse_lazy(f"{assessment.framework}_objective_{objective_data_['code']}"),
            }
        ]

    def form_valid(self, form):
        """
        Validates the form data and updates the current assessment's data.

        This method is responsible for handling the logic when the form is validated
        successfully. It retrieves the current assessment, updates the assessment's
        data using the cleaned data from the form, saves the updated assessment,
        and proceeds with the default behavior of the parent class.

        :param self: Reference to the current class instance.
        :param form: The submitted form instance containing cleaned data after
            validation.
        :return: The HTTP response returned by the parent class's form_valid method.
        """
        assessment = SessionUtil.get_current_assessment(self.request)
        if assessment:
            current_user_profile = SessionUtil.get_current_user_profile(self.request)
            if self.class_id not in assessment.assessments_data:
                assessment.assessments_data[self.class_id] = {}
            if self.stage not in assessment.assessments_data[self.class_id]:
                assessment.assessments_data[self.class_id][self.stage] = {}

            if (
                self.stage == "indicators"
                and assessment.assessments_data[self.class_id][self.stage] != form.cleaned_data
            ):
                # If we are changing the indicators, then we have to reset the confirmation data
                if "confirmation" in assessment.assessments_data[self.class_id]:
                    current_outcome_status = assessment.assessments_data[self.class_id]["confirmation"].get(
                        "outcome_status", ""
                    )
                    assessment.assessments_data[self.class_id]["confirmation"] = {
                        k: v
                        for k, v in assessment.assessments_data[self.class_id]["confirmation"].items()
                        # This is the comment associated with the confirmation
                        if k
                        in [
                            "confirm_outcome_confirm_comment",
                        ]
                    }
                    self.logger.info(
                        f"Updated assessment data for class {self.class_id} as the answers have changed status is {current_outcome_status}."
                    )
            assessment.assessments_data[self.class_id][self.stage] = form.cleaned_data
            assessment.last_updated_by = current_user_profile.user
            assessment.save()
            self.logger.info(
                f"Updating section {self.class_id} -> [{self.stage}] saved by user {current_user_profile.user.username}[{current_user_profile.role}] of {current_user_profile.organisation.name}"
            )
        else:
            return HttpResponseNotFound("Requested assessment could not be found.")

        return FormView.form_valid(self, form)

    def form_invalid(self, form):
        return FormView.form_invalid(self, form)

    def _build_duplicate_field_suffix(self, form: Form, other_field_names: list[str]):
        """
        Summary: Builds a suffix for duplicate fields based on form and other field names.

        :param form: The current form object.
        :param other_field_names: List of field names to be used as references.
        :return: A string with the duplicate field suffix, marked as safe for HTML rendering.
        """
        return mark_safe(
            f"""identical to {" and ".join(f"{'-'.join([part.lower() for part in CafFormUtil.get_category_name(field).split()])} statement {CafFormUtil.human_index(form, field)}" for field in other_field_names)}"""
        )


class OutcomeIndicatorsView(BaseIndicatorsFormView):
    """
    Represents a view for outcome indicators.

    This class is likely used for displaying or interacting with outcome
    indicators in the system. It inherits from FormViewWithClassId, which
    might suggest that it includes functionality for handling forms and is
    tied to a specific ClassId.

    """

    def get_form(self, form_class: Optional[type[forms.Form]] = None):
        """
        Returns a modified form instance. Finds fields with duplicate labels in the
        provided form class and adjusts their label suffix to ensure differentiation.
        This method processes all fields except those with names ending in "_comment".

        :param form_class: The form class to generate the form instance from. Defaults
            to `None`.
        :type form_class: Optional[type[forms.Form]]
        :return: The modified form instance with adjusted label suffixes for fields
            with duplicate labels.
        :rtype: forms.Form
        """
        duplicate_form_data = defaultdict(list)
        form = super().get_form(form_class)
        for field_name, field in form.fields.items():
            if not field_name.endswith("_comment"):
                duplicate_form_data[field.label].append((field, field_name))
        for label, fields in duplicate_form_data.items():
            if len(fields) > 1:
                for field in fields:
                    field[0].label_suffix = self._build_duplicate_field_suffix(
                        form, [other_field[1] for other_field in fields if other_field[1] != field[1]]
                    )
        return form

    def build_breadcrumbs(self):
        """
        Build breadcrumbs for the context with appended outcome details.

        This method extends the base breadcrumbs by adding an entry that includes
        the objective code and title extracted from the `outcome` data in
        `extra_context`. The additional entry provides specific details related to
        the context being processed.

        :raise KeyError: If ``outcome`` key is missing from the ``extra_context`` dictionary
        :raise TypeError: If the ``extra_context`` is not subscriptable or unexpected
        :type context data
        :return: List of breadcrumb entries with appended objective details.
        :rtype: list[dict]
        """
        outcome = self.extra_context["outcome"]
        return super().build_breadcrumbs() + [
            {
                "text": f'Objective {outcome["code"]} - {outcome["title"]}',
            }
        ]

    def form_invalid(self, form):
        # Reset the form initial data to the cleaned data
        # This will update any feilds that the user has changed.
        form.initial.update(form.cleaned_data)
        friendly_errors = set()
        for error_field, errors in form.errors.items():
            # validation on word count breaks the below so skip that and keep entered text
            if "_comment" in error_field:
                error_message = "Word count limit exceeded in justifcation of answer for "
            else:
                error_message = "Need an answer for "

            friendly_errors.add(
                ValidationError(
                    {
                        error_field: f"{error_message}"
                        f"{CafFormUtil.get_category_name(error_field)} question "
                        f"{CafFormUtil.human_index(form, error_field)}"
                    }
                )
            )

        form.errors.clear()
        for message in friendly_errors:
            form.add_error(None, message)
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        assessment = SessionUtil.get_current_assessment(self.request)
        data["back_url"] = f"{assessment.framework}_objective_{data['objective_code']}"
        data["progress"] = True
        data["assessment"] = assessment
        return data

    @transaction.atomic
    def form_valid(self, form):
        """
        Summary:
        Validates the form and updates the assessment data accordingly.
        Allow the data to be persisted using the parent class method.
        Then reset the confirmation data if the form data has changed.

        :param form: The form to be validated.
        :return: The result of calling super().form_valid(form).
        """

        def if_any_selected():
            for field_name, value in form.cleaned_data.items():
                if not field_name.endswith("_comment") and value:
                    return True
            return False

        if not if_any_selected():
            form.add_error(None, ValidationError("You need to select at least one statement to answer"))
            return super().form_invalid(form)
        return super().form_valid(form)


class OutcomeConfirmationView(BaseIndicatorsFormView):
    """
    Handles the outcome confirmation view for a specific class.

    This class is responsible for rendering and managing the outcome
    confirmation view. It extends functionality from
    `FormViewWithClassId`.

    """

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        assessment = SessionUtil.get_current_assessment(self.request)
        data["outcome_status"] = IndicatorStatusChecker.get_status_for_indicator(
            assessment.assessments_data[self.class_id]
        )
        data["back_url"] = f"{assessment.framework}_indicators_{self.class_id}"
        # Remove the redundant override option from the choice list for confirmation
        data["form"].fields["confirm_outcome"].choices = [
            choice
            for choice in data["form"].fields["confirm_outcome"].choices
            if choice[1].lower() != f"Change to {data['outcome_status']['outcome_status']}".lower()
        ]
        data["progress"] = True
        data["assessment"] = assessment
        return data

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        outcome = cleaned_data["confirm_outcome"]
        assessment = SessionUtil.get_current_assessment(self.request)

        if not outcome.startswith("back_to_achieved"):
            #     Validate if the user has provided justification text for changing the outcome
            #     Find out what it was changed to
            comment_for_the_change = cleaned_data.get(f"confirm_outcome_{outcome}_comment")
            if not comment_for_the_change:
                form.initial.update(form.cleaned_data)
                form.add_error(f"confirm_outcome_{outcome}_comment", ValidationError("You must provide a summary."))
            # We directly call super as we don't want to call form_invalid here.'This is because
            # form_invalid will us purly to capture non selected questions and we cannot have
            # optional logic to handle this.
        else:
            return redirect(reverse_lazy(f"{assessment.framework}_indicators_{self.class_id}"))

        if form.errors:
            return super().form_invalid(form)

        status_for_indicator = IndicatorStatusChecker.get_status_for_indicator(
            assessment.assessments_data[self.class_id]
        )
        form.cleaned_data.update(**status_for_indicator)
        self.logger.info(f"Saving outcome confirmation {self.class_id} form {self.request.user.username}")
        return super().form_valid(form)

    def build_breadcrumbs(self):
        outcome = self.extra_context["outcome"]
        assessment = SessionUtil.get_current_assessment(self.request)
        return super().build_breadcrumbs() + [
            {
                "text": f'Objective {outcome["code"]} - {outcome["title"]}',
                "url": reverse_lazy(f"{assessment.framework}_indicators_{self.class_id}"),
            },
            {
                "text": f'Objective {outcome["code"]} - {outcome["title"]} outcome',
            },
        ]

    def get_success_url(self):
        """
        Generates and returns a URL pointing to a success page based on the given
        objective code present in the extra context of the instance.

        :raises KeyError: If 'objective_code' is not found in `extra_context`.
        :return: A lazily reversed URL string built using the objective code.
        :rtype: str
        """
        assessment = SessionUtil.get_current_assessment(self.request)
        return reverse_lazy(f"{assessment.framework}_objective_{self.extra_context['objective_code']}")

    def form_invalid(self, form):
        form.initial.update(form.cleaned_data)
        return super().form_invalid(form)


create_form_view_logger = logging.getLogger("create_form_view")


def create_form_view(
    success_url_name: str,
    template_name: str = "section.html",
    form_class: Optional[type[forms.Form]] = None,
    class_prefix: str = "View",
    stage: Optional[str] = None,
    class_id: Optional[str] = None,
    extra_context: Optional[dict[str, Any]] = None,
) -> type[FormView]:
    """
    Creates a new subclass of FormView. Each view in the automated part
    of the assessment flow has a separate view class, generated here.

    These views do not do a lot of work. Most of the page structure
    is defined in the form class.
    """
    class_id = class_id or uuid.uuid4().hex
    class_name = f"{class_prefix}_{class_id}"

    class_attrs = {
        "template_name": template_name,
        "success_url": reverse_lazy(success_url_name),
        "extra_context": extra_context,
        "logger": logging.getLogger(class_name),
    }

    class_attrs["form_class"] = form_class if form_class else ContinueForm
    class_attrs["class_id"] = class_id
    class_attrs["stage"] = stage

    # Implement the custom view that handles the form submissions if defined in the
    # view registry.
    parent_classes: Tuple[Type[LoginRequiredMixin], Type[FormViewWithBreadcrumbs]]
    if "OutcomeIndicatorsView" in class_prefix:
        parent_classes = (
            LoginRequiredMixin,
            OutcomeIndicatorsView,
        )
    elif "OutcomeConfirmationView" in class_prefix:
        parent_classes = (
            LoginRequiredMixin,
            OutcomeConfirmationView,
        )
    elif "ObjectiveView" in class_prefix:
        parent_classes = (
            LoginRequiredMixin,
            ObjectiveView,
        )
        # Use custom form class for the Objective
        # By default we get continue form which is not needed
        class_attrs["form_class"] = NextObjectiveForm
    else:
        parent_classes = (
            LoginRequiredMixin,
            FormViewWithBreadcrumbs,
        )

    FormViewClass = type(class_name, parent_classes, class_attrs)
    create_form_view_logger.info(f"Creating view class {class_name} with parent classes {parent_classes}")
    return FormViewClass
