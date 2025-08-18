"""Objective overview view and helpers.

This module defines the ObjectiveView, a Django class-based view that renders the
objective overview page for an assessment workflow in the WebCAF application.

Key responsibilities:
- Build breadcrumbs for navigation back to the draft assessment.
- Derive objective heading, principles, and their indicators from the framework
  routing map (ROUTE_FACTORY for version v3.2).
- Determine completion state and outcome status per indicator from the
  persisted Assessment.assessments_data.
- Provide next-step navigation info to the template (e.g., whether this is the
  final objective and what the next objective is).

Session contract used by this view:
- request.session["draft_assessment"]["assessment_id"]: int – ID of the draft assessment.
- request.session["current_profile_id"]: int – ID of the current UserProfile used
  to scope the assessment to the user’s organisation.

Performance considerations:
- The view caches the Assessment object for the lifetime of a request using
  django.utils.functional.cached_property to avoid repeated database queries.

Template context produced (selected keys):
- breadcrumbs: List[Dict[str, str]] – Navigation trail to display.
- objective_heading: str – Formatted title for the current objective.
- principles: List[Dict[str, Any]] – Principles under the objective, including
  their indicators with completion and outcome status.
- final_objective: bool – True if this objective is the last in the framework.
- assessment_id: int – Current assessment ID from the session.
- next_objective: Optional[str] – Provided only when not the last objective.

Notes:
- All framework structure (objectives, principles, indicators and their
  relationships) is sourced from ROUTE_FACTORY.get_router("v3.2").parent_map.
- The view keeps behavior intentionally aligned with existing logic to avoid
  any functional changes.
"""
from typing import Any, Dict, List, Tuple

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.generic import TemplateView

from webcaf.webcaf.models import Assessment, UserProfile
from webcaf.webcaf.router_factory import ROUTE_FACTORY
from webcaf.webcaf.status_calculator import calculate_outcome_status


class ObjectiveView(LoginRequiredMixin, TemplateView):
    """Render the Objective overview page for a given objective.

    Combines router metadata and persisted assessment data to produce the
    context required by the assessment/objective-overview.html template.

    Authentication:
        Requires login; unauthenticated users are redirected to /oidc/authenticate/.

    Template:
        assessment/objective-overview.html

    Session requirements:
        - draft_assessment.assessment_id
        - current_profile_id
    """

    template_name = "assessment/objective-overview.html"
    login_url = "/oidc/authenticate/"

    # Constants to avoid magic strings while keeping behavior identical
    _SESSION_DRAFT_ASSESSMENT = "draft_assessment"
    _SESSION_ASSESSMENT_ID = "assessment_id"
    _SESSION_CURRENT_PROFILE_ID = "current_profile_id"

    # Use a cached_property to avoid repeated DB lookups within the same request
    @cached_property
    def assessment(self) -> Assessment:
        return self.get_assessment()

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Assemble the template context for the objective overview.

        Expects kwargs to contain:
            objective_id: str – The objective key (e.g., "objective_A").

        Adds to context:
            - breadcrumbs, objective_heading, principles (with indicators),
              final_objective, assessment_id, and next_objective when relevant.
        """
        data = super().get_context_data(**kwargs)
        parent_map: Dict[str, Any] = self._get_parent_map()
        assessment_id = self.request.session[self._SESSION_DRAFT_ASSESSMENT][self._SESSION_ASSESSMENT_ID]
        objective_id: str = kwargs["objective_id"]

        # Breadcrumbs
        objective_title = self._format_objective_heading(objective_id, parent_map)
        data["breadcrumbs"] = self._build_breadcrumbs(assessment_id, objective_title)

        # Objective heading
        data["objective_heading"] = objective_title

        # Build the list of principles based on the parent map. This will be used to display
        # in the table with the links to the indicators.
        assessment = self.assessment

        # Navigation data (computed once)
        is_last_objective, next_objective = self._objective_navigation(objective_id, parent_map)
        data["final_objective"] = is_last_objective
        data["assessment_id"] = assessment_id
        if not is_last_objective and next_objective:
            data["next_objective"] = next_objective

        data["principles"] = []

        # Select principles where parent == objective_id
        principles: List[Tuple[str, Dict[str, Any]]] = self._principles_for_objective(parent_map, objective_id)

        for principle_key, principle_val in principles:
            indicators: List[Tuple[str, Dict[str, Any]]] = self._indicators_for_principle(parent_map, principle_key)

            data["principles"].append(
                {
                    "name": self._format_principle_name(principle_key, principle_val["text"]),
                    "indicators": [
                        {
                            "id": indicator_key,
                            "title": self._format_indicator_title(indicator_key, indicator_val["text"]),
                            "complete": assessment.assessments_data.get(f"indicator_{indicator_key}") is not None,
                            "outcome": self.calculate_outcome_status(f"indicator_{indicator_key}"),
                        }
                        for indicator_key, indicator_val in indicators
                    ],
                }
            )

        return data

    # ----- Helpers -----
    def _get_parent_map(self) -> Dict[str, Any]:
        """Return the framework routing map for version v3.2.

        The parent_map defines relationships between objectives, principles, and
        indicators, e.g.:
        - objective_X -> principle_Xn
        - principle_Xn -> indicators_Xn.*
        """
        return ROUTE_FACTORY.get_router("v3.2").parent_map

    def _build_breadcrumbs(self, assessment_id: str, objective_title: str) -> List[Dict[str, Any]]:
        """Construct the breadcrumb trail for the objective overview page.

        Parameters:
            assessment_id: The current draft assessment ID from session.
            objective_title: The formatted title for the current objective.

        Returns:
            A list of dictionaries with keys: url (optional) and text.
        """
        return [
            {
                "url": reverse("my-account", kwargs={}),  # keep kwargs={} for 1:1 behavior
                "text": "Home",
            },
            {
                "url": reverse(
                    "edit-draft-assessment",
                    kwargs={"version": "v3.2", "assessment_id": assessment_id},
                ),
                "text": "Edit draft assessment",
            },
            {
                "text": objective_title,
            },
        ]

    def _objective_navigation(self, objective_id: str, parent_map: Dict[str, Any]) -> Tuple[bool, str | None]:
        """Derive navigation flags for the current objective.

        Parameters:
            objective_id: The current objective key (e.g., "objective_A").
            parent_map: Framework structure map.

        Returns:
            Tuple[is_last_objective, next_objective_id_or_None]
        """
        all_objectives = [k for k in parent_map.keys() if k.startswith("objective_")]
        # If the objective isn't in the list, treat as last to keep safe behavior
        is_last = (
            all_objectives.index(objective_id) == len(all_objectives) - 1 if objective_id in all_objectives else True
        )
        if is_last:
            return True, None
        objective_key = objective_id.split("_")[1]
        return False, f"objective_{chr(ord(objective_key) + 1)}"

    def _principles_for_objective(
        self, parent_map: Dict[str, Any], objective_id: str
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Filter principles that have the given objective as their parent.

        Returns:
            List of (principle_key, principle_value) tuples.
        """
        return [item for item in parent_map.items() if item[1].get("parent") == objective_id]

    def _indicators_for_principle(
        self, parent_map: Dict[str, Any], principle_key: str
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Return indicator entries that belong to the given principle.

        Only keys that start with "indicators" are included.
        """
        return [
            item
            for item in parent_map.items()
            if item[1].get("parent") == principle_key and item[0].startswith("indicators")
        ]

    @staticmethod
    def _format_objective_heading(objective_id: str, parent_map: Dict[str, Any]) -> str:
        """Format the objective heading combining ID and human text.

        Example: "objective_A" + "Some title" -> "Objective A - Some title"
        """
        return objective_id.replace("_", " ").title() + " - " + parent_map[objective_id]["text"]

    @staticmethod
    def _format_principle_name(principle_key: str, text: str) -> str:
        """Format a principle label: replace first underscore with colon and title-case.

        Example: "principle_A1" + "Text" -> "Principle:A1 Text"
        """
        return principle_key.replace("_", ":").title() + " " + text

    @staticmethod
    def _format_indicator_title(indicator_key: str, text: str) -> str:
        """Format the indicator title by stripping "indicators_" prefix.

        Example: "indicators_A1.a" + "Text" -> "A1.a Text"
        """
        return indicator_key.replace("indicators_", "") + " " + text

    # ----- Data access -----
    def get_assessment(self) -> Assessment:
        """Fetch the current draft Assessment for the user's organisation.

        Reads the assessment_id and current_profile_id from the session and then
        retrieves the Assessment scoped by the user's organisation.

        Returns:
            The draft Assessment instance.

        Raises:
            KeyError: If required session keys are missing.
            UserProfile.DoesNotExist: If the stored profile id is invalid.
            Assessment.DoesNotExist: If a matching draft assessment is not found.
        """
        id_: int = self.request.session[self._SESSION_DRAFT_ASSESSMENT][self._SESSION_ASSESSMENT_ID]
        user_profile_id = self.request.session[self._SESSION_CURRENT_PROFILE_ID]
        user_profile = UserProfile.objects.get(id=user_profile_id)
        assessment = Assessment.objects.get(status="draft", id=id_, system__organisation=user_profile.organisation)
        return assessment

    def calculate_outcome_status(self, indicator_id: str) -> Any:
        """Calculate the derived outcome status for a given indicator.

        Parameters:
            indicator_id: The key used in assessments_data for the indicator
                responses (e.g., "indicator_indicators_A1.a"). The corresponding
                confirmation key is computed by replacing the "indicator_" prefix
                with "confirmation_".

        Returns:
            Whatever value is produced by webcaf.webcaf.views.status_calculator
            calculate_outcome_status(confirmation, indicators). Typically a
            status token/label consumed by templates.

        Notes:
            Accesses the cached Assessment instance to avoid repeated DB hits.
        """
        assessment = self.assessment
        indicators = assessment.assessments_data.get(indicator_id, {})
        confirmation = assessment.assessments_data.get(
            indicator_id.replace("indicator_", "confirmation_"),
            {},
        )
        return calculate_outcome_status(confirmation, indicators)
