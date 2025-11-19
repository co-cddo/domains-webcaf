from django.urls import reverse_lazy
from django.views.generic import TemplateView

from webcaf.webcaf.models import Review
from webcaf.webcaf.utils.permission import UserRoleCheckMixin
from webcaf.webcaf.utils.session import SessionUtil


class ReviewIndexView(UserRoleCheckMixin, TemplateView):
    """
    Provides a view for assessors' account page/ list of reviews opened for the current organisation.

    This class-based view is designed for authenticated users to display the assessor's
    account page. It ensures that only logged-in users can access the page, and it provides
    necessary context data such as the current user profile and associated reviews.

    :ivar template_name: Path to the template file that renders the assessor's account page.
    :type template_name: str
    :ivar login_url: URL route to initiate the OIDC login process for unauthenticated users.
    :type login_url: str
    """

    template_name = "review/list.html"
    login_url = reverse_lazy("oidc_authentication_init")  # OIDC login route

    def get_allowed_roles(self) -> list[str]:
        return [
            "cyber_advisor",
            "organisation_lead",
            "reviewer",
            "assessor",
        ]

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        data["reviews"] = Review.objects.filter(
            assessed_by__is_active=True,
            assessment__status__in=["submitted"],
            assessment__system__organisation=data["current_profile"].organisation,
        )
        return data
