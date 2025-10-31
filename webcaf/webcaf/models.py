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
        ("procurement_and_contract_management", "Procurement and contract management"),
        ("customer_relationship_management", "Customer relationship management"),
        ("help_desk_it_support", "Help desk / IT support"),
        ("data_management_analytics", "Data management / analytics"),
        ("none", "None of the above"),
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
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default="Draft")
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
        return f"reference={self.reference if self.reference else '-'}, id={self.id}"


class UserProfile(models.Model):
    ROLE_ACTIONS = {
        "organisation_lead": [
            "start a new self-assessment",
            "continue a draft self-assessment",
            "view self-assessments already sent for review",
            "add and remove organisation users",
        ],
        "organisation_user": ["continue a draft self-assessment", "view self-assessments already sent for review"],
    }
    ROLE_DESCRIPTIONS = {
        "cyber_advisor": """On this page you can add new systems, modify existing systems and manage users within an
                    organisation.""",
        "organisation_lead": """On this page you can manage users within an
                    organisation, continue a draft self-assessment and view self-assessments already sent for review.""",
        "organisation_user": "On this page you can continue a draft self-assessment and view self-assessments already sent for review.",
    }
    ROLE_CHOICES = [
        ("cyber_advisor", "GDS cyber advisor"),
        ("organisation_lead", "Organisation lead"),
        ("organisation_user", "Organisation user"),
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
