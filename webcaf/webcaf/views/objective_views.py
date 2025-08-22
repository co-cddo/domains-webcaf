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

        objective_id = kwargs["objective_id"]
        data = super().get_context_data(**kwargs)
        parent_map: dict[str, Any] = settings.CAF_FRAMEWORKS["v3.2"].framework["objectives"][objective_id.split("_")[1]]
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
                "text": kwargs["objective_id"].replace("_", " ").title() + " - " + parent_map["title"],
            },
        ]
        data["objective_heading"] = kwargs["objective_id"].replace("_", " ").title() + " - " + parent_map["title"]
        data["principles"] = []
        # Build the list of principles based on the parent map. This will be used to display in the table with
        # the links to the indicators.
        assessment = self.get_assessment()
        for principle in parent_map["principles"].values():
            data["principles"].append(
                {
                    "name": f"Principal : {principle['code']} {principle['title']}",
                    "indicators": [
                        {
                            "id": f"indicators_{x['code']}",
                            "title": f'{x["code"]}  {x["title"]}',
                            "complete": assessment.assessments_data.get("indicator_indicators_" + x["code"])
                            is not None,
                            "outcome": self.calculate_outcome_status("indicator_indicators_" + x["code"]),
                        }
                        for x in principle["outcomes"].values()
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
