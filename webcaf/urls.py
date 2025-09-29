"""
URL configuration for webcaf project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from webcaf.webcaf.views import (
    AccountView,
    AccountViewAssessmentsView,
    ChangeActiveProfileView,
    CreateAssessmentProfileView,
    CreateAssessmentReviewTypeView,
    CreateAssessmentSystemView,
    CreateAssessmentView,
    EditAssessmentProfileView,
    EditAssessmentReviewTypeView,
    EditAssessmentSystemView,
    EditAssessmentView,
    Index,
    MyOrganisationView,
    OrganisationContactView,
    OrganisationTypeView,
)
from webcaf.webcaf.views.general import logout_view
from webcaf.webcaf.views.sections import (
    SectionConfirmationView,
    ShowSubmissionConfirmationView,
)
from webcaf.webcaf.views.system import (
    CreateOrSkipSystemView,
    EditSystemView,
    SystemView,
    ViewSystemsView,
)
from webcaf.webcaf.views.user_profiles import (
    CreateOrSkipUserProfileView,
    CreateUserProfileView,
    RemoveUserProfileView,
    UserProfilesView,
    UserProfileView,
)

urlpatterns = [
    path("", Index.as_view(), name="index"),
    path("my-account/", AccountView.as_view(), name="my-account"),
    path("my-account/view-draft-assessments/", AccountViewAssessmentsView.as_view(), name="view-draft-assessments"),
    path("my-organisation/<int:id>/type", OrganisationTypeView.as_view(), name="edit-my-organisation-type"),
    path("my-organisation/<int:id>/contact", OrganisationContactView.as_view(), name="edit-my-organisation-contact"),
    path("my-organisation/<int:id>/", MyOrganisationView.as_view(), name="my-organisation"),
    path("view-organisations/", ChangeActiveProfileView.as_view(), name="view-organisations"),
    path("change-organisation/", ChangeActiveProfileView.as_view(), name="change-organisation"),
    path("logout/", logout_view, name="logout"),
    path("admin/", admin.site.urls),
    path("oidc/", include("mozilla_django_oidc.urls")),
    #     Assessment paths
    path("create-draft-assessment/", CreateAssessmentView.as_view(), name="create-draft-assessment"),
    path(
        "create-draft-assessment/profile", CreateAssessmentProfileView.as_view(), name="create-draft-assessment-profile"
    ),
    path("create-draft-assessment/system", CreateAssessmentSystemView.as_view(), name="create-draft-assessment-system"),
    path(
        "create-draft-assessment/review-type",
        CreateAssessmentReviewTypeView.as_view(),
        name="create-draft-assessment-choose-review-type",
    ),
    # Editing existing draft assessment
    path("edit-draft-assessment/<int:assessment_id>/", EditAssessmentView.as_view(), name="edit-draft-assessment"),
    path(
        "edit-draft-assessment/<int:assessment_id>/profile",
        EditAssessmentProfileView.as_view(),
        name="edit-draft-assessment-profile",
    ),
    path(
        "edit-draft-assessment/<int:assessment_id>/system",
        EditAssessmentSystemView.as_view(),
        name="edit-draft-assessment-system",
    ),
    path(
        "edit-draft-assessment/<int:assessment_id>/review-type",
        EditAssessmentReviewTypeView.as_view(),
        name="edit-draft-assessment-choose-review-type",
    ),
    path("objective-confirmation/", SectionConfirmationView.as_view(), name="objective-confirmation"),
    path(
        "show-submission-confirmation/", ShowSubmissionConfirmationView.as_view(), name="show-submission-confirmation"
    ),
    #     system paths
    path("create-new-system/", SystemView.as_view(), name="create-new-system"),
    path("edit-system/<int:system_id>/", EditSystemView.as_view(), name="edit-system"),
    path("view-systems/", ViewSystemsView.as_view(), name="view-systems"),
    path("create-or-skip-new-system/", CreateOrSkipSystemView.as_view(), name="create-or-skip-new-system"),
    #     User management paths
    path("create-new-profile/", CreateUserProfileView.as_view(), name="create-new-profile"),
    path("create-or-skip-new-profile/", CreateOrSkipUserProfileView.as_view(), name="create-or-skip-new-profile"),
    path("edit-profile/<int:user_profile_id>", UserProfileView.as_view(), name="edit-profile"),
    path("remove-profile/<int:user_profile_id>", RemoveUserProfileView.as_view(), name="remove-profile"),
    path("view-profiles/", UserProfilesView.as_view(), name="view-profiles"),
    path("data-usage-policy/", TemplateView.as_view(template_name="data-policy.html")),
    path("cookies/", TemplateView.as_view(template_name="cookies.html")),
    path("privacy/", TemplateView.as_view(template_name="privacy.html")),
    path("help/", TemplateView.as_view(template_name="help.html")),
]
