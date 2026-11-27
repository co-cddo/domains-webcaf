from .account import AccountView, ViewDraftAssessmentsView
from .assesment import (
    CreateAssessmentProfileView,
    CreateAssessmentReviewTypeView,
    CreateAssessmentSystemView,
    CreateAssessmentView,
    EditAssessmentProfileView,
    EditAssessmentReviewTypeView,
    EditAssessmentSystemView,
    EditAssessmentView,
    ExportAssessmentTemplateView,
)
from .general import AuthenticationErrorView, Index, logout_view  # noqa
from .organisation import (
    ChangeActiveProfileView,
    MyOrganisationView,
)
from .sections import ViewSubmittedAssessmentsView

__all__ = [
    # Assessment views
    "EditAssessmentSystemView",
    "EditAssessmentProfileView",
    "CreateAssessmentSystemView",
    "CreateAssessmentProfileView",
    "EditAssessmentView",
    "CreateAssessmentView",
    "CreateAssessmentReviewTypeView",
    "EditAssessmentReviewTypeView",
    "ExportAssessmentTemplateView",
    # General views
    "logout_view",
    "AuthenticationErrorView",
    # Account views
    "Index",
    "AccountView",
    "ViewDraftAssessmentsView",
    # Organisation views
    "MyOrganisationView",
    "ChangeActiveProfileView",
    # Workflow views
    "ViewSubmittedAssessmentsView",
]
