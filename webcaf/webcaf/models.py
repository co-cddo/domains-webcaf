import logging
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import F, Func, Value
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
        for objective in self.get_router().get_sections():
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
        "assessor": ["view self-assessments already sent for review"],
        "reviewer": ["view self-assessments already sent for peer-review"],
    }
    ROLE_DESCRIPTIONS = {
        "cyber_advisor": """On this page you can add new systems, modify existing systems and manage users within an
                    organisation.""",
        "organisation_lead": """On this page you can manage users within an
                    organisation, continue a draft self-assessment and view self-assessments already sent for review.""",
        "organisation_user": "On this page you can continue a draft self-assessment and view self-assessments already sent for review.",
        "assessor": "On this page you can view self-assessments already sent for review.",
        "reviewer": "On this page you can view self-assessments already sent for peer-review.",
    }
    ROLE_CHOICES = [
        ("cyber_advisor", "GDS cyber advisor"),
        ("organisation_lead", "Organisation lead"),
        ("organisation_user", "Organisation user"),
        ("assessor", "Independent assessor"),
        ("reviewer", "Peer reviewer"),
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


class Assessor(ReferenceGeneratorMixin, models.Model):
    """
    Represents an Assessor entity with the following attributes:

    This class is used to model the details of an assessor (independent/peer), including their contact
    information, type, and associations with organizations and members.

    Only UserProfiles with the role "assessor" and "reviewer" are allowed to be associated as members of this assessor.
    This is enforced in the view layer. Also, it is validated that the members belong to the same organisation as
    the assessor.

    When an assessor is deleted, we only soft-delete the entry by setting the is_active attribute to False.

    The class inherits from ReferenceGeneratorMixin to generate a unique reference identifier for each assessor.


    :ivar is_active: Indicates whether the assessor is active.
    :type is_active: bool
    :ivar phone_number: The phone number of the assessor.
    :type phone_number: str
    :ivar contact_name: The name of the contact person for the assessor.
    :type contact_name: str
    :ivar email: The email address of the assessor.
    :type email: str
    :ivar address: The address of the assessor.
    :type address: str
    :ivar name: The name of the assessor.
    :type name: str
    :ivar assessor_type: The type of the assessor, chosen from predefined options.
    :type assessor_type: str
    :ivar last_updated: The timestamp indicating the last update to the record.
    :type last_updated: datetime
    :ivar created_on: The timestamp indicating when the record was created.
    :type created_on: datetime
    :ivar last_updated_by: The user who last updated the record.
    :type last_updated_by: User or None
    :ivar reference: A unique reference identifier for the assessor.
    :type reference: str
    :ivar history: Historical records of the assessor's changes.
    :type history: HistoricalRecords
    :ivar organisation: The organization associated with the assessor.
    :type organisation: Organisation
    :ivar members: The user profiles associated as members under this assessor.
    :type members: ManyToManyField
    """

    ASSESSOR_TYPES = [("independent", "Independent assurance review"), ("peer", "Peer review")]

    is_active = models.BooleanField(default=True)
    phone_number = models.CharField(max_length=255, null=True, blank=True)
    contact_name = models.CharField(max_length=255, null=False, blank=False, default=None)
    email = models.EmailField(max_length=255, null=False, blank=False)
    address = models.TextField(null=False, blank=False)
    name = models.CharField(max_length=255, null=False, blank=False)
    assessor_type = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        choices=ASSESSOR_TYPES,
        default=None,
    )

    last_updated = models.DateTimeField(auto_now=True)
    created_on = models.DateTimeField(auto_now_add=True)
    last_updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reference = models.CharField(max_length=20, null=True, unique=True)
    history = HistoricalRecords()

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="assessors")
    members = models.ManyToManyField(UserProfile, related_name="member_of")

    def __str__(self):
        return f"name={self.name}, email={self.email}, contact_name={self.contact_name}"

    def contact_details(self):
        return f"""{self.name}
                    {self.contact_name}
                    {self.phone_number}
                    {self.email}
                """


class Review(ReferenceGeneratorMixin, models.Model):
    """
    Represents a review entity that ties an assessment to a specific assessor for purposes
    such as evaluations, reports, or clarifications.

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
    :ivar assessed_by: The assessor associated with this review. If the assessor is removed,
        the reference to the assessor in this review will be nullified.
    :type assessed_by: Assessor
    """

    STATUS_CHOICES = [
        ("to_do", "To do"),
        ("in_progress", "In review"),
        ("clarify", "Clarify"),
        ("completed", "Report generated"),
        ("cancelled", "Cancelled"),
    ]
    created_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="to_do")
    review_data = models.JSONField(default=dict, null=False, blank=True)
    reference = models.CharField(max_length=20, null=True, unique=True)

    # This is assuming that an organisation can commission more than one assessor to review
    # a given system. If the assessment is deleted, then we delete the review
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="reviews")
    assessed_by = models.ForeignKey(
        Assessor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_on"]
        unique_together = [
            "assessment",
            "assessed_by",
        ]

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
                "assessor": self.assessed_by.contact_details() if self.assessed_by else "",
            },
        )

    def set_initial_data(self):
        self.review_data["system_details"], self.review_data["assessor_details"] = self.get_initial_data()

    def save(self, *args, **kwargs):
        is_create = self.pk is None
        # Only populate initial data on creation and when status is 'to_do'.
        if is_create and self.status == "to_do":
            # Ensure review_data is a dict
            if not isinstance(self.review_data, dict):
                self.review_data = {}
            # Populate only if not already provided
            if "system_details" not in self.review_data and "assessor_details" not in self.review_data:
                self.set_initial_data()
        super().save(*args, **kwargs)

    @property
    def is_org_details_confirmed(self) -> bool:
        """
        Determines if the organization details are complete based on the system's responses.

        The method checks whether the 'status_confirmed' value under 'organisation_details'
        in the 'system_details' section of the assessor's response is set to "confirm".
        It returns True if the organization details are complete, otherwise False.

        :return: True if the organization details are marked as complete ("confirm"),
            otherwise False
        :rtype: bool
        """
        return (
            self._get_or_crearte_nested_path(
                "assessor_response_data",
                "system_details",
                "organisation_details",
            ).get("status_confirmed", None)
            == "confirm"
        )

    def confirm_org_details(self):
        org_details = self._get_or_crearte_nested_path(
            "assessor_response_data", "system_details", "organisation_details"
        )
        org_details["status_confirmed"] = "confirm"

    @property
    def is_assessor_details_confirmed(self) -> bool:
        """
        Determines if assessor details are complete.

        This method checks whether the assessor's details have been confirmed by
        evaluating the "status_confirmed" key within the nested dictionary structure
        returned by the method `get_assessor_response`. The status is considered
        complete when its value is equal to "confirm".

        :return: True if the assessor details are marked as confirmed, otherwise False
        :rtype: bool
        """
        return (
            self._get_or_crearte_nested_path("assessor_response_data", "system_details", "assessor_details").get(
                "status_confirmed", None
            )
            == "confirm"
        )

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
        return self._get_or_crearte_nested_path("assessor_response_data")

    def _get_or_crearte_nested_path(self, *keys) -> dict:
        """
        Ensures a nested path exists in review_data by creating intermediate dicts as needed.

        :param keys: Variable number of string keys representing the nested path
        :return: The innermost dict at the specified path
        """
        current = self.review_data
        for key in keys:
            if not current.get(key):
                current[key] = {}
            current = current[key]
        return current
