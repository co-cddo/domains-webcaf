from typing import cast

from django.views.generic import FormView, TemplateView


class Index(TemplateView):
    template_name = "index.html"


class ViewRegistry:
    """
    Registry for views.
    All views are registered here so that they can be accessed by name when
    the framework is instantiated.
    """

    __views: dict[str, type[FormView]] = {}

    @staticmethod
    def register(view):
        ViewRegistry.__views[view.view_name] = view

    @staticmethod
    def get_view(view_name):
        return ViewRegistry.__views.get(view_name)


class FormHandlingMixin:
    """
    Mixin for registered views that handle form submissions.
    Subclass must define a view_name attribute which is used to register the view for the appropriate handling.
    NOTE:
        Any subclass of this can override any FormView method.
    """

    view_name: str

    def __init_subclass__(cls, **kwargs):
        ViewRegistry().register(cls)


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
