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
    MyOrganisationView,
    OrganisationContactView,
    OrganisationTypeView,
)
from webcaf.webcaf.views.general_views import logout_view

urlpatterns = [
    path("", Index.as_view(), name="index"),
    path("my-account/", MyAccountView.as_view(), name="my-account"),
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
]
