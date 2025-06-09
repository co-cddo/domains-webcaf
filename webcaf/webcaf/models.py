from django.contrib.auth.models import User
from django.db import models


class Organisation(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class System(models.Model):
    name = models.CharField(max_length=255)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="systems")

    class Meta:
        unique_together = ["name", "organisation"]


class UserProfile(models.Model):
    # Do this rather than add a foreign key to Oranisation, in case we need a many-to-many relationship later
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE, related_name="members", null=True, blank=True
    )
