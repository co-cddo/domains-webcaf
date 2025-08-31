from django.views.generic import TemplateView

from webcaf.webcaf.views.util import ConfigHelper


class ObjectiveConfirmationView(TemplateView):
    """
    Represents a view to handle the objective confirmation page.

    This view is responsible for rendering the template associated with the
    objective confirmation process. It provides the necessary context data,
    including the objectives fetched using an external helper class. The
    primary responsibility of this view is to render the template with all
    required data, ensuring seamless user interaction.

    :ivar template_name: Path to the template used to render the objective
        confirmation page.
    :type template_name: str
    """

    template_name = "assessment/objective-confirmation.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["objectives"] = ConfigHelper.get_objectives()
        return data
