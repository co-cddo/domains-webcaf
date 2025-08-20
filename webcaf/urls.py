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

from webcaf.webcaf.views import (
    ChangeActiveProfileView,
    CreateAssessmentProfileView,
    CreateAssessmentSystemView,
    CreateAssessmentView,
    EditAssessmentProfileView,
    EditAssessmentSystemView,
    EditAssessmentView,
    Index,
    MyAccountView,
    MyAccountViewAssessmentsView,
    MyOrganisationView,
    OrganisationContactView,
    OrganisationTypeView,
)
from webcaf.webcaf.views.general_views import logout_view
from webcaf.webcaf.views.objective_views import ObjectiveConfirmationView, ObjectiveView
from webcaf.webcaf.views.system_views import (
    CreateOrSkipSystemView,
    EditSystemView,
    SystemView,
    ViewSystemsView,
)
from webcaf.webcaf.views.users_profiles_view import (
    CreateOrSkipUserProfileView,
    CreateUserProfileView,
    RemoveUserProfileView,
    UserProfilesView,
    UserProfileView,
)
from webcaf.webcaf.views.workflow_views import (
    OutcomeConfirmationHandlerView,
    OutcomeIndicatorsHandlerView,
)

urlpatterns = [
    path("", Index.as_view(), name="index"),
    path("my-account/", MyAccountView.as_view(), name="my-account"),
    path("my-account/view-draft-assessments/", MyAccountViewAssessmentsView.as_view(), name="view-draft-assessments"),
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
    # Editing existing draft assessment
    path(
        "<str:version>/edit-draft-assessment/<int:assessment_id>/",
        EditAssessmentView.as_view(),
        name="edit-draft-assessment",
    ),
    path(
        "<str:version>/edit-draft-assessment/<int:assessment_id>/profile",
        EditAssessmentProfileView.as_view(),
        name="edit-draft-assessment-profile",
    ),
    path(
        "<str:version>/edit-draft-assessment/<int:assessment_id>/system",
        EditAssessmentSystemView.as_view(),
        name="edit-draft-assessment-system",
    ),
    #     Objective overview paths
    path("<str:version>/objective-overview/<str:objective_id>/", ObjectiveView.as_view(), name="objective-overview"),
    path("<str:version>/objective-confirmation/", ObjectiveConfirmationView.as_view(), name="objective-confirmation"),
    path("<str:version>/indicator/<str:indicator_id>/", OutcomeIndicatorsHandlerView.as_view(), name="indicator-view"),
    path(
        "<str:version>/indicator/<str:indicator_id>/confirmation",
        OutcomeConfirmationHandlerView.as_view(),
        name="indicator-confirmation-view",
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
]
