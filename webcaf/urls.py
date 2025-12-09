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
    ViewDraftAssessmentsView,
    ViewSubmittedAssessmentsView,
)
from webcaf.webcaf.views.assessor.assessor import (
    AssessorsView,
    CreateOrSkipAssessorView,
    EditAssessorView,
    RemoveAssessorView,
)
from webcaf.webcaf.views.assessor.review import (
    DownloadReport,
    EditReviewSystemView,
    ReopenReviewView,
    ReviewDetailView,
    ReviewHistoryView,
    ReviewIndexView,
    ShowReportView,
    SystemAndScopeView,
)
from webcaf.webcaf.views.assessor.review_assessment import (
    AddIarPeriodView,
    AddObjectiveAreasOfGoodPracticeView,
    AddObjectiveAreasOfImprovementView,
    AddObjectiveRecommendationView,
    AddOutcomeRecommendationView,
    AddQualityOfEvidenceView,
    AddReviewMethodView,
    CreateReportView,
    ObjectiveSummaryView,
    OutcomeView,
    ShowReportConfirmation,
)
from webcaf.webcaf.views.general import logout_view
from webcaf.webcaf.views.sections import (
    DownloadSubmittedAssessmentPdf,
    SectionConfirmationView,
    ShowSubmissionConfirmationView,
    ViewSubmittedAssessment,
)
from webcaf.webcaf.views.session_expired import session_expired
from webcaf.webcaf.views.system import (
    CreateOrSkipSystemView,
    EditSystemView,
    SystemView,
    ViewSystemsView,
)
from webcaf.webcaf.views.two_factor_auth import Verify2FATokenView
from webcaf.webcaf.views.user_profiles import (
    CreateOrSkipUserProfileView,
    CreateUserProfileView,
    RemoveUserProfileView,
    UserProfilesView,
    UserProfileView,
)

urlpatterns = [
    path("my-account/", AccountView.as_view(), name="my-account"),
    path("my-account/view-draft-assessments/", ViewDraftAssessmentsView.as_view(), name="view-draft-assessments"),
    path("my-organisation/<int:id>/type", OrganisationTypeView.as_view(), name="edit-my-organisation-type"),
    path("my-organisation/<int:id>/contact", OrganisationContactView.as_view(), name="edit-my-organisation-contact"),
    path("my-organisation/<int:id>/", MyOrganisationView.as_view(), name="my-organisation"),
    path("view-organisations/", ChangeActiveProfileView.as_view(), name="view-organisations"),
    path("change-organisation/", ChangeActiveProfileView.as_view(), name="change-organisation"),
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
    path("view-submitted-assessments/", ViewSubmittedAssessmentsView.as_view(), name="view-submitted-assessments"),
    path(
        "view-submitted-assessment/<int:assessment_id>",
        ViewSubmittedAssessment.as_view(),
        name="view-submitted-assessment",
    ),
    path(
        "download-submitted-assessment/<int:assessment_id>",
        DownloadSubmittedAssessmentPdf.as_view(),
        name="download-submitted-assessment",
    ),
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
    # Public pages
    path("public/data-usage-policy/", TemplateView.as_view(template_name="data-policy.html"), name="data-usage-policy"),
    path("public/cookies/", TemplateView.as_view(template_name="cookies.html"), name="cookies"),
    path("public/privacy/", TemplateView.as_view(template_name="privacy.html"), name="privacy"),
    path("public/help/", TemplateView.as_view(template_name="help.html"), name="help"),
    path("public/accessibility/", TemplateView.as_view(template_name="accessibility.html"), name="accessibility"),
    # Application pages that does not need login
    path("logout/", logout_view, name="logout"),
    path("", Index.as_view(), name="index"),
    path("assessor/", TemplateView.as_view(template_name="assessor-index.html"), name="assessor-index"),
    path("session-expired/", session_expired, name="session-expired"),
    path("verify-2fa-token/", Verify2FATokenView.as_view(), name="verify-2fa-token"),
    # Assessor pages
    path("create-or-skip-new-assessor/", CreateOrSkipAssessorView.as_view(), name="create-or-skip-new-assessor"),
    path("assessor-list/", AssessorsView.as_view(), name="assessor-list"),
    path("add-assessor/", EditAssessorView.as_view(), name="add-assessor"),
    path("edit-assessor/<int:pk>/", EditAssessorView.as_view(), name="edit-assessor"),
    path("remove-assessor/<int:pk>/", RemoveAssessorView.as_view(), name="remove-assessor"),
    # Review paths
    path("review/", ReviewIndexView.as_view(), name="review-list"),
    path("review/<int:pk>/", ReviewDetailView.as_view(), name="edit-review"),
    path("review/<int:pk>/revisions", ReviewHistoryView.as_view(), name="review-history"),
    path("review/<int:pk>/reopen", ReopenReviewView.as_view(), name="reopen-review"),
    path("review/<int:pk>/system-and-scope", SystemAndScopeView.as_view(), name="system-and-scope"),
    path("review/<int:pk>/system/<str:field_to_change>", EditReviewSystemView.as_view(), name="edit-review-system"),
    path(
        "review/<int:pk>/objective-summary/<str:objective_code>",
        ObjectiveSummaryView.as_view(),
        name="objective-summary",
    ),
    path(
        "review/<int:pk>/next-objective/<str:objective_code>",
        ObjectiveSummaryView.as_view(),
        name="next-objective-or-skip",
    ),
    path(
        "review/<int:pk>/outcome/<str:objective_code>/<str:outcome_code>",
        OutcomeView.as_view(),
        name="review-outcome",
    ),
    path(
        "review/<int:pk>/recommendations/<str:objective_code>/<str:outcome_code>",
        AddOutcomeRecommendationView.as_view(),
        name="review-outcome-recommendation",
    ),
    path(
        "review/<int:pk>/recommendations/<str:objective_code>/",
        AddObjectiveRecommendationView.as_view(),
        name="review-objective-recommendation",
    ),
    path(
        "review/<int:pk>/areas-of-improvement/<str:objective_code>/",
        AddObjectiveAreasOfImprovementView.as_view(),
        name="review-objective-areas-of-improvement",
    ),
    path(
        "review/<int:pk>/areas-of-good-practice/<str:objective_code>/",
        AddObjectiveAreasOfGoodPracticeView.as_view(),
        name="review-objective-areas-of-good-practice",
    ),
    path(
        "review/<int:pk>/quality-of-evidence/",
        AddQualityOfEvidenceView.as_view(),
        name="quality-of-evidence",
    ),
    path(
        "review/<int:pk>/review-method/",
        AddReviewMethodView.as_view(),
        name="review-method",
    ),
    path(
        "review/<int:pk>/iar-period/",
        AddIarPeriodView.as_view(),
        name="iar-period",
    ),
    path(
        "review/<int:pk>/create-report/",
        CreateReportView.as_view(),
        name="create-report",
    ),
    path(
        "review/<int:pk>/show-report-confirmation/",
        ShowReportConfirmation.as_view(),
        name="show-report-confirmation",
    ),
    path(
        "review/<int:pk>/<int:version>/show-report/",
        ShowReportView.as_view(),
        name="show-report",
    ),
    path(
        "review/<int:pk>/<int:version>/download-report/",
        DownloadReport.as_view(),
        name="download-report",
    ),
]
