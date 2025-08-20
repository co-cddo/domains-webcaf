from abc import abstractmethod
from typing import Any, Dict

from django.contrib.auth.mixins import LoginRequiredMixin

from webcaf.webcaf.models import UserProfile


def get_current_user_profile(request):
    current_profile_id = request.session.get("current_profile_id")
    return UserProfile.objects.filter(user=request.user, id=current_profile_id).first()


class UserRoleCheckMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        else:
            user_profile = get_current_user_profile(request)
            if user_profile.role not in self.get_allowed_roles():
                return self.handle_no_permission()
            return super().dispatch(request, *args, **kwargs)

    @abstractmethod
    def get_allowed_roles(self) -> list[str]:
        """
        Needs to be implemented by the subclass.
        List of roles that are allowed to access the view.
        :return:
        """


# ----- Helpers -----
def get_parent_map() -> Dict[str, Any]:
    """Return the framework routing map for version v3.2.

    The parent_map defines relationships between objectives, principles, and
    indicators, e.g.:
    - objective_X -> principle_Xn
    - principle_Xn -> indicators_Xn.*
    """
    from webcaf.webcaf.router_factory import ROUTE_FACTORY

    return ROUTE_FACTORY.get_router("v3.2").parent_map


def principles_for_objective(parent_map: Dict[str, Any], objective_id: str) -> list[tuple[str, dict[str, Any]]]:
    """Filter principles that have the given objective as their parent.

    Returns:
        List of (principle_key, principle_value) tuples.
    """
    return [item for item in parent_map.items() if item[1].get("parent") == objective_id]


def indicators_for_principle(parent_map: dict[str, Any], principle_key: str) -> list[tuple[str, dict[str, Any]]]:
    """Return indicator entries that belong to the given principle.

    Only keys that start with "indicators" are included.
    """
    return [
        item
        for item in parent_map.items()
        if item[1].get("parent") == principle_key and item[0].startswith("indicators")
    ]


def format_objective_heading(objective_id: str, parent_map: dict[str, Any]) -> str:
    """Format the objective heading combining ID and human text.

    Example: "objective_A" + "Some title" -> "Objective A - Some title"
    """
    return objective_id.replace("_", " ").title() + " - " + parent_map[objective_id]["text"]


def format_principle_name(principle_key: str, text: str) -> str:
    """Format a principle label: replace first underscore with colon and title-case.

    Example: "principle_A1" + "Text" -> "Principle:A1 Text"
    """
    return principle_key.replace("_", ":").title() + " " + text


def format_indicator_title(indicator_key: str, text: str) -> str:
    """Format the indicator title by stripping "indicators_" prefix.

    Example: "indicators_A1.a" + "Text" -> "A1.a Text"
    """
    return indicator_key.replace("indicators_", "") + " " + text
