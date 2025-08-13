from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import TemplateView

from webcaf.webcaf.models import Assessment, UserProfile


class ObjectiveView(LoginRequiredMixin, TemplateView):
    template_name = "assessment/objective-overview.html"
    login_url = "/oidc/authenticate/"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        from webcaf import settings

        data = super().get_context_data(**kwargs)
        parent_map: dict[str, Any] = settings.CAF_FRAMEWORKS["v3.2"]
        assessment_id = self.request.session["draft_assessment"]["assessment_id"]
        data["breadcrumbs"] = [
            {
                "url": reverse("my-account", kwargs={}),
                "text": "Home",
            },
            {
                "url": reverse("edit-draft-assessment", kwargs={"version": "v3.2", "assessment_id": assessment_id}),
                "text": "Edit draft assessment",
            },
            {
                "text": kwargs["objective_id"].replace("_", " ").title()
                + " - "
                + parent_map[kwargs["objective_id"]]["text"],
            },
        ]
        data["objective_heading"] = (
            kwargs["objective_id"].replace("_", " ").title() + " - " + parent_map[kwargs["objective_id"]]["text"]
        )
        data["principles"] = []
        # Build the list of principles based on the parent map. This will be used to display in the table with
        # the links to the indicators.
        assessment = self.get_assessment()
        for principle in list(filter(lambda x: x[1]["parent"] == kwargs["objective_id"], parent_map.items())):
            data["principles"].append(
                {
                    "name": principle[0].replace("_", ":").title() + " " + principle[1]["text"],
                    "indicators": [
                        {
                            "id": x[0],
                            "title": x[0].replace("indicators_", "") + " " + x[1]["text"],
                            "complete": assessment.assessments_data.get("indicator_" + x[0]) is not None,
                            "outcome": self.calculate_outcome_status("indicator_" + x[0]),
                        }
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

    def get_assessment(self):
        id_ = self.request.session["draft_assessment"]["assessment_id"]
        user_profile_id = self.request.session["current_profile_id"]
        user_profile = UserProfile.objects.get(id=user_profile_id)
        assessment = Assessment.objects.get(
            status="draft", id=id_, system__organisation_id=user_profile.organisation.id
        )
        return assessment

    def calculate_outcome_status(self, indicator_id: str):
        assessment = self.get_assessment()
        indicators = assessment.assessments_data.get(indicator_id)
        if indicators:
            achieved_responses = set(
                map(
                    lambda x: x[1],
                    filter(
                        lambda x: not x[0].endswith("_comment") and x[0].startswith("achieved_"), indicators.items()
                    ),
                )
            )
            return (
                "not achieved" if len(achieved_responses) != 1 or "agreed" not in achieved_responses else "achieved"
            ).capitalize()
        return "not achieved".capitalize()
