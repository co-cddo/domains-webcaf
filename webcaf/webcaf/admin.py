from datetime import datetime
from typing import Any, Optional

from django import forms
from django.contrib import admin
from django.core.validators import RegexValidator
from django.db.models import Model
from django.forms import CharField, DateTimeInput, ModelForm
from django.forms.fields import ChoiceField
from django.http import HttpRequest
from simple_history.admin import SimpleHistoryAdmin

from webcaf.webcaf.models import (
    Assessment,
    Configuration,
    Organisation,
    System,
    UserProfile,
)


class OptionalFieldsAdminMixin:
    """Mixin to make specified fields optional in the admin form."""

    optional_fields: list[str] = []  # list of field names to make optional

    def get_form(self, request: HttpRequest, obj: Optional[Model] = None, **kwargs: Any):
        form = super().get_form(request, obj, **kwargs)  # type: ignore
        for field_name in self.optional_fields:
            if field_name in form.base_fields:
                form.base_fields[field_name].required = False
        return form


@admin.register(UserProfile)
class UserProfileAdmin(SimpleHistoryAdmin):
    model = UserProfile
    search_fields = ["organisation__name", "user__email"]
    list_display = ["user__email", "organisation__name", "role"]


@admin.register(Organisation)
class OrganisationAdmin(OptionalFieldsAdminMixin, SimpleHistoryAdmin):  # type: ignore
    model = Organisation
    search_fields = ["name", "systems__name", "reference"]
    list_display = ["name", "reference"]
    readonly_fields = ["reference"]
    optional_fields = ["reference"]


@admin.register(System)
class SystemAdmin(OptionalFieldsAdminMixin, SimpleHistoryAdmin):  # type: ignore
    model = System
    search_fields = ["name", "reference"]
    list_display = ["name", "reference", "organisation__name", "system_type", "description"]
    readonly_fields = ["reference"]
    optional_fields = ["reference"]


@admin.register(Assessment)
class AssessmentAdmin(OptionalFieldsAdminMixin, SimpleHistoryAdmin):  # type: ignore
    model = Assessment
    search_fields = ["status", "system__name", "reference"]
    list_display = ["status", "reference", "system__name", "system__organisation__name", "created_on", "last_updated"]
    list_filter = ["status", "system__organisation"]
    ordering = ["-created_on"]
    readonly_fields = ["reference"]
    optional_fields = ["reference"]


class CustomConfigForm(ModelForm):
    """
    Custom form to display the config json content
    in individual fields.
    """

    current_assessment_period = CharField(
        required=True,
        max_length=5,
        validators=[
            RegexValidator(
                regex=r"^\d{2}/\d{2}$",
                message="Enter in the format 'YY/YY', e.g., 25/26",
            )
        ],
        help_text="Enter in format 'YY/YY', e.g., 25/26",
    )
    assessment_period_end = forms.DateTimeField(
        widget=DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": "vDateTimeField",
            }
        ),
        required=True,
    )
    default_framework = ChoiceField(required=True, choices=Assessment.FRAMEWORK_CHOICES)

    class Meta:
        model = Configuration
        fields = ["name", "current_assessment_period", "assessment_period_end", "default_framework"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["current_assessment_period"].initial = self.instance.get_current_assessment_period()
        self.fields["assessment_period_end"].initial = datetime.strptime(
            self.instance.get_assessment_period_end(), "%d %B %Y %I:%M%p"
        ).strftime("%Y-%m-%dT%H:%M")
        self.fields["default_framework"].initial = self.instance.get_default_framework()

    def save(self, commit=True):
        if not self.instance.config_data:
            self.instance.config_data = {}
        self.instance.config_data["current_assessment_period"] = self.cleaned_data["current_assessment_period"]
        # Convert back to the string representation
        self.instance.config_data["assessment_period_end"] = self.cleaned_data["assessment_period_end"].strftime(
            "%d %B %Y %I:%M%p"
        )
        self.instance.config_data["default_framework"] = self.cleaned_data["default_framework"]
        return super().save(commit=commit)


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    form = CustomConfigForm
