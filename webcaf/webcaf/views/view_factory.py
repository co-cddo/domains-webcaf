import logging
import uuid
from typing import Any, Optional

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import FormView

from webcaf.webcaf.forms import ContinueForm
from webcaf.webcaf.views.session_utils import SessionUtil

logger = logging.getLogger(__name__)


def create_form_view(
    success_url_name: str,
    template_name: str = "section.html",
    form_class: Optional[type[forms.Form]] = None,
    class_prefix: str = "View",
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
    if form_class:
        class_attrs["form_class"] = form_class
    # Implement the custom view that handles the form submissions if defined in the
    # view registry.
    parent_classes = (
        LoginRequiredMixin,
        FormView,
    )

    def get_initial(self):
        """
        Get the initial data for the form.

        This method retrieves the initial data for the form by combining the base initial
        data from the parent class with specific assessment data, if available. It utilizes
        the `SessionUtil.get_current_assessment` method to retrieve the current assessment
        related to the request. If valid assessment data linked to the provided `class_id`
        is found, it updates the initial form data accordingly.

        :param self: Instance of the class calling the method.
        :return: A dictionary containing the initial data for the form.
        """
        initial = FormView.get_initial(self)
        if current_assessment := SessionUtil.get_current_assessment(self.request):
            initial.update(current_assessment.assessments_data.get(class_id, {}))
        return initial

    def get_context_data(self, **kwargs):
        data = FormView.get_context_data(self, **kwargs)
        return data

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
            assessment.assessments_data[class_id] = form.cleaned_data
            assessment.last_modified_by = current_user_profile.user
            assessment.save()
            self.logger.info(
                f"Form step {class_id} saved by user {current_user_profile.user.username}[{current_user_profile.role}] of {current_user_profile.organisation.name}"
            )
        return FormView.form_valid(self, form)

    def form_invalid(self, form):
        print(self.success_url, self.template_name)
        return FormView.form_invalid(self, form)

    class_attrs["form_valid"] = form_valid
    class_attrs["form_invalid"] = form_invalid
    class_attrs["get_context_data"] = get_context_data
    class_attrs["get_initial"] = get_initial
    FormViewClass = type(class_name, parent_classes, class_attrs)
    logger.info(f"Creating view class {class_name} with parent classes {parent_classes}")
    return FormViewClass
