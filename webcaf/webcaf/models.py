from django.contrib.auth.models import User
from django.db import models


class Organisation(models.Model):
    ORGANISATION_TYPE_CHOICES = sorted(
        [
            ("Ad-hoc advisory group", "Ad-hoc advisory group"),
            ("Advisory non-departmental public body", "Advisory non-departmental public body"),
            ("Civil service", "Civil service"),
            ("Executive agency", "Executive agency"),
            ("Executive non-departmental public body", "Executive non-departmental public body"),
            ("Executive office", "Executive office"),
            ("Independent monitoring body", "Independent monitoring body"),
            ("Ministerial department", "Ministerial department"),
            ("Non-ministerial department", "Non-ministerial department"),
            ("Public corporation", "Public corporation"),
            ("Special health authority", "Special health authority"),
            ("Tribunal", "Tribunal"),
        ]
    ) + [("Other", "Other")]
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


class System(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="systems")

    class Meta:
        unique_together = ["name", "organisation"]


class Assessment(models.Model):
    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Submitted", "Submitted"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    ]
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default="Draft")
    name = models.CharField(max_length=255)
    system = models.ForeignKey(System, on_delete=models.CASCADE, related_name="assessments")
    assessment_period = models.CharField(max_length=255)
    start_date = models.DateField()

    class Meta:
        unique_together = ["assessment_period", "system", "status"]


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("Cyber advisor", "Cyber advisor"),
        ("GovAssure Lead", "GovAssure Lead"),
        ("Organisation user", "Organisation user"),
    ]
    # Do this rather than add a foreign key to Organisation, in case we need a many-to-many relationship later
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="profiles")
    organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE, related_name="members", null=True, blank=True
    )
    role = models.CharField(max_length=255, null=True, blank=True, choices=ROLE_CHOICES, default="User")

    class Configuration(models.Model):
        config_data = models.JSONField(default=dict)

        def get_current_assessment_period(self):
            return self.config_data.get("current_assessment_period")

        def get_assessment_period_end(self):
            return self.config_data.get("assessment_period_end")
