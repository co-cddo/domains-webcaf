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
)
from .general import Index, logout_view  # noqa
from .organisation import (
    ChangeActiveProfileView,
    MyOrganisationView,
    OrganisationContactView,
    OrganisationTypeView,
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
    # General views
    "logout_view",
    # Account views
    "Index",
    "AccountView",
    "ViewDraftAssessmentsView",
    # Organisation views
    "MyOrganisationView",
    "OrganisationContactView",
    "OrganisationTypeView",
    "ChangeActiveProfileView",
    # Workflow views
    "ViewSubmittedAssessmentsView",
]
