from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.db.transaction import atomic
from django.forms import ChoiceField, Form
from django.urls import reverse_lazy

from webcaf.webcaf.models import Assessor, Configuration, Review, UserProfile
from webcaf.webcaf.utils.permission import UserRoleCheckMixin
from webcaf.webcaf.utils.session import SessionUtil

"""
This module contains a mixin class for handling user role management in review-related views.
**Important**: This mixin should be used in all review-related views.
"""


class BaseReviewMixin(UserRoleCheckMixin):
    """
    Mixin providing base functionality for review-related user role management.

    The purpose of this class is to handle user access control for review-related
    features by enforcing and verifying role-based permissions.

    :ivar login_url: URL used for routing users to the appropriate login page for
        authentication.
    :type login_url: str
    """

    login_url = reverse_lazy("oidc_authentication_init")  # OIDC login route

    def get_allowed_roles(self) -> list[str]:
        return [
            "cyber_advisor",
            "organisation_lead",
            "reviewer",
            "assessor",
        ]

    def get_reviews_for_user(self, user_profile: UserProfile, configuration: Configuration) -> QuerySet[Review, Review]:
        """
        Retrieve reviews associated with a given user profile and configuration.

        This method fetches reviews from the database based on the user's role
        and the organisation's assessment period. It distinguishes between users
        holding certain roles (e.g., "organisation_lead", "cyber_advisor") and
        others, to filter assessments accordingly. The filtering criteria include
        the status of the assessment, whether the assessor is active, the
        organisation associated with the assessment system, and the current
        assessment period.

        :param user_profile: Represents the user's profile, containing information
            about roles and the organisation the user is associated with.
        :type user_profile: UserProfile
        :param configuration: Configuration settings, including methods to retrieve
            the current assessment period.
        :type configuration: Configuration
        :return: A queryset of reviews filtered according to the provided user profile
            and configuration.
        :rtype: QuerySet[Review, Review]
        """
        base_filter = Review.objects.filter(
            assessed_by__is_active=True,
            assessment__status__in=["submitted"],
            assessment__system__organisation=user_profile.organisation,
            assessment__assessment_period=configuration.get_current_assessment_period(),
        )
        if user_profile.role in ["organisation_lead", "cyber_advisor"]:
            return base_filter

        return base_filter.filter(
            assessed_by__in=Assessor.objects.filter(
                members=user_profile,
                organisation=user_profile.organisation,
            )
        )

    def get_queryset(self):
        configuration = Configuration.objects.get_default_config()
        return self.get_reviews_for_user(SessionUtil.get_current_user_profile(self.request), configuration)

    def get_object(self, queryset=None):
        """
        Retrieve and return a single object, ensuring additional access control logic is applied.

        This method fetches a single object using the parent implementation and then checks
        whether the current user has permissions to edit the object. It updates the object's
        attributes accordingly to indicate whether it is editable based on the user's role.

        :param queryset: Queryset used to fetch the object. Defaults to None.
        :type queryset: Optional[QuerySet]
        :return: The retrieved object with potential additional attributes for access control.
        :rtype: Any
        """
        obj = super().get_object(queryset)
        if obj:
            current_profile = SessionUtil.get_current_user_profile(self.request)
            # Set the editable flag here
            obj.can_edit = current_profile.role not in self.get_read_only_roles()
        return obj

    def get_read_only_roles(self):
        return ["organisation_lead"]

    @atomic
    def form_valid(self, form):
        """
        Handle form validation and save the form instance.

        This method overrides the default form_valid behavior to catch ValidationErrors
        raised by the Review model's save() method. If a ValidationError occurs, it adds
        the error message to the form and returns form_invalid.

        The Review model's save() method can raise ValidationErrors for:
        - Attempting to modify review_data on a completed review
        - Attempting to save when can_edit is False
        - Attempting to save when the data has been updated by another user (optimistic locking)

        :param form: The form instance to validate and save
        :type form: Form
        :return: Response redirecting to success_url or rendering form with errors
        :rtype: HttpResponse
        """
        try:
            return super().form_valid(form)
        except ValidationError as e:
            # Add the validation error to the form's non-field errors
            # ValidationError.messages contains the list of error messages
            if hasattr(e, "message"):
                form.add_error(None, e.message)
            else:
                # For ValidationErrors with multiple messages or dict-based errors
                for message in e.messages:
                    form.add_error(None, message)
            return self.form_invalid(form)


class YesNoForm(Form):
    """
    Represents a form for selecting Yes or No.
    """

    yes_no = ChoiceField(choices=[("yes", "Yes"), ("no", "No")], required=True, label="")

    def __init__(self, *args, **kwargs):
        yes_no_label = kwargs.pop("yes_no_label", "")
        super().__init__(*args, **kwargs)
        self.fields["yes_no"].initial = "no"
        self.fields["yes_no"].label = yes_no_label
