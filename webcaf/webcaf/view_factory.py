import uuid
from typing import Any, Optional

from django import forms
from django.urls import reverse_lazy
from django.views.generic import FormView

from .forms import ContinueForm


def create_form_view(
    success_url_name: str,
    template_name: str = "section.html",
    form_class: Optional[type[forms.Form]] = None,
    class_prefix: str = "View",
    class_id: Optional[str] = None,
    extra_context: Optional[dict[str, Any]] = None,
) -> type[FormView]:
    class_id = class_id or uuid.uuid4().hex
    class_name = f"{class_prefix}_{class_id}"

    class_attrs = {
        "template_name": template_name,
        "success_url": reverse_lazy(success_url_name),
        "extra_context": extra_context,
    }
    class_attrs["form_class"] = form_class if form_class else ContinueForm
    if form_class:
        class_attrs["form_class"] = form_class
    FormViewClass = type(class_name, (FormView,), class_attrs)
    return FormViewClass
