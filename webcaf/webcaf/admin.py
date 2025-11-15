import csv
import logging
from datetime import datetime
from io import BytesIO, StringIO, TextIOWrapper
from typing import Any, Optional

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db.models import Model, Q
from django.forms import CharField, DateTimeInput, ModelForm
from django.forms.fields import ChoiceField
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import path
from simple_history.admin import SimpleHistoryAdmin

from webcaf.webcaf.models import (
    Assessment,
    Configuration,
    Organisation,
    System,
    UserProfile,
)
from webcaf.webcaf.views.system import SystemForm


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
    list_filter = ["role", "user__email", "organisation__name"]


@admin.register(Organisation)
class OrganisationAdmin(OptionalFieldsAdminMixin, SimpleHistoryAdmin):  # type: ignore
    model = Organisation
    search_fields = ["name", "systems__name", "reference"]
    list_display = ["name", "reference"]
    readonly_fields = ["reference"]
    optional_fields = ["reference"]

    logger = logging.getLogger("OrganisationAdmin")
    csv_headers = [
        "Organisation",
        "Lead Government Department",
        "Reference",
        "Type",
        "Email1",
        "Email2",
        "Email3",
        "Email4",
        "Email5",
        "Email6",
    ]

    # Add custom URL for the import view
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-org-csv/", self.admin_site.admin_view(self.import_csv), name="import-org-csv"),
            path(
                "import-org-csv-template/",
                self.admin_site.admin_view(self.import_csv_template),
                name="import-org-csv-template",
            ),
        ]
        return custom_urls + urls

    def import_csv_template(self, request):
        """
        Creates and serves a CSV file as a downloadable response. The CSV file acts
        as a template for importing organisation data, containing specific headers
        which must be adhered to for proper processing during an import operation.

        :param request: The HTTP request object.
        :return: An HTTP response containing the generated CSV file.
        """
        csv_buffer = StringIO()
        writer = csv.DictWriter(
            csv_buffer,
            fieldnames=self.csv_headers,
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()
        csv_buffer.seek(0)
        csv_bytes = BytesIO(csv_buffer.getvalue().encode("utf-8"))
        response = HttpResponse(content_type="text/csv")
        response.write(csv_bytes.getvalue())
        response["Content-Disposition"] = 'attachment; filename="organisation_import_template.csv"'
        return response

    def import_csv(self, request):
        """
        Handles the import of a CSV file through a POST request, processes its data to create or update
        organisations and users in the database, and associates organisations with a designated parent
        organisation.
        The header row is expected to contain the fields defined in `csv_headers`:
        Each email field represents a cyber advisor for a particular organisation.

        This method expects a CSV file containing organisation and user information. It reads and processes
        this file to create the necessary records in the database while maintaining proper associations between
        users, organisations, and their parent organisations.

        :param request: The HTTP request object that includes the CSV file to be processed.
        :type request: HttpRequest
        :return: A redirect to the organisation admin page upon successful file processing or renders a
            form to upload the CSV file if the request method is not POST.
        :rtype: HttpResponse
        """
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded = TextIOWrapper(csv_file.file, encoding="utf-8")
            reader = csv.DictReader(decoded)

            # Check headers
            headers = reader.fieldnames
            if set(headers) != set(self.csv_headers):
                self.message_user(
                    request, f"The CSV file is missing required headers {self.csv_headers}.", messages.ERROR
                )
                return redirect("..")

            count = 0
            # Import the organisations
            for row in reader:
                count += 1
                organisation = self.find_organisation(row)

                # If still not found, then create a new organisation
                if not organisation:
                    self.logger.info(
                        f"Creating {row['Organisation']} as not found in the database"
                        f"reference: {row['Reference']}"
                        f"name: {row['Organisation']}."
                    )
                    self.message_user(
                        request, f"Creating {row['Organisation']} as not found in the database", messages.WARNING
                    )
                    organisation_type = row.get("Type", "").strip()
                    if org_type_id := Organisation.get_type_id(organisation_type):
                        organisation = Organisation.objects.create(
                            name=row["Organisation"], organisation_type=org_type_id
                        )
                    else:
                        organisation = Organisation.objects.create(name=row["Organisation"])

                for email in ["Email1", "Email2", "Email3", "Email4", "Email5", "Email6"]:
                    email_ = row.get(email, "").strip()
                    if email_:
                        user = User.objects.filter(email=email_).first()
                        if not user:
                            self.logger.info(f"Creating {email_} as not found in the database.")
                            self.message_user(
                                request, f"Creating {email_} as not found in the database.", messages.WARNING
                            )
                            # If not found, create a new user
                            user = User.objects.create_user(email_, email_)
                        profile, _created = UserProfile.objects.get_or_create(
                            user=user, organisation=organisation, role="cyber_advisor"
                        )

                        if not _created:
                            msg = f"The user with email {email_} already exists in the database for the organisation {organisation}."
                            self.logger.warning(msg)
                            self.logger.info(msg)

            # Now set the parent organisation
            # Reset the reader
            decoded.seek(0)
            reader = csv.DictReader(decoded)
            for row in reader:
                parent_organisation = Organisation.objects.filter(Q(name=row["Lead Government Department"])).first()
                if parent_organisation:
                    organisation = self.find_organisation(row)
                    if organisation != parent_organisation:
                        # No parent if this is the parent organisation
                        organisation.parent_organisation = parent_organisation
                        organisation.save()
                    else:
                        organisation.parent_organisation = None
                        organisation.save()

            self.message_user(request, f"✅ Imported {count} Organisations.", messages.SUCCESS)
            return redirect("..")

        opts = self.model._meta
        context = {
            **self.admin_site.each_context(request),  # adds admin context
            "opts": opts,
            "app_label": opts.app_label,
            "title": "Import Organisations from CSV",
        }
        # Render upload form
        return render(request, "admin/webcaf/organisation/import_csv.html", context)

    def find_organisation(self, row: dict[str | Any, str | Any]) -> Organisation | None:
        """
        Finds and returns an Organisation instance based on the provided row data.

        This method attempts to retrieve an Organisation object by first using the
        `Reference` field. If the organisation cannot be found using the reference,
        it falls back to searching by the organisation's name.

        :param row: A dictionary containing data for finding an organisation. Keys
            include `Reference` and `Organisation`.
        :return: An Organisation object if found, otherwise None.
        """
        organisation: Organisation | None = None
        # first try to get the organisation by reference
        if row["Reference"]:
            organisation = Organisation.objects.filter(Q(reference=row["Reference"])).first()

        # If fails try to get the organisation by name
        if not organisation and row["Organisation"]:
            organisation = Organisation.objects.filter(Q(name=row["Organisation"])).first()
        return organisation


class AdminSystemForm(SystemForm):
    """
    AdminSystemForm class for customizing the behavior of the system form in an admin context.

    This class is a subclass of SystemForm and is designed to override some field requirements
    specific to the admin form use case. It hides the "action" field and makes the
    "corporate_services_other" field optional. Useful for simplifying the interface and ensuring
    only relevant fields are presented to the user.

    :ivar fields: Dictionary of form fields with details about required status and widgets.
    :type fields: dict
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["corporate_services_other"].required = False
        self.fields["description"].required = False
        # Do not need the action field. It is only used in the user screen confirmation
        self.fields["action"].required = False
        self.fields["action"].widget = forms.HiddenInput(
            attrs={
                "class": "vHiddenField",
            }
        )

    class Meta(SystemForm.Meta):
        fields = SystemForm.Meta.fields + [
            "organisation",
            "description",
        ]

        labels = SystemForm.Meta.labels | {
            "system_type": "System type",
        }


@admin.register(System)
class SystemAdmin(OptionalFieldsAdminMixin, SimpleHistoryAdmin):  # type: ignore
    form = AdminSystemForm
    search_fields = ["name", "reference"]
    list_display = ["name", "reference", "organisation__name", "system_type", "description"]
    readonly_fields = ["reference"]
    optional_fields = ["reference"]

    class Media:
        js = ("webcaf/js/admin_system.js",)


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
