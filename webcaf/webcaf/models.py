from django.contrib.auth.models import User
from django.db import models


class Organisation(models.Model):
    ORGANISATION_TYPE_CHOICES = sorted(
        [
            ("ad-hoc-advisory-group", "Ad-hoc advisory group"),
            ("advisory-non-departmental-public-body", "Advisory non-departmental public body"),
            ("civil-service", "Civil service"),
            ("executive-agency", "Executive agency"),
            ("executive-non-departmental-public-body", "Executive non-departmental public body"),
            ("executive-office", "executive office"),
            ("independent-monitoring-body", "Independent monitoring body"),
            ("ministerial-department", "Ministerial department"),
            ("non-ministerial-department", "Non-ministerial department"),
            ("public-corporation", "Public corporation"),
            ("special-health-authority", "Special health authority"),
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
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
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
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default="Draft")
    system = models.ForeignKey(System, on_delete=models.CASCADE, related_name="assessments")

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

    class Meta:
        unique_together = ["assessment_period", "system", "status"]


class UserProfile(models.Model):
    ROLE_ACTIONS = {
        "govassure_lead": ["View, add and submit assessment", "Add organisation users"],
        "organisation_user": ["View and edit assessments"],
    }
    ROLE_CHOICES = [
        ("cyber_advisor", "Cyber advisor"),
        ("govassure_lead", "GovAssure Lead"),
        ("organisation_user", "Organisation user"),
    ]
    # Do this rather than add a foreign key to Organisation, in case we need a many-to-many relationship later
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="profiles")
    organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE, related_name="members", null=True, blank=True
    )
    role = models.CharField(max_length=255, null=True, blank=True, choices=ROLE_CHOICES, default="User")

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
