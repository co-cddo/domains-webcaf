from django.contrib.auth.models import User
from django.db import models
from multiselectfield import MultiSelectField
from simple_history.models import HistoricalRecords

from webcaf.webcaf.abcs import FrameworkRouter


class Organisation(models.Model):
    ORGANISATION_TYPE_CHOICES = sorted(
        [
            ("ad-hoc-advisory-group", "Ad-hoc advisory group"),
            ("advisory-non-departmental-public-body", "Advisory non-departmental public body"),
            ("agencies-other-public-bodies", "Agencies and other public bodies"),
            ("devolved-administrations", "Devolved administrations"),
            ("executive-agency", "Executive agency"),
            ("executive-non-departmental-public-body", "Executive non-departmental public body"),
            ("executive-office", "Executive office"),
            ("high-profile-groups", "High profile groups"),
            ("ministerial-department", "Ministerial department"),
            ("non-ministerial-department", "Non-ministerial department"),
            ("public-corporation", "Public corporation"),
            ("tribunal", "Tribunal"),
        ]
    ) + [("other", "Other")]
    name = models.CharField(max_length=255, unique=True)
    organisation_type = models.CharField(
        max_length=255, null=True, blank=True, choices=ORGANISATION_TYPE_CHOICES, default=None
    )
    contact_name = models.CharField(max_length=255, null=True, blank=True)
    contact_email = models.EmailField(null=True, blank=True)
    contact_role = models.CharField(max_length=255, null=True, blank=True)
    parent_organisation = models.ForeignKey(
        "self", on_delete=models.SET_NULL, related_name="sub_organisations", null=True, blank=True
    )

    def __str__(self):
        return self.name

    @classmethod
    def get_type_id(cls, label):
        for type in cls.ORGANISATION_TYPE_CHOICES:
            if type[1] == label:
                return type[0]
        return None


class System(models.Model):
    INTERNET_FACING = [("yes", "Yes"), ("no", "No")]
    SYSTEM_TYPES = [
        (
            "directly_supports_organisation_mission",
            """The system directly supports the organisation mission""",
            """for example, Universal Credit""",
        ),
        (
            "supports_other_critical_systems",
            """The system is a corporate or enterprise system or network that supports other critical systems""",
            """for example, hosting platform or network, Active Directory""",
        ),
        (
            "is_critical_for_day_to_day_operations",
            """The system is a corporate or enterprise system deemed critical for day-to-day operations""",
            """for example, Microsoft Office 365, telephony, corporate website""",
        ),
        (
            "hosted_externally_or_by_commercial_providers_or_other_departments",
            """The system is hosted externally, including by commercial providers or other departments""",
            """for example, shared services""",
        ),
    ]
    OWNER_TYPES = [
        ("owned_by_organisation_being_assessed", """The organisation being assessed"""),
        ("owned_by_another_government_organisation", """Another government organisation"""),
        ("owned_by_third_party_company", """Third-party company"""),
        ("owned_by_other", """Other"""),
    ]
    HOSTING_TYPES = [
        ("hosted_on_premises", "On premises"),
        ("hosted_on_cloud", "Cloud hosted"),
        ("hosted_hybrid", "Hybrid"),
        ("hosted_by_third_party", "Commercially hosted by third-party"),
    ]
    ASSESSED_CHOICES = [
        ("assessed_in_2324", "Yes, assessed in 2023/24"),
        ("assessed_in_2425", "Yes, assessed in 2024/25"),
        ("assessed_in_2324_and_2425", "Yes, assessed in both 2023/24 and 2024/25"),
        ("assessed_not_done", "No"),
    ]
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    system_type = models.CharField(
        choices=[(s_type[0], s_type[1]) for s_type in SYSTEM_TYPES], null=True, blank=True, max_length=255
    )
    system_owner = MultiSelectField(choices=OWNER_TYPES, null=True, blank=True, max_length=255)
    hosting_type = MultiSelectField(choices=HOSTING_TYPES, null=True, blank=True, max_length=255)
    internet_facing = models.CharField(choices=INTERNET_FACING, null=True, blank=True)
    last_assessed = models.CharField(choices=ASSESSED_CHOICES, max_length=255, null=True, blank=True)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="systems")

    class Meta:
        unique_together = ["name", "organisation"]


class Assessment(models.Model):
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
    reference = models.CharField(max_length=20, null=True, blank=True)
    framework = models.CharField(max_length=255, choices=FRAMEWORK_CHOICES, default="caf32")
    caf_profile = models.CharField(
        max_length=255,
        choices=PROFILE_CHOICES,
        default="baseline",
    )
    assessment_period = models.CharField(max_length=255)
    created_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
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


class UserProfile(models.Model):
    ROLE_ACTIONS = {
        "organisation_lead": [
            "start a new assessment",
            "continue a draft assessment",
            "view assessments already sent for review",
            "add organisation users",
        ],
        "organisation_user": ["continue a draft assessment", "view assessments already sent for review"],
    }
    ROLE_DESCRIPTIONS = {
        "cyber_advisor": """On this page you can add new systems, modify existing systems and manage users within an
                    organisation.""",
        "organisation_lead": """On this page you can manage users within an
                    organisation, continue a draft assessment and view assessments already sent for review.""",
        "organisation_user": "On this page you can continue a draft assessment and view assessments already sent for review.",
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

    @classmethod
    def get_role_id(cls, role_name):
        for role in cls.ROLE_CHOICES:
            if role[1] == role_name:
                return role[0]
        return None


class Configuration(models.Model):
    config_data = models.JSONField(default=dict)

    def get_current_assessment_period(self):
        return self.config_data.get("current_assessment_period")

    def get_assessment_period_end(self):
        return self.config_data.get("assessment_period_end")
