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

from webcaf.webcaf.general_views import (
    ChangeOrganisationView,
    Index,
    MyAccountView,
    MyOrganisationView,
    logout_view,
)

urlpatterns = [
    path("", Index.as_view(), name="index"),
    path("my-account/", MyAccountView.as_view(), name="my-account"),
    path("my-organisation/<int:id>/<str:mode>", MyOrganisationView.as_view(), name="edit-my-organisation"),
    path("my-organisation/<int:id>/", MyOrganisationView.as_view(), name="my-organisation"),
    path("view-organisations/", ChangeOrganisationView.as_view(), name="view-organisations"),
    path("change-organisation/", ChangeOrganisationView.as_view(), name="change-organisation"),
    path("logout/", logout_view, name="logout"),
    path("admin/", admin.site.urls),
    path("oidc/", include("mozilla_django_oidc.urls")),
]
