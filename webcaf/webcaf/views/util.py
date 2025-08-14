from abc import abstractmethod

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
