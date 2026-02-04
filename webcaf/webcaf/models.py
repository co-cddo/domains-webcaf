import logging
import typing
from datetime import datetime
from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Func, QuerySet, Value
from django.db.models.functions import Cast
from django.utils.timezone import make_aware
from django_otp.plugins.otp_email.models import EmailDevice
from multiselectfield import MultiSelectField
from simple_history.models import HistoricalRecords

from webcaf.webcaf.abcs import FrameworkRouter
from webcaf.webcaf.notification import send_notify_email
from webcaf.webcaf.utils import mask_email
from webcaf.webcaf.utils.references import generate_reference

# Set up a logger for any Notify errors
logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    # For historical review data type checking
    class HistoricalReview:
        review_type: str
        review_data: dict
        instance: "Review"


class ReferenceGeneratorMixin:
    """
    Mixin to automatically generate a unique reference for models.
    Requires a 'reference' field on the model.
    """

    def save(self, *args, **kwargs):
        if not self.reference:
            model_name = self.__class__.__name__.lower()
            if self.pk is None:
                super().save(*args, **kwargs)
                self.reference = generate_reference(self.pk, prime_set=model_name)
                super().save(update_fields=["reference"])
                return
            else:
                self.reference = generate_reference(self.pk, prime_set=model_name)
        super().save(*args, **kwargs)


class Organisation(ReferenceGeneratorMixin, models.Model):
    ORGANISATION_TYPE_CHOICES = sorted(
        [
            ("ad-hoc-advisory-group", "Ad-hoc advisory group"),
            ("advisory-non-departmental-public-body", "Advisory non-departmental public body"),
            ("agency-or-other-public-body", "Agency or other public body"),
            ("devolved-administration", "Devolved administration"),
            ("executive-agency", "Executive agency"),
            ("executive-non-departmental-public-body", "Executive non-departmental public body"),
            ("executive-office", "Executive office"),
            ("high-profile-group", "High profile group"),
            ("ministerial-department", "Ministerial department"),
            ("non-ministerial-department", "Non-ministerial department"),
            ("public-corporation", "Public corporation"),
            ("tribunal", "Tribunal"),
        ]
    ) + [("other", "Other")]
    name = models.CharField(max_length=255, unique=True)
    reference = models.CharField(max_length=20, null=True, unique=True)
    organisation_type = models.CharField(
        max_length=255, null=True, blank=True, choices=ORGANISATION_TYPE_CHOICES, default=None
    )
    contact_name = models.CharField(max_length=255, null=True, blank=True)
    contact_email = models.EmailField(null=True, blank=True)
    contact_role = models.CharField(max_length=255, null=True, blank=True)
    parent_organisation = models.ForeignKey(
        "self", on_delete=models.SET_NULL, related_name="sub_organisations", null=True, blank=True
    )

    history = HistoricalRecords()

    def __str__(self):
        return self.name

    @classmethod
    def get_type_id(cls, label):
        for type in cls.ORGANISATION_TYPE_CHOICES:
            if type[1] == label:
                return type[0]
        return None


class System(ReferenceGeneratorMixin, models.Model):
    CORPORATE_SERVICES = [
        ("email_and_communication", "Email and communication"),
        ("office_productivity", "Office productivity"),
        ("document_storage_and_management", "Document storage and management"),
        ("hr", "HR"),
        ("payroll", "Payroll"),
        ("financial_and_accounting", "Financial and accounting"),
        ("procurement_and_contract_management", "Procurement and contract management"),
        ("customer_relationship_management", "Customer relationship management"),
        ("help_desk_it_support", "Help desk / IT support"),
        ("data_management_analytics", "Data management / analytics"),
        ("other", "Other"),
    ]
    SYSTEM_TYPES = [
        (
            "directly_delivers_public_services",
            """It directly delivers public services""",
            """for example, Universal Credit""",
        ),
        (
            "supports_other_critical_systems",
            """It provides core infrastructure essential for other critical systems to function""",
            """for example, hosting platform or network, Active Directory""",
        ),
        (
            "is_critical_for_day_to_day_operations",
            """It provides corporate services or functions required for day-to-day operations for example, payroll""",
            """for example, Microsoft Office 365, telephony, corporate website""",
        ),
    ]
    OWNER_TYPES = [
        ("owned_by_organisation_being_assessed", """The organisation being assessed"""),
        ("owned_by_another_government_organisation", """Another government organisation"""),
        ("owned_by_third_party_company", """Third-party company"""),
    ]
    HOSTING_TYPES = [
        ("hosted_on_premises", "On-premises"),
        ("hosted_on_cloud", "Cloud hosted"),
        ("hosted_hybrid", "Hybrid"),
    ]
    ASSESSED_CHOICES = [
        ("assessed_in_2324", "Yes, in 2023/24"),
        ("assessed_in_2425", "Yes, in 2024/25"),
        ("assessed_in_2324_and_2425", "Yes, in both 2023/24 and 2024/25"),
        ("assessed_not_done", "No, it has not been assessed before"),
    ]
    name = models.CharField(max_length=255)
    reference = models.CharField(max_length=20, null=True, unique=True)
    description = models.TextField(null=True, blank=True)
    system_type = models.CharField(
        choices=[(s_type[0], s_type[1]) for s_type in SYSTEM_TYPES], null=True, blank=True, max_length=255
    )
    system_owner = MultiSelectField(choices=OWNER_TYPES, null=True, blank=True, max_length=255)
    hosting_type = MultiSelectField(choices=HOSTING_TYPES, null=True, blank=True, max_length=255)
    last_assessed = models.CharField(choices=ASSESSED_CHOICES, max_length=255, null=True, blank=True)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="systems")
    corporate_services = MultiSelectField(choices=CORPORATE_SERVICES, null=True, blank=True, max_length=255)
    corporate_services_other = models.CharField(max_length=100, blank=True, null=True)

    history = HistoricalRecords()

    class Meta:
        unique_together = ["name", "organisation"]

    def __str__(self):
        return self.name


class Assessment(ReferenceGeneratorMixin, models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    PROFILE_CHOICES = [
        (
            "baseline",
            "Baseline",
        ),
        (
            "enhanced",
            "Enhanced",
        ),
    ]
    FRAMEWORK_CHOICES = [
        ("caf32", "Cyber Assessment Framework v3.2"),
        ("caf40", "Cyber Assessment Framework v4.0"),
    ]

    REVIEW_TYPE_CHOICES = [
        ("independent", "Independent assurance review"),
        ("peer_review", "Peer review"),
        ("self_assessment", "No review, self-assessment only"),
        ("not_decided", "Not decided"),
    ]
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default="draft")
    system = models.ForeignKey(System, on_delete=models.CASCADE, related_name="assessments")
    reference = models.CharField(max_length=20, null=True, unique=True)
    framework = models.CharField(max_length=255, choices=FRAMEWORK_CHOICES, default="caf32")
    caf_profile = models.CharField(
        max_length=255,
        choices=PROFILE_CHOICES,
        default="baseline",
    )
    assessment_period = models.CharField(max_length=255)
    created_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    # This is calculated based on the current end date of the assessment period
    submission_due_date = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assessments_created"
    )
    last_updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assessments_updated"
    )
    assessments_data = models.JSONField(default=dict)

    review_type = models.CharField(max_length=255, choices=REVIEW_TYPE_CHOICES, default="not_decided")

    history = HistoricalRecords()

    class Meta:
        unique_together = ["assessment_period", "system", "status"]

    def get_section_by_outcome_id(self, outcome_id):
        """
        Retrieve a specific section of assessments data based on the provided outcome ID.

        The method looks up the `outcome_id` in the `assessments_data` attribute and
        returns the corresponding value if it exists. If the `outcome_id` is not found
        or `assessments_data` is not available, the method returns `None`.

        :param outcome_id: The unique identifier for the outcome to retrieve
        :type outcome_id: str
        :return: The section corresponding to the provided outcome_id, or None if not found
        :rtype: Any
        """
        if self.assessments_data:
            return self.assessments_data.get(outcome_id, None)
        return None

    def get_sections_by_objective_id(self, objective_id: str):
        """
        Retrieves and returns a list of assessment sections based on the provided
        objective ID. If the objective ID matches the beginning of a key within the
        assessments data, that key-value pair is included in the result. If no data
        exists or no matches are found, returns None.

        :param objective_id: The ID of the objective used to filter the assessment
            sections
        :type objective_id: str
        :return: A list of key-value tuples matching the objective ID, or None if no
            matches or data exist
        :rtype: list[tuple] | None
        """
        if self.assessments_data:
            return [(k, v) for k, v in self.assessments_data.items() if k.startswith(objective_id)]
        return None

    def get_router(self) -> FrameworkRouter:
        from webcaf.webcaf.frameworks import routers

        return routers[self.framework]

    def is_complete(self):
        """
        Check if all objectives are completed.

        :return: True if all objectives are completed, False otherwise
        """
        for objective in self.get_all_caf_objectives():
            objective_id = objective["code"]
            if not self.is_objective_complete(objective_id):
                return False
        return True

    def is_objective_complete(
        self,
        objective_id: str,
    ):
        """
        Checks if an objective is completed based on provided sections. An objective is considered complete
        if all its outcomes have a corresponding "confirmation" in the provided sections.

        :param objective_id: The unique identifier of the objective to check.
        :type objective_id: str
        :return: True if the objective is complete, otherwise False.
        :rtype: bool
        """
        sections = self.get_sections_by_objective_id(objective_id)
        if sections:
            objective = self.get_router().get_section(objective_id)
            if objective is None or "principles" not in objective:
                return False
            all_outcomes = [
                outcome["code"]
                for principle in objective["principles"].values()
                for outcome in principle["outcomes"].values()
            ]
            completed_outcomes = [
                completed_section[0]
                for completed_section in sections
                if
                # Only consider as complete if we have the confirm_outcome attribute in the confirmation
                "confirmation" in completed_section[1]
                and completed_section[1]["confirmation"].get("confirm_outcome", None) == "confirm"
            ]
            return set(all_outcomes) == set(completed_outcomes)
        return False

    def get_caf_outcome_by_id(self, objective_id: str, outcome_id: str):
        for objective in self.get_all_caf_objectives():
            if objective["code"] == objective_id:
                principal_code = outcome_id.split(".")[0]
                return objective["principles"][principal_code]["outcomes"][outcome_id]
        return None

    def get_caf_objective_by_id(self, objective_id: str):
        for objective in self.get_all_caf_objectives():
            if objective["code"] == objective_id:
                return objective
        return None

    def get_all_caf_objectives(self) -> list[dict]:
        return self.get_router().get_sections()

    def __str__(self):
        return f"reference={self.reference if self.reference else '-'}, status={self.status} org={self.system.organisation.name}"


class UserProfile(models.Model):
    ROLE_ACTIONS = {
        "organisation_lead": [
            "start a new self-assessment",
            "continue a draft self-assessment",
            "view self-assessments already sent for review",
            "add and remove organisation users",
        ],
        "organisation_user": ["continue a draft self-assessment", "view self-assessments already sent for review"],
        "reviewer": ["review a self-assessment", "create and edit a peer review report"],
        "assessor": ["review a self-assessment", "create and edit an IAR report"],
    }
    ROLE_DESCRIPTIONS = {
        "cyber_advisor": [
            "add new systems",
            "modify existing systems",
            "manage users within an organisation",
            "view self-assessments",
            "view Independent Assurance Reviews",
        ],
        "organisation_lead": [
            "start a new self-assessment",
            "continue a draft self-assessment",
            "view self-assessments already sent for review",
            "view Independent Assurance Reviews",
        ],
        "organisation_user": [
            "continue a draft self-assessment",
            "view self-assessments already sent for review",
        ],
        "assessor": [],
        "reviewer": [],
    }
    ROLE_CHOICES = [
        ("cyber_advisor", "GDS cyber advisor"),
        ("organisation_lead", "GovAssure lead"),
        ("organisation_user", "Organisation user"),
        ("reviewer", "Peer reviewer"),
        ("assessor", "Independent assurance reviewer"),
    ]
    # Do this rather than add a foreign key to Organisation, in case we need a many-to-many relationship later
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="profiles")
    organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE, related_name="members", null=True, blank=True
    )
    role = models.CharField(max_length=255, null=True, blank=True, choices=ROLE_CHOICES)

    history = HistoricalRecords()

    @classmethod
    def get_role_id(cls, role_name) -> str | None:
        for role in cls.ROLE_CHOICES:
            if role[1] == role_name:
                return role[0]
        return None

    @classmethod
    def get_role_label(cls, role_key) -> str | None:
        for role in cls.ROLE_CHOICES:
            if role[0] == role_key:
                return role[1]
        return None

    def __str__(self):
        return f"{self.user.email} - {self.organisation.name} - ({self.get_role_display()})"


class ConfigurationManager(models.Manager):
    def get_default_config(self):
        """
        Summary:
        Retrieves the default configuration based on the current date and time.
        This will check all existing configurations that have the assessment_period_end
        value that is greater than or equal to the current date and time, and pick
        the closest value to the current date+time.

        :return: The default configuration if found, otherwise None.
        """
        now = make_aware(datetime.now())
        # Annotate the model with a datetime parsed from JSON field
        qs = (
            self.get_queryset()
            .annotate(
                # Extract the key "assessment_period_end" from the JSON field and cast to text
                assessment_period_end_text=Cast(
                    F("config_data__assessment_period_end"), output_field=models.TextField()
                )
            )
            .annotate(
                # Remove the quotes from the string
                assessment_period_end_dt=Func(
                    Func(F("assessment_period_end_text"), Value('"'), Value(""), function="replace"),
                    Value("DD Month YYYY HH12:MIpm"),  # Adjust format to match your string
                    function="to_timestamp",
                    output_field=models.DateTimeField(),
                )
            )
        )

        # Filter configs where assessment_period_end >= now and get the earliest one
        default_config = qs.filter(assessment_period_end_dt__gte=now).order_by("assessment_period_end_dt").first()
        return default_config


class Configuration(models.Model):
    config_data = models.JSONField(default=dict)
    name = models.CharField(max_length=255, unique=True)
    # custom manager to get the default config
    objects = ConfigurationManager()

    def get_current_assessment_period(self):
        return self.config_data.get("current_assessment_period")

    def get_assessment_period_end(self):
        return self.config_data.get("assessment_period_end")

    def get_default_framework(self):
        return self.config_data.get("default_framework")

    def get_submission_due_date(self):
        """
        Convert the get_assessment_period_end in to a datetime object.
        The format is 31 March 2026 11:59pm.
        :return:
        """
        assessment_period_end = self.get_assessment_period_end()
        # Parse the date string in format "31 March 2026 11:59pm"
        return make_aware(datetime.strptime(assessment_period_end, "%d %B %Y %I:%M%p"))

    def __str__(self):
        return self.name


class GovNotifyEmailDevice(EmailDevice):
    """
    A proxy model for ``django_otp.plugins.otp_email.models.EmailDevice``.

    This subclass overrides the token sending mechanism to use the
    GOV.UK Notify service instead of Django's built-in email backend,
    which is configurable via settings.
    """

    def send_mail(self, token, **kwargs):
        """
        Overrides the default ``send_mail`` method to send the OTP token.

        This method is called by django-otp's ``generate_challenge`` after
        a token is generated.

        If ``settings.SSO_MODE`` is not set to "external", it falls back
        to the parent class's ``send_mail`` method (which typically prints
        the token to the console in development).

        If ``settings.SSO_MODE`` is "external", it attempts to send the
        token using the GOV.UK Notify API. Any exceptions during this
        process are caught and logged, preventing a hard failure.

        :param token: The one-time password (OTP) token to be sent.
        :type token: str
        :param **kwargs: Arbitrary keyword arguments passed from the
                         calling method. Not used in this implementation.
        """
        # if not external sso mode then we can print the token in the console for
        # local development
        if not settings.SSO_MODE == "external":
            logger.debug("SSO_MODE is not 'external'. Using default send_mail.")
            return super().send_mail(token, **kwargs)

        try:
            personalisation_data = {
                "token": token,
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
            }
            send_notify_email([self.email], personalisation_data, settings.NOTIFY_OTP_TEMPLATE_ID)
            logger.info(mask_email(f"GOV.UK Notify: Successfully sent OTP to {self.email}"))
        except Exception as e:
            logger.exception(mask_email(f"GOV.UK Notify: Failed to send OTP to {self.email}: {e}"))
            pass

    class Meta:
        """
        Meta options for the GovNotifyEmailDevice model.

        ``proxy = True`` ensures that this model does not create its own
        database table. Instead, it operates on the existing
        ``otp_email_emaildevice`` table from the ``django-otp`` app.
        """

        proxy = True


def _get_or_create_nested_path(current: dict[str, Any], *keys) -> dict:
    """
    Ensures a nested path exists in review_data by creating intermediate dicts as needed.
    :param current: The current dict in which to create the nested path
    :param keys: Variable number of string keys representing the nested path
    :return: The innermost dict at the specified path
    """
    for key in keys:
        if not current.get(key):
            current[key] = {}
        current = current[key]
    return current


class Review(ReferenceGeneratorMixin, models.Model):
    """
    Represents a review entity that ties an assessment to its review process.

    This class facilitates the tracking, management, and organization of review processes
    associated with an assessment. It records review metadata (in review_data), links to related entities
    like assessments and assessors, and provides mechanisms to manage and retrieve nested
    data tied to reviews. The class also includes functionality to manage statuses and ensure
    organizational and assessor details confirmation.

    :ivar created_on: Timestamp of when the review was created.
    :type created_on: datetime.datetime
    :ivar last_updated: Timestamp of when the review was last updated.
    :type last_updated: datetime.datetime
    :ivar last_updated_by: The user who last updated the review.
    :type last_updated_by: User
    :ivar status: The current status of the review. Possible values are:
        "to_do", "in_progress", "clarify", "completed", and "cancelled".
    :type status: str
    :ivar review_data: A JSON field storing various data about the review, including nested data.
    :type review_data: dict
    :ivar reference: A unique reference identifier for the review.
    :type reference: str
    :ivar assessment: The associated assessment object for this review. If the assessment
        is deleted, the review is also deleted.
    :type assessment: Assessment
    """

    STATUS_CHOICES = [
        ("to_do", "To do"),
        ("in_progress", "In-progress"),
        ("clarify", "Clarify"),
        ("completed", "Closed"),
        ("cancelled", "Cancelled"),
    ]
    created_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="to_do")
    review_data = models.JSONField(default=dict, null=False, blank=True)
    reference = models.CharField(max_length=20, null=True, unique=True)

    # If the assessment is deleted, then we delete the review
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="reviews")

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_on"]
        unique_together = [
            "assessment",
        ]

    def __init__(self, *args, **kwargs):
        """
        Initializes an instance of the class, inheriting from its superclass. It performs
        default initialization and stores the original value of `last_updated` if the
        object already exists (has a primary key).

        :param args: Positional arguments passed to the superclass constructor.
        :param kwargs: Keyword arguments passed to the superclass constructor.
        """
        super().__init__(*args, **kwargs)
        self._original_last_updated = self.last_updated if self.pk else None

    def refresh_from_db(
        self,
        using: str | None = None,
        fields: typing.Iterable[str] | None = None,
        from_queryset: QuerySet[typing.Self] | None = None,
    ):
        """
        Reloads the instance from the database and updates the _original_last_updated
        timestamp to reflect the current state from the database.

        This ensures that the optimistic locking check in the save method works correctly
        after a refresh_from_db() call.

        :param using: The database alias to use (optional)
        :param fields: List of field names to refresh (optional)
        :return: None
        """
        super().refresh_from_db(using=using, fields=fields)
        self._original_last_updated = self.last_updated if self.pk else None

    def __str__(self):
        return f"review_id={self.id} assessment={self.assessment}"

    def get_initial_data(self):
        return (
            {
                # General
                "reference": self.assessment.reference,
                "organisation": self.assessment.system.organisation.name,
                "assessment_period": self.assessment.assessment_period,
                # System attributes
                "system_name": self.assessment.system.name,
                "system_description": self.assessment.system.description,
                "prev_assessments": self.assessment.system.last_assessed,
                "hosting_and_connectivity": self.assessment.system.hosting_type,
                "corporate_services": self.assessment.system.corporate_services,
            },
            {
                "review_type": self.assessment.review_type,
                "framework": self.assessment.framework,
                "profile": self.assessment.caf_profile,
            },
        )

    @property
    def is_system_and_scope_completed(self):
        assessor_response_data = self.get_assessor_response()
        system_scope = _get_or_create_nested_path(assessor_response_data, "system_and_scope")
        return system_scope.get("completed") == "yes"

    def confirm_system_and_scope_completed(self, completed_data: dict[str, Any]):
        """
        Confirms the completion of the system and scope section by updating the
        appropriate data path with the completion status and provided completion
        details.

        :param completed_data: A dictionary containing the details of the completed
            data for the system and scope section.
        :type completed_data: dict[str, Any]
        :return: None
        """
        assessor_response_data = self.get_assessor_response()
        system_scope = _get_or_create_nested_path(assessor_response_data, "system_and_scope")
        system_scope["completed"] = "yes"
        system_scope["completed_data"] = completed_data

    def reset_system_and_scope_completed(self):
        """
        Reset the "completed" flag within the "system_and_scope" section of the
        assessor response. This method retrieves the assessor response data,
        accesses the "system_and_scope" nested path, and removes the "completed"
        attribute.

        :raises KeyError: If the "completed" key does not exist in the
            "system_and_scope" section.
        :return: None
        """
        assessor_response_data = self.get_assessor_response()
        system_scope = _get_or_create_nested_path(assessor_response_data, "system_and_scope")
        if system_scope:
            system_scope.pop("completed", None)

    def record_assessor_action(self, action_type: str, action_details: dict[str, Any]):
        assessor_response_data = self.get_assessor_response()
        assessor_actions = _get_or_create_nested_path(assessor_response_data, "assessor_actions")
        if "records" not in assessor_actions:
            assessor_actions["records"] = []
        assessor_actions["records"].append(
            {
                "type": action_type,
                "details": action_details,
            }
        )

    def set_outcome_review(self, objective_code: str, outcome_code: str, data: dict[str, Any]):
        """
        Updates the assessment review data and indicators for a specific outcome within an objective.

        :param objective_code: The identifier for the objective.
        :type objective_code: str
        :param outcome_code: The identifier for the outcome within the objective.
        :type outcome_code: str
        :param data: A dictionary containing data for review and indicators. Keys starting
            with "review_" are used as review data, while all other keys are treated
            as indicator data.
        :type data: dict[str, Any]
        :return: None
        """
        assessor_response_data = self.get_assessor_response()
        outcome_section = _get_or_create_nested_path(assessor_response_data, objective_code, outcome_code)
        # Split the data in to review and indicator data for visual clarity
        review_data = {k: v for k, v in data.items() if k.startswith("review_")}
        indicator_data = {k: v for k, v in data.items() if not k.startswith("review_")}
        outcome_section["indicators"] = indicator_data
        outcome_section["review_data"] = review_data

    def get_outcome_review(
        self,
        objective_code: str,
        outcome_code: str,
    ) -> dict[str, Any]:
        """
        Fetches the review data for a specified outcome within a given objective.

        This method retrieves assessor response data and uses a nested path to access
        or create the specified outcome section for the given objective code.
        It then consolidates indicator data and review data found in the outcome
        section.

        :param objective_code: Unique identifier for the objective.
        :param outcome_code: Unique identifier for the outcome within the objective.
        :return: A dictionary containing a merged set of indicator and review data.
        :rtype: dict[str, Any]
        """
        assessor_response_data = self.get_assessor_response()
        outcome_section = _get_or_create_nested_path(assessor_response_data, objective_code, outcome_code)
        return outcome_section.get("indicators", {}) | outcome_section.get("review_data", {})

    def get_outcome_recommendations(
        self,
        objective_code: str,
        outcome_code: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieves a list of outcome recommendations based on the provided objective code and outcome code.
        The method accesses assessor response data and navigates to the relevant outcome section
        to fetch the recommendations. Recommendations are returned as a list of dictionaries.

        :param objective_code: A string representing the objective code used to locate the specific objective.
        :param outcome_code: A string representing the outcome code defining the target outcome within the objective.
        :return: A list of dictionaries containing recommendations for the specified outcome.
        """
        assessor_response_data = self.get_assessor_response()
        outcome_section = _get_or_create_nested_path(assessor_response_data, objective_code, outcome_code)
        return outcome_section.get("recommendations", [])

    def set_outcome_recommendations(self, objective_code: str, outcome_code: str, comments=list[dict[str, Any]]):
        """
        Sets outcome recommendations for the given objective and outcome codes within
        the assessor response data. This method ensures a nested path exists for the
        specified objective and outcome codes and then updates the "recommendations"
        section with the provided comments.

        The assessor response data is retrieved and updated accordingly, ensuring
        a structured approach to organizing recommendations based on objectives
        and outcomes.

        :param objective_code: The code representing the objective to be updated.
        :type objective_code: str
        :param outcome_code: The code representing the specific outcome to be updated.
        :type outcome_code: str
        :param comments: A list of dictionaries, where each dictionary contains
            recommendation details to be added to the specified outcome.
        :type comments: list[dict[str, Any]]
        :return: None
        """
        assessor_response_data = self.get_assessor_response()
        outcome_section = _get_or_create_nested_path(assessor_response_data, objective_code, outcome_code)
        outcome_section["recommendations"] = comments

    def get_objective_comments(self, objective_code: str, category: str) -> str | None:
        """
        Retrieve comments for a specific objective under a given category. The method accesses
        assessment response data, navigates to the relevant section based on the provided objective
        code, and attempts to retrieve comments associated with the specified category.

        :param objective_code: The identifier string for the specific objective.
        :param category: The category within the objective code from which to fetch the comments.
        :return: A string representing the comments for the specific category, or None if the
                 category does not exist.
        """
        assessor_response_data = self.get_assessor_response()
        outcome_section = _get_or_create_nested_path(assessor_response_data, objective_code)
        return outcome_section.get(category, None)

    def is_objective_complete(self, objective_code: str) -> bool:
        """
        Evaluates whether a specific objective has been fully completed based on its review data
        and associated recommendations. This method inspects the data for key components such as
        recommendations, areas for improvement, areas of good practice, and the status of associated
        outcomes for an objective, determining if all required conditions are met.

        :param objective_code: The code that uniquely identifies the objective to be checked.
        :type objective_code: str
        :return: A boolean indicating whether the objective has been completely achieved. Returns
                 True if all required checks pass, otherwise False.
        :rtype: bool
        """
        assessor_response_data = self.get_assessor_response()
        review_objective = _get_or_create_nested_path(assessor_response_data, objective_code)
        caf_objective = self.assessment.get_caf_objective_by_id(objective_code)
        for principal in caf_objective["principles"].values():
            # Objective level key check.
            if not {"objective-areas-of-improvement", "objective-areas-of-good-practice"}.issubset(
                review_objective.keys()
            ):
                return False
            for outcome in principal["outcomes"].values():
                outcome_data = review_objective.get(outcome["code"], {})
                # Outcome level check
                # if the status is not present or not achieved state, then
                # we need recommendations
                if review_decision := outcome_data.get("review_data", {}).get("review_decision"):
                    if (
                        not review_decision
                        or review_decision != "achieved"
                        and not outcome_data.get("recommendations", [])
                    ):
                        return False
                else:
                    return False
        return True

    def is_all_objectives_complete(self):
        """
        Checks whether all objectives associated with the assessment are complete.

        This method retrieves all the CAF (Capability Assessment Framework) objectives
        associated with the current assessment and checks their completion status. If
        any objective is not complete, the method returns False; otherwise, it returns
        True.

        :return: Indicates whether all objectives are complete
        :rtype: bool
        """
        caf_objectives = self.assessment.get_all_caf_objectives()
        for objective in caf_objectives:
            if not self.is_objective_complete(objective["code"]):
                return False
        return True

    def is_system_and_scope_complete(self):
        assessor_response_data = self.get_assessor_response()
        return assessor_response_data.get("system_and_scope", {}).get("completed") == "yes"

    def is_iar_period_complete(self) -> bool:
        return self.get_additional_detail("iar_period") is not None

    def is_quality_of_evidence_complete(self) -> bool:
        return self.get_additional_detail("quality_of_evidence") is not None

    def is_review_method_complete(self) -> bool:
        return self.get_additional_detail("review_method") is not None

    def is_company_details_complete(self) -> bool:
        return self.get_additional_detail("company_details") is not None

    def get_additional_detail(self, detail_key) -> str | None:
        """
        Retrieve additional detail from the 'additional_information' field in the assessor's
        response data using the provided detail key.

        This method accesses the nested path 'additional_information' within the assessor's
        response data, ensuring the path exists or is created. It then extracts the detail
        corresponding to the given detail key. If the key is not present, it returns None.

        :param detail_key: The key corresponding to the required detail within the
            'additional_information' data.
        :type detail_key: str
        :return: The detail corresponding to the provided key or None if the key
            is not found.
        :rtype: str | None
        """
        assessor_response_data = self.get_assessor_response()
        additional_information = _get_or_create_nested_path(assessor_response_data, "additional_information")
        return additional_information.get(detail_key, None)

    def set_additional_detail(self, detail_key, detail_value):
        """
        Sets an additional detail in the nested structure of the assessor response data under
        the "additional_information" path. This method modifies the nested dictionary
        by adding a new key-value pair, where `detail_key` serves as the key and
        `detail_value` as its corresponding value.

        :param detail_key: Key to identify the additional detail within the nested
                           "additional_information" structure
        :type detail_key: str
        :param detail_value: Value corresponding to the provided `detail_key` to
                             be added to the "additional_information" structure
        :type detail_value: Any
        :return: None
        """
        assessor_response_data = self.get_assessor_response()
        additional_information = _get_or_create_nested_path(assessor_response_data, "additional_information")
        additional_information[detail_key] = detail_value

    def is_ready_to_submit(self) -> bool:
        """
        Evaluates whether all necessary components are completed to determine readiness for submission.

        This method checks the completion status of several required components, including
        objectives, system and scope, IAR period, quality of evidence, and review methods.
        Readiness is determined by ensuring all these components meet their completion criteria.

        :return: A boolean indicating if all components are completed and ready for submission.
        :rtype: bool
        """
        return (
            self.is_all_objectives_complete()
            and self.is_system_and_scope_complete()
            and self.is_iar_period_complete()
            and self.is_quality_of_evidence_complete()
            and self.is_review_method_complete()
            and self.is_company_details_complete()
        )

    def get_completed_outcomes_info(self):
        assessor_response_data = self.get_assessor_response()
        caf_objectives = self.assessment.get_all_caf_objectives()
        total_outcomes = 0
        completed_outcomes = 0
        for caf_objective in caf_objectives:
            review_objective = _get_or_create_nested_path(assessor_response_data, caf_objective["code"])
            for principal in caf_objective["principles"].values():
                for outcome in principal["outcomes"].values():
                    outcome_data = review_objective.get(outcome["code"], {})
                    # Outcome level check
                    # if the status is not present or not achieved state, then
                    # we need recommendations
                    total_outcomes += 1
                    if review_decision := outcome_data.get("review_data", {}).get("review_decision"):
                        if review_decision and (review_decision == "achieved" or outcome_data.get("recommendations")):
                            completed_outcomes += 1

        return {"total_outcomes": total_outcomes, "completed_outcomes": completed_outcomes}

    def set_objective_comments(self, objective_code: str, category: str, comment: str):
        """
        This method updates or sets comments for a specific objective code and its associated
        category within an assessor response data structure. It ensures that the data is
        appropriately nested in the response if not already present.

        :param objective_code: A string representing the unique identifier for the specific
                               objective within the assessor's response.
        :param category: A string denoting the category under the objective code in which
                         the comment is being added or updated.
        :param comment: A string containing the actual comment to be added or updated
                        under the specified objective code and category.
        :return: None
        """
        assessor_response_data = self.get_assessor_response()
        outcome_section = _get_or_create_nested_path(assessor_response_data, objective_code)
        outcome_section[category] = comment

    def get_assessor_response(self):
        """
        Retrieves assessor response data from the review data.

        This method extracts and returns the "assessor_response_data" from the
        `review_data` dictionary. If the "assessor_response_data" key does not exist
        in the dictionary, an empty dictionary is returned.

        :rtype: dict
        :return: A dictionary containing the assessor data or an empty
                 dictionary if the key "assessor_response_data" is not present.
        """
        return _get_or_create_nested_path(self.review_data, "assessor_response_data")

    def mark_review_complete(self, profile: UserProfile):
        if self.status == "in_progress":
            review_completion = _get_or_create_nested_path(self.review_data, "review_completion")
            review_completion["review_completed"] = "yes"
            review_completion["review_completed_at"] = datetime.now().isoformat()
            review_completion["review_completed_by"] = profile.user.first_name + " " + profile.user.last_name
            review_completion["review_completed_by_email"] = profile.user.email
            review_completion["review_completed_by_role"] = profile.role
            self.status = "completed"
        else:
            raise ValidationError("Invalid state for report creation.")

    def is_review_complete(self):
        review_completion = _get_or_create_nested_path(self.review_data, "review_completion")
        return review_completion.get("review_completed") == "yes" and self.status == "completed"

    def is_review_finalised(self):
        review_finalised = _get_or_create_nested_path(self.review_data, "review_finalised")
        return self.is_review_complete() and review_finalised

    @property
    def completion_info(self) -> dict | None:
        """
        Retrieves the review completion information from the assessor response.

        This method accesses the assessor response data and attempts to extract
        the value associated with the 'review_completion' key. If the key is not
        present, the method returns None.

        :return: The value of the "review_completion" key from assessor response
            data, or None if the key does not exist.
        :rtype: dict | None
        """
        review_completion: dict | None = self.review_data.get("review_completion", None)
        if review_completion is not None:
            if completed_at := review_completion.get("review_completed_at"):
                if type(completed_at) is str:
                    review_completion["review_completed_at"] = datetime.strptime(completed_at, "%Y-%m-%dT%H:%M:%S.%f")
        return review_completion

    def reopen(self):
        """
        Reopens a report if the current status is not "completed", transitioning it to
        an "in_progress" state and resetting certain review data.

        This method ensures that reopening the report is only allowed when the
        current status is not marked as "completed". Upon reopening, related review
        data is cleared to allow for new assessment updates.

        :raises ValidationError: When the report status is already "completed".

        :return: Updates the report status and clears specific review data for further
                 reassessment.
        """
        if self.status != "completed" or self.is_review_finalised():
            raise ValidationError("Invalid state for report reopening.")

        review_completion = _get_or_create_nested_path(self.review_data, "review_completion")
        self.status = "in_progress"
        # Remove the review_completed key and its associated values
        review_completion.clear()

    def finalise_review(self, profile: UserProfile):
        if self.status != "completed":
            raise ValidationError("Invalid state for report finalising.")

        review_completion = _get_or_create_nested_path(self.review_data, "review_finalised")
        # Add the finalised timestamp
        review_completion["review_finalised_at"] = datetime.now().isoformat()
        review_completion["review_finalised_by"] = f"{profile.user.first_name} {profile.user.last_name}"
        review_completion["review_finalised_by_email"] = profile.user.email
        review_completion["review_finalised_by_role"] = profile.role

    def save(self, *args, **kwargs):
        """
        Saves the current state of the instance to the database. This method overrides
        the default `save` behavior to perform additional validation before the model
        instance is saved. Specifically, it ensures that the `review_data` field cannot
        be modified if the `status` field is already marked as "completed".

        This also checks for the can_edit attribute on the object.
        If present, it will make sure the value is set to true before
        saving the object.

        :param args: Positional arguments to pass to the superclass's `save` method.
        :param kwargs: Keyword arguments to pass to the superclass's `save` method.
        :return: None
        """
        if self.pk:
            old = Review.objects.get(pk=self.pk)
            # Prevent changing review_data if the status was already "completed"
            # This allows the addition of finalised review data to the json
            # while it is still in the completed state
            if (old.status == "completed" and "completed" == self.status) and (
                self.review_data.get("review_completion", {}) != old.review_data.get("review_completion", {})
                or self.review_data.get("assessor_response_data", {})
                != old.review_data.get("assessor_response_data", {})
                or old.is_review_finalised()
            ):
                raise ValidationError("Review data cannot be changed after it has been marked as completed.")

            # If we have specifically added permissions for this object, then we should check that
            if hasattr(self, "can_edit") and not getattr(self, "can_edit"):
                raise ValidationError("You do not have permission to edit this report.")

            if hasattr(self, "_original_last_updated") and getattr(self, "_original_last_updated"):
                if old.last_updated != getattr(self, "_original_last_updated"):
                    raise ValidationError("Your copy of data has been updated since you last saved it.")

        super().save(*args, **kwargs)
        # Update _original_last_updated to the new last_updated value after successful save
        self._original_last_updated = self.last_updated

    @property
    def current_version_number(self) -> int | None:
        """
        Calculate and return the total number of versions if `all_versions` exists.

        This property provides the count of all available versions or returns None
        if `all_versions` is not available or empty.

        :return: The number of versions as an integer or None if no versions exist.
        :rtype: int | None
        """
        all_versions = self.all_versions
        return len(all_versions) if all_versions else None

    @property
    def current_version(self) -> typing.Optional["HistoricalReview"] | None:
        """
        Property that retrieves the most recent version of a historical review
        if any versions exist. If there are no versions, it returns None.

        Returns the first item in the list of all versions as it represents
        the most current version based on the assumption that all_versions
        are sorted by recency in descending order.

        :return: The most current version of the historical review or None if no
            versions are available.
        :rtype: typing.Optional[HistoricalReview] | None
        """
        all_versions = self.all_versions
        return all_versions[0] if all_versions else None

    @property
    def all_versions(self) -> list["HistoricalReview"]:
        """
        Retrieve all unique historical versions of a review in reverse chronological order.
        A new version is considered for inclusion only if it has a status of "completed" and
        either the list is currently empty or its contents differ from the last added version.

        :return: A list of unique historical review versions with a status of "completed"
                 in reverse chronological order.
        :rtype: list[HistoricalReview]

        """
        versions: list["HistoricalReview"] = []
        full_history = self.history.filter(status="completed").order_by("-last_updated").all()
        for version in full_history:
            if (
                # No versions in the list, so the first submitted we find is the latest version
                not versions
                # There could be other filed changes recorded, so only pick the next
                # submitted if the contents are different
                or version.instance.get_assessor_response() != versions[-1].instance.get_assessor_response()
            ):
                versions.append(version)
        return versions

    def get_version(self, version_number: int) -> typing.Optional["HistoricalReview"]:
        """
        Retrieves a historical review based on the given version number.

        This method is used to access a specific version of a historical review. It
        returns the review corresponding to the provided version number, or None if no
        historical versions exist.

        :param version_number: The version number of the historical review to retrieve.
        :type version_number: int
        :return: The historical review matching the given version number, or None if no
            versions are available.
        :rtype: typing.Optional["HistoricalReview"]
        """
        return (
            # We have the latest version as the 0th index,
            # So, we have to do a reverse lookup
            list(reversed(self.all_versions))[version_number - 1]
            if self.all_versions and version_number > 0 and version_number - 1 < len(self.all_versions)
            else None
        )
