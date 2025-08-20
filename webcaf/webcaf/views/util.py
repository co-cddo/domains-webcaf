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
