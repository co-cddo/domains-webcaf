from .assesment_views import (
    CreateAssessmentProfileView,
    CreateAssessmentSystemView,
    CreateAssessmentView,
    EditAssessmentProfileView,
    EditAssessmentSystemView,
    EditAssessmentView,
)
from .general_views import logout_view
from .my_account import Index, MyAccountView, MyAccountViewAssessmentsView
from .my_organisation import (
    ChangeActiveProfileView,
    MyOrganisationView,
    OrganisationContactView,
    OrganisationTypeView,
)
from .workflow_views import OutcomeIndicatorsHandlerView

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
    "MyAccountView",
    "MyAccountViewAssessmentsView",
    # Organisation views
    "MyOrganisationView",
    "OrganisationContactView",
    "OrganisationTypeView",
    "ChangeActiveProfileView",
    # Workflow views
    "OutcomeIndicatorsHandlerView",
]
