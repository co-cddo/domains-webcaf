from typing import cast

from django.views.generic import FormView

from webcaf.webcaf.view_registry import FormHandlingMixin


class ObjectiveView_A_Controller(FormHandlingMixin):
    """
    Handle the form handling for the ObjectiveView_A view. Templating and routing are automatically
    handled by the view factory.
    """

    view_name = "ObjectiveView_A"

    def get_context_data(self):
        return cast(FormView, super()).get_context_data()

    def form_valid(self, form):
        return cast(FormView, super()).form_valid(form)

    def form_invalid(self, form):
        return cast(FormView, super()).form_invalid(form)
