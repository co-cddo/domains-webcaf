"""
NOTE:
    It is vital that this module is loaded before the view factory is started.
    This is done by including this in the __init__.py file
"""

from typing import cast

from django.views.generic import FormView

from webcaf.webcaf.views.view_registry import FormHandlingMixin


class ObjectiveViewAView(FormHandlingMixin):
    """
    Handle the form methods for the ObjectiveView_A view. Templating and routing are automatically
    handled by the view factory. Responsibility of this is view to handle the data submitted and gather
    the user input.
    """

    view_name = "ObjectiveView_A"

    def get_context_data(self):
        return cast(FormView, super()).get_context_data()

    def form_valid(self, form):
        return cast(FormView, super()).form_valid(form)

    def form_invalid(self, form):
        return cast(FormView, super()).form_invalid(form)
