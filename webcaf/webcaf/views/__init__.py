from .account import AccountView, AccountViewAssessmentsView
from .assesment import (
    CreateAssessmentProfileView,
    CreateAssessmentSystemView,
    CreateAssessmentView,
    EditAssessmentProfileView,
    EditAssessmentSystemView,
    EditAssessmentView,
)
from .general import Index, logout_view
from .organisation import (
    ChangeActiveProfileView,
    MyOrganisationView,
    OrganisationContactView,
    OrganisationTypeView,
)

__all__ = [
    # Assessment views
    "EditAssessmentSystemView",
    "EditAssessmentProfileView",
    "CreateAssessmentSystemView",
    "CreateAssessmentProfileView",
    "EditAssessmentView",
    "CreateAssessmentView",
    # General views
    "logout_view",
    # Account views
    "Index",
    "AccountView",
    "AccountViewAssessmentsView",
    # Organisation views
    "MyOrganisationView",
    "OrganisationContactView",
    "OrganisationTypeView",
    "ChangeActiveProfileView",
    # Workflow views
]
