import logging
import uuid
from textwrap import shorten
from typing import Any, Optional, Tuple, Type, Union

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import FormView

from webcaf.webcaf.forms import ContinueForm
from webcaf.webcaf.views.session_utils import SessionUtil
from webcaf.webcaf.views.util import IndicatorStatusChecker


class BaseIndicatorsFormView(FormView):
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

    def get_context_data(self, **kwargs):
        return FormView.get_context_data(self, **kwargs)

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
            assessment.assessments_data[self.class_id][self.stage] = form.cleaned_data
            assessment.last_modified_by = current_user_profile.user
            assessment.save()
            self.logger.info(
                f"Form step {self.class_id} -> [{self.stage}] saved by user {current_user_profile.user.username}[{current_user_profile.role}] of {current_user_profile.organisation.name}"
            )
        return FormView.form_valid(self, form)

    def form_invalid(self, form):
        return FormView.form_invalid(self, form)


class OutcomeIndicatorsView(BaseIndicatorsFormView):
    """
    Represents a view for outcome indicators.

    This class is likely used for displaying or interacting with outcome
    indicators in the system. It inherits from FormViewWithClassId, which
    might suggest that it includes functionality for handling forms and is
    tied to a specific ClassId.

    """

    def form_valid(self, form):
        return super().form_valid(form)

    def form_invalid(self, form):
        # Reset the form initial data to the cleaned data
        # This will update any feilds that the user has changed.
        form.initial.update(form.cleaned_data)
        friendly_errors = set()
        for error_field in form.errors.keys():
            friendly_errors.add("Need an input for : " + shorten(form.fields[error_field].label, 50, placeholder="..."))
        form.errors.clear()
        for message in friendly_errors:
            form.add_error(None, message)
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["back_url"] = f"objective_{data['objective_code']}"
        return data


class OutcomeConfirmationView(BaseIndicatorsFormView):
    """
    Handles the outcome confirmation view for a specific class.

    This class is responsible for rendering and managing the outcome
    confirmation view. It extends functionality from
    `FormViewWithClassId`.

    """

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        current_assessment = SessionUtil.get_current_assessment(self.request)
        data["outcome_status"] = IndicatorStatusChecker.get_status_for_indicator(
            current_assessment.assessments_data[self.class_id]
        )
        data["back_url"] = f"indicators_{self.class_id}"
        return data


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
    parent_classes: Tuple[
        Type[LoginRequiredMixin], Type[Union[OutcomeIndicatorsView, OutcomeConfirmationView, FormView]]
    ]
    if class_prefix.startswith("OutcomeIndicatorsView"):
        # Use the indicators view as a parent class.
        parent_classes = (
            LoginRequiredMixin,
            OutcomeIndicatorsView,
        )
    elif class_prefix.startswith("OutcomeConfirmationView"):
        # Use the confirmation view as a parent class.
        parent_classes = (
            LoginRequiredMixin,
            OutcomeConfirmationView,
        )
    else:
        parent_classes = (
            LoginRequiredMixin,
            FormView,
        )

    FormViewClass = type(class_name, parent_classes, class_attrs)
    create_form_view_logger.info(f"Creating view class {class_name} with parent classes {parent_classes}")
    return FormViewClass
