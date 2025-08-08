from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class ObjectiveView(LoginRequiredMixin, TemplateView):
    template_name = "assessment/objective-overview.html"
    login_url = "/oidc/authenticate/"

    def get_context_data(self, **kwargs):
        from webcaf.webcaf.caf32_router import FrameworkRouter

        data = super().get_context_data(**kwargs)
        parent_map: dict[str, Any] = FrameworkRouter.parent_map
        data["breadcrumbs"] = [{"url": "#", "text": "Objective overview"}]
        data["objective_heading"] = (
            kwargs["objective_id"].replace("_", " ").title() + " - " + parent_map[kwargs["objective_id"]]["text"]
        )
        data["principles"] = []
        # Build the list of principles based on the parent map. This will be used to display in the table with
        # the links to the indicators.
        for principle in list(filter(lambda x: x[1]["parent"] == kwargs["objective_id"], parent_map.items())):
            data["principles"].append(
                {
                    "name": principle[0].replace("_", ":").title() + " " + principle[1]["text"],
                    "indicators": [
                        {"url": x[0], "title": x[0].replace("indicators_", "") + " " + x[1]["text"]}
                        for x in list(
                            filter(
                                lambda x: x[1]["parent"] == principle[0] and x[0].startswith("indicators"),
                                parent_map.items(),
                            )
                        )
                    ],
                }
            )
        return data
