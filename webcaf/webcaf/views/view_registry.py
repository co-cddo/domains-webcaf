import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView


class ViewRegistry:
    """
    Registry for views.
    All views are registered here so that they can be accessed by name when
    the framework is instantiated.
    """

    __views: dict[str, type[FormView]] = {}
    logger = logging.getLogger("ViewRegistry")

    @staticmethod
    def register(view):
        ViewRegistry.__views[view.view_prefix] = view

    @classmethod
    def get_view(cls, view_name):
        for view_prefix, view in ViewRegistry.__views.items():
            if view_prefix in view_name:
                cls.logger.info(f"Found view {view_name} for prefix {view_prefix}")
                return view
        return None


class FormHandlingMixin(LoginRequiredMixin):
    """
    Mixin for registered views that handle form submissions.
    Subclass must define a view_name attribute which is used to register the view for the appropriate handling.
    NOTE:
        Any subclass of this can override any FormView method.
    """

    view_prefix: str

    def __init_subclass__(cls, **kwargs):
        if hasattr(cls, "view_prefix"):
            ViewRegistry().register(cls)
