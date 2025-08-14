from typing import Any, Dict, List, Tuple

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.generic import TemplateView

from webcaf.webcaf.models import Assessment, UserProfile
from webcaf.webcaf.views.status_calculator import calculate_outcome_status


class ObjectiveView(LoginRequiredMixin, TemplateView):
    """Render the Objective overview page.

    This view builds breadcrumbs, objective heading, and a tabular list of
    principles and their indicators for a given objective. Logic is kept as a
    1-to-1 replacement of the previous implementation while improving
    readability and maintainability.
    """

    template_name = "assessment/objective-overview.html"
    login_url = "/oidc/authenticate/"

    # Constants to avoid magic strings while keeping behavior identical
    _SESSION_DRAFT_ASSESSMENT = "draft_assessment"
    _SESSION_ASSESSMENT_ID = "assessment_id"
    _SESSION_CURRENT_PROFILE_ID = "current_profile_id"
    _FRAMEWORK_VERSION = "v3.2"

    # Use a cached_property to avoid repeated DB lookups within the same request
    @cached_property
    def assessment(self) -> Assessment:
        return self.get_assessment()

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        from webcaf import settings  # keep as-is to avoid changing import behavior

        data = super().get_context_data(**kwargs)
        parent_map: Dict[str, Any] = settings.CAF_FRAMEWORKS[self._FRAMEWORK_VERSION]
        assessment_id = self.request.session[self._SESSION_DRAFT_ASSESSMENT][self._SESSION_ASSESSMENT_ID]

        objective_id: str = kwargs["objective_id"]

        # Breadcrumbs
        data["breadcrumbs"] = [
            {
                "url": reverse("my-account", kwargs={}),  # keep kwargs={} for 1:1 behavior
                "text": "Home",
            },
            {
                "url": reverse(
                    "edit-draft-assessment",
                    kwargs={"version": self._FRAMEWORK_VERSION, "assessment_id": assessment_id},
                ),
                "text": "Edit draft assessment",
            },
            {
                "text": self._format_objective_heading(objective_id, parent_map),
            },
        ]

        # Objective heading
        data["objective_heading"] = self._format_objective_heading(objective_id, parent_map)

        # Build the list of principles based on the parent map. This will be used to display
        # in the table with the links to the indicators.
        assessment = self.assessment

        data["principles"] = []

        # Select principles where parent == objective_id
        principles: List[Tuple[str, Dict[str, Any]]] = [
            item for item in parent_map.items() if item[1].get("parent") == objective_id
        ]

        for principle_key, principle_val in principles:
            indicators: List[Tuple[str, Dict[str, Any]]] = [
                item
                for item in parent_map.items()
                if item[1].get("parent") == principle_key and item[0].startswith("indicators")
            ]

            all_objectives = list(filter(lambda x: x.startswith("objective_"), parent_map.keys()))
            is_last_objective = all_objectives.index(objective_id) == len(all_objectives) - 1
            objective_key = objective_id.split("_")[1]
            data["final_objective"] = is_last_objective
            data["assessment_id"] = assessment_id
            if not is_last_objective:
                data["next_objective"] = f"objective_{chr(ord(objective_key) + 1)}"
            data["principles"].append(
                {
                    "name": self._format_principle_name(principle_key, principle_val["text"]),
                    "indicators": [
                        {
                            "id": indicator_key,
                            "title": self._format_indicator_title(indicator_key, indicator_val["text"]),
                            "complete": assessment.assessments_data.get("indicator_" + indicator_key) is not None,
                            "outcome": self.calculate_outcome_status("indicator_" + indicator_key),
                        }
                        for indicator_key, indicator_val in indicators
                    ],
                }
            )

        return data

    # ----- Helpers -----

    @staticmethod
    def _format_objective_heading(objective_id: str, parent_map: Dict[str, Any]) -> str:
        return objective_id.replace("_", " ").title() + " - " + parent_map[objective_id]["text"]

    @staticmethod
    def _format_principle_name(principle_key: str, text: str) -> str:
        return principle_key.replace("_", ":").title() + " " + text

    @staticmethod
    def _format_indicator_title(indicator_key: str, text: str) -> str:
        return indicator_key.replace("indicators_", "") + " " + text

    # ----- Data access -----

    def get_assessment(self) -> Assessment:
        """Fetch the current draft assessment for the user's organisation.

        Note: Kept behavior identical to the original implementation.
        """
        id_: int = self.request.session[self._SESSION_DRAFT_ASSESSMENT][self._SESSION_ASSESSMENT_ID]
        user_profile_id = self.request.session[self._SESSION_CURRENT_PROFILE_ID]
        user_profile = UserProfile.objects.get(id=user_profile_id)
        assessment = Assessment.objects.get(status="draft", id=id_, system__organisation=user_profile.organisation)
        return assessment

    def calculate_outcome_status(self, indicator_id: str) -> Any:
        """Calculate the outcome status for an indicator.

        Uses a cached assessment when available to avoid duplicate queries within
        the same request lifecycle. Falls back to fetching the assessment to keep
        external behavior identical.
        """
        assessment = self.assessment
        indicators = assessment.assessments_data.get(indicator_id, {})
        confirmation = assessment.assessments_data.get(
            indicator_id.replace("indicator_", "confirmation_"),
            {},
        )
        return calculate_outcome_status(confirmation, indicators)
