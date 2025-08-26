import logging
import uuid
from typing import Any, Optional

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import FormView

from webcaf.webcaf.forms import ContinueForm

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

    def get_context_data(self, **kwargs):
        return FormView.get_context_data(self, **kwargs)

    def form_valid(self, form):
        print(self.success_url, self.template_name)
        return FormView.form_valid(self, form)

    def form_invalid(self, form):
        print(self.success_url, self.template_name)
        return FormView.form_invalid(self, form)

    class_attrs["form_valid"] = form_valid
    class_attrs["form_invalid"] = form_invalid
    class_attrs["get_context_data"] = get_context_data
    FormViewClass = type(class_name, parent_classes, class_attrs)
    logger.info(f"Creating view class {class_name} with parent classes {parent_classes}")
    return FormViewClass
