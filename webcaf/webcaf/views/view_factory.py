import logging
import uuid
from textwrap import shorten
from typing import Any, Optional, Tuple, Type

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import FormView

from webcaf.webcaf.forms import ContinueForm
from webcaf.webcaf.views.session_utils import SessionUtil
from webcaf.webcaf.views.util import IndicatorStatusChecker


class FormViewWithBreadcrumbs(FormView):
    """
    Extension of the standard FormView class to include breadcrumb functionality.

    This class provides additional support for dynamically appending breadcrumb
    links to the context data for rendering in templates. It is particularly useful
    for enhancing user navigation in views where step-by-step progress or a hierarchy
    is represented.

    :ivar breadcrumbs: List of breadcrumb dictionaries specifying the navigation
        links for the view.
    :type breadcrumbs: list[dict]
    """

    def get_context_data(self, **kwargs: Any):
        context_data = FormView.get_context_data(self, **kwargs)
        context_data["breadcrumbs"] = context_data["breadcrumbs"] + self.build_breadcrumbs()
        return context_data

    def build_breadcrumbs(self):
        """
        Generate breadcrumb links for navigating to the draft assessment edit view.

        This method constructs a list of dictionaries where each dictionary represents
        a breadcrumb link with its display text and URL. It is primarily used for
        rendering navigation links in the user interface.

        :return: A list containing breadcrumb dictionaries. Each dictionary includes a
            'text' key for the display name of the breadcrumb and a 'url' key for the
            corresponding hyperlink.
        :rtype: list[dict[str, str]]
        """
        return [
            {
                "text": "Edit draft assessment",
                "url": reverse_lazy(
                    "edit-draft-assessment",
                    kwargs={"assessment_id": self.request.session["draft_assessment"]["assessment_id"]},
                ),
            }
        ]


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
        return super().build_breadcrumbs() + [
            {
                "text": f'Objective {objective_data_["code"]} - {objective_data_["title"]}',
                "url": reverse_lazy(f"objective_{objective_data_['code']}"),
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
                assessment.assessments_data[self.class_id][self.stage]
                and assessment.assessments_data[self.class_id][self.stage] != form.cleaned_data
            ):
                # Reset the confirmation data if the form data has changed
                assessment.assessments_data[self.class_id]["confirmation"] = {}
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
        # Remove the redundant override option from the choice list for confirmation
        data["form"].fields["confirm_outcome"].choices = [
            choice
            for choice in data["form"].fields["confirm_outcome"].choices
            if choice[1].lower() != f"Change to {data['outcome_status']['outcome_status']}".lower()
        ]
        return data

    def build_breadcrumbs(self):
        outcome = self.extra_context["outcome"]
        return super().build_breadcrumbs() + [
            {
                "text": f'Objective {outcome["code"]} - {outcome["title"]}',
                "url": reverse_lazy(f"indicators_{self.class_id}"),
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
        return reverse_lazy(f"objective_{self.extra_context['objective_code']}")


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
    elif class_prefix.startswith("ObjectiveView"):
        parent_classes = (
            LoginRequiredMixin,
            ObjectiveView,
        )
    else:
        parent_classes = (
            LoginRequiredMixin,
            FormViewWithBreadcrumbs,
        )

    FormViewClass = type(class_name, parent_classes, class_attrs)
    create_form_view_logger.info(f"Creating view class {class_name} with parent classes {parent_classes}")
    return FormViewClass
