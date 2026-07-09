import csv
import json
import logging
import zoneinfo
from datetime import datetime
from io import BytesIO, StringIO, TextIOWrapper
from typing import Any, MutableMapping, Optional
from zoneinfo import ZoneInfo

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db.models import F, Model, Q
from django.forms import CharField, DateTimeInput, ModelForm
from django.forms.fields import ChoiceField
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils import timezone
from simple_history.admin import SimpleHistoryAdmin

from webcaf.webcaf.models import (
    Assessment,
    Configuration,
    Organisation,
    Review,
    Settings,
    System,
    Tip,
    UserProfile,
)
from webcaf.webcaf.tip.util import RecommendationService
from webcaf.webcaf.views.system import SystemForm


class PrettyJSONWidget(forms.Textarea):
    """
    A custom widget that extends the Django Textarea widget for formatting JSON data.

    This widget ensures that JSON data is presented in a readable, pretty-printed format
    with an indentation of 4 spaces. It supports JSON input in string format and attempts
    to parse and reformat it. If parsing fails, the raw value is returned.

    :ivar is_required: Indicates whether the widget is required in forms.
    :type is_required: bool
    """

    def format_value(self, value):
        if value in ("", None):
            return ""
        try:
            if isinstance(value, str):
                value = json.loads(value)
            return json.dumps(value, indent=4)
        except Exception:
            return value


class JsonDataAdminForm(forms.ModelForm):
    """
    Base ``ModelForm`` for admin models that expose a single large JSON field.

    Subclasses only need to declare :attr:`json_field` (and the usual ``Meta``
    naming their model). The base class provides the behaviour shared by all
    such forms:

    * renders the JSON field with :class:`PrettyJSONWidget` for readable,
      pretty-printed output;
    * seeds the form's initial data from the current instance so the stored
      JSON is shown on load;
    * parses a submitted JSON string back into a Python object on clean.

    :cvar json_field: Name of the model field holding the JSON payload.
    :cvar json_readonly: Whether the JSON widget should be rendered read-only.
        A read-only flag applied elsewhere (e.g. per-request in an admin's
        ``get_form``) is also honoured.
    """

    json_field: str = ""
    json_readonly: bool = False
    # Get around mypy warning
    initial: MutableMapping[str, Any]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        field = self.fields[self.json_field]
        # Honour a read-only flag set either on the class or on the widget by
        # the admin's ``get_form`` before swapping in the pretty widget.
        attrs = {"rows": 20, "cols": 60}
        if self.json_readonly or field.widget.attrs.get("readonly"):
            attrs["readonly"] = True
        field.widget = PrettyJSONWidget(attrs=attrs)

        value = getattr(self.instance, self.json_field, None)
        if value:
            self.initial[self.json_field] = value

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        if cleaned_data:
            value = cleaned_data.get(self.json_field)
            if isinstance(value, str):
                cleaned_data[self.json_field] = json.loads(value)
        return cleaned_data if cleaned_data else {}


class OptionalFieldsAdminMixin:
    """Mixin to make specified fields optional in the admin form."""

    optional_fields: list[str] = []  # list of field names to make optional

    def get_form(self, request: HttpRequest, obj: Optional[Model] = None, **kwargs: Any):
        form = super().get_form(request, obj, **kwargs)  # type: ignore
        for field_name in self.optional_fields:
            if field_name in form.base_fields:
                form.base_fields[field_name].required = False
        return form


class SortedOrganisationFilter(admin.SimpleListFilter):
    """
    A Django admin filter for sorting and filtering querysets by Organisation.
    This filter dynamically detects the appropriate field chain in the queryset
    model to apply the organisation filtering based on its structure.

    :ivar title: The display name for the filter in the admin interface.
    :type title: str
    :ivar parameter_name: The query parameter name used in the URL for the filter.
    :type parameter_name: str
    """

    title = "Organisation"
    parameter_name = "organisation"  # the query parameter used in the URL

    def lookups(self, request, model_admin):
        # Generic: works with Organisation model, sorts alphabetically
        orgs = Organisation.objects.all().order_by("name")
        return [(org.id, org.name) for org in orgs]

    def queryset(self, request, queryset):
        if self.value():
            model = queryset.model
            if self._has_field(model, "organisation"):
                return queryset.filter(organisation__id=self.value())
            if self._has_field(model, "system"):
                return queryset.filter(system__organisation__id=self.value())
            if self._has_field(model, "assessment"):
                return queryset.filter(assessment__system__organisation__id=self.value())
        return queryset

    @staticmethod
    def _has_field(model, name: str) -> bool:
        try:
            model._meta.get_field(name)
            return True
        except Exception:
            return False


class SettingsAdminForm(forms.ModelForm):
    class Meta:
        model = Settings
        fields = "__all__"
        labels = {
            "admin_verification_enabled": "Enable admin 2f verification",
            "gov_assure_email": "GovAssure email address",
        }


@admin.register(Settings)
class SettingsAdmin(SimpleHistoryAdmin):
    form = SettingsAdminForm

    def get_changeform_initial_data(self, request):
        """
        Force the new screen to have the values from the singleton
        :param request:
        :return:
        """
        settings_instance = Settings.get_instance()
        return {
            "admin_verification_enabled": settings_instance.admin_verification_enabled,
        }


@admin.register(UserProfile)
class UserProfileAdmin(SimpleHistoryAdmin):
    model = UserProfile
    search_fields = ["organisation__name", "user__email"]
    list_display = ["user_email", "organisation_name", "role"]
    list_filter = ["role", SortedOrganisationFilter]
    autocomplete_fields = ["organisation", "user"]
    list_select_related = ["user", "organisation"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            user_email=F("user__email"),
            organisation_name=F("organisation__name"),
        )

    @admin.display(ordering="user_email", description="User email")
    def user_email(self, obj):
        return obj.user_email

    @admin.display(ordering="organisation_name", description="Organisation")
    def organisation_name(self, obj):
        return obj.organisation_name


@admin.register(Organisation)
class OrganisationAdmin(OptionalFieldsAdminMixin, SimpleHistoryAdmin):  # type: ignore
    model = Organisation
    search_fields = ["name", "systems__name", "reference"]
    list_display = ["name", "reference"]
    readonly_fields = ["reference"]
    optional_fields = ["reference"]
    autocomplete_fields = [
        "parent_organisation",
    ]

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
    list_display = ["name", "reference", "organisation_name", "system_type", "description"]
    readonly_fields = ["reference"]
    optional_fields = ["reference"]
    list_filter = [SortedOrganisationFilter, "system_type"]
    list_select_related = ["organisation"]
    autocomplete_fields = ["organisation"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            organisation_name=F("organisation__name"),
        )

    @admin.display(ordering="organisation_name", description="Organisation")
    def organisation_name(self, obj):
        return obj.organisation_name

    class Media:
        js = ("webcaf/js/admin_system.js",)


class AssessmentAdminForm(JsonDataAdminForm):
    json_field = "assessments_data"
    json_readonly = True

    class Meta:
        model = Assessment
        fields = "__all__"


@admin.register(Assessment)
class AssessmentAdmin(OptionalFieldsAdminMixin, SimpleHistoryAdmin):  # type: ignore
    model = Assessment
    form = AssessmentAdminForm
    search_fields = ["status", "system__name", "reference"]
    list_display = [
        "status",
        "reference",
        "review_type",
        "system_name",
        "system_organisation",
        "created_on",
        "last_updated",
    ]
    list_filter = ["status", SortedOrganisationFilter, "review_type"]
    ordering = ["-created_on"]
    readonly_fields = ["reference"]
    optional_fields = ["reference"]
    list_select_related = ["system", "system__organisation"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            system_name=F("system__name"),
            system_organisation=F("system__organisation__name"),
        )

    @admin.display(ordering="system_name", description="System")
    def system_name(self, obj):
        return obj.system_name

    @admin.display(ordering="system_organisation", description="Organisation")
    def system_organisation(self, obj):
        return obj.system_organisation

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "system":
            object_id = request.resolver_match.kwargs.get("object_id")
            obj = self.get_object(request, object_id)
            if object_id and obj and obj.system:
                # If we are editing an assessment, then we can make sure
                # that we only pick systems from the current organisation only
                kwargs["queryset"] = System.objects.filter(organisation=obj.system.organisation)

        form_field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        return form_field


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
    # Parameter to control the cutoff date display
    banner_display_until = forms.DateTimeField(
        widget=DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": "vDateTimeField",
            }
        ),
        required=True,
    )

    class Meta:
        model = Configuration
        fields = [
            "name",
            "current_assessment_period",
            "assessment_period_end",
            "banner_display_until",
            "default_framework",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assessment_period = self.instance.get_current_assessment_period()
        if assessment_period is None:
            return

        def set_local_tz(input_date):
            """
            Removes the UTC timezone from a date string and returns it in local timezone format.
            This is needed because the django app is running in UTC and the dates are stored in the local timezone
            for this form.
            :param input_date:
            :return:
            """
            parsed_date = datetime.strptime(input_date, "%d %B %Y %I:%M%p")
            parsed_date.replace(tzinfo=ZoneInfo("Europe/London"))
            return parsed_date.strftime("%Y-%m-%dT%H:%M")

        self.fields["current_assessment_period"].initial = assessment_period
        self.fields["assessment_period_end"].initial = set_local_tz(self.instance.get_assessment_period_end())
        if self.instance.get_banner_display_until():
            self.fields["banner_display_until"].initial = set_local_tz(self.instance.get_banner_display_until())
        self.fields["default_framework"].initial = self.instance.get_default_framework()

    def save(self, commit=True):
        if not self.instance.config_data:
            self.instance.config_data = {}
        self.instance.config_data["current_assessment_period"] = self.cleaned_data["current_assessment_period"]

        # Convert back to the string representation
        def to_local(date_time):
            """
            Converts a datetime object to local timezone format.
            :param date_time:
            :return:
            """
            local_tz = zoneinfo.ZoneInfo("Europe/London")
            date_time.replace(tzinfo=local_tz)
            return date_time.strftime("%d %B %Y %I:%M%p")

        # The user is inputting the date/time in their timezone, but django
        # assumes that the date/time is in UTC as that is the setting in the settings.py,
        # Therefore, manually convert to Europe/London before saving to the database
        self.instance.config_data["assessment_period_end"] = to_local(self.cleaned_data["assessment_period_end"])
        self.instance.config_data["banner_display_until"] = to_local(self.cleaned_data["banner_display_until"])
        self.instance.config_data["default_framework"] = self.cleaned_data["default_framework"]
        return super().save(commit=commit)


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    form = CustomConfigForm


class ReviewAdminForm(JsonDataAdminForm):
    json_field = "review_data"
    json_readonly = True

    class Meta:
        model = Review
        fields = "__all__"


@admin.register(Review)
class ReviewAdmin(OptionalFieldsAdminMixin, SimpleHistoryAdmin):
    form = ReviewAdminForm
    search_fields = ["assessment_system_name", "assessment_reference", "assessment_organisation"]
    list_display = [
        "assessment_system_name",
        "assessment_framework",
        "assessment_review_type",
        "assessment_reference",
        "assessment_organisation",
        "status",
    ]
    list_filter = [
        "assessment__system__name",
        "assessment__framework",
        SortedOrganisationFilter,
        "assessment__review_type",
        "status",
    ]
    list_select_related = [
        "assessment",
        "assessment__system",
        "assessment__system__organisation",
    ]
    readonly_fields = ["created_on", "last_updated", "last_updated_by", "reference"]
    optional_fields = ["reference"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            assessment_system_name=F("assessment__system__name"),
            assessment_framework=F("assessment__framework"),
            assessment_review_type=F("assessment__review_type"),
            assessment_reference=F("assessment__reference"),
            assessment_organisation=F("assessment__system__organisation__name"),
        )

    @admin.display(ordering="assessment_review_type", description="Review type")
    def assessment_review_type(self, obj):
        return obj.assessment_review_type

    @admin.display(ordering="assessment_system_name", description="System")
    def assessment_system_name(self, obj):
        return obj.assessment_system_name

    @admin.display(ordering="assessment_reference", description="Assessment Ref")
    def assessment_reference(self, obj):
        return obj.assessment_reference

    @admin.display(ordering="assessment_framework", description="Framework")
    def assessment_framework(self, obj):
        return obj.assessment_framework

    @admin.display(ordering="assessment_organisation", description="Organisation")
    def assessment_organisation(self, obj):
        return obj.assessment_organisation

    def get_form(self, request, obj=None, **kwargs):
        """
        This method customizes the form retrieved for the given request, allowing
        specific queryset filtering based on the `assessment` foreign key field.
        It adjusts the queryset to include unassigned assessments and, in case of
        a change view, assessments assigned to the current object.

        :param request: The request object, representing the HTTP request being
            processed.
        :param obj: Optional; Represents the object being edited in change views.
            Defaults to None for add views.
        :param kwargs: Arbitrary keyword arguments that can be passed while
            retrieving the form.
        :return: A customized form instance with the adjusted queryset for the
            `assessment` field.
        """
        form = super().get_form(request, obj, **kwargs)

        fk_field = form.base_fields["assessment"]
        qs = fk_field.queryset

        # Any unassigned assessments
        fk_field.queryset = qs.filter(reviews__isnull=True)
        if obj:  # change view
            # filter queryset: unassigned OR assigned to current obj
            fk_field.queryset |= qs.filter(reviews__in=[obj.id])

        return form

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "assessment":
            current_config = Configuration.objects.get_default_config()
            kwargs["queryset"] = Assessment.objects.filter(
                status="submitted",
                assessment_period=current_config.get_current_assessment_period(),
            ).order_by("-created_on")
        form_field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        return form_field

    def save_form(self, request, form, change):
        return super().save_form(request, form, change)

    def save_model(self, request, obj, form, change):
        if hasattr(obj, "last_updated_by"):
            obj.last_updated_by = request.user
        super().save_model(request, obj, form, change)


class TipAdminForm(JsonDataAdminForm):
    json_field = "tip_data"

    # Read-only state is decided per-request in ``TipAdmin.get_form``.

    class Meta:
        model = Tip
        fields = "__all__"


@admin.register(Tip)
class TipAdmin(OptionalFieldsAdminMixin, SimpleHistoryAdmin):
    form = TipAdminForm
    exclude = ("status",)
    search_fields = [
        "assessment_system_name",
        "assessment_reference",
        "assessment_organisation",
    ]
    readonly_fields = [
        "status_badge",
        "created_on",
        "last_updated",
        "last_updated_by",
        "reference",
        "pdf_link",
        "excel_link",
        "completed_percentage",
    ]
    optional_fields = ["reference"]
    list_display = [
        "status_badge",
        "completed_percentage",
        "assessment_system_name",
        "assessment_framework",
        "assessment_review_type",
        "assessment_reference",
        "assessment_organisation",
        "pdf_link",
        "excel_link",
    ]
    list_filter = [
        "review__assessment__system__name",
        SortedOrganisationFilter,
        "review__assessment__review_type",
        "status",
    ]
    actions: list[str] = []

    def get_form(self, request: HttpRequest, obj: Optional[Model] = None, **kwargs: Any):
        """
        Fetches and customizes the form for the specified model instance based on user access rights.

        If the user is not a superuser, the "tip_data" field in the form will be set to readonly.

        :param request: The HTTP request object representing the current request.
        :type request: HttpRequest
        :param obj: An optional instance of the model associated with the form.
        :type obj: Optional[Model]
        :param kwargs: Arbitrary keyword arguments passed to the underlying `get_form` method.
        :type kwargs: Any
        :return: A Django form, potentially customized to restrict certain fields based on user access.
        :rtype: BaseModelForm
        """
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            form.base_fields["tip_data"].widget.attrs["readonly"] = True
        return form

    @admin.display(ordering="assessment_review_type", description="Review type")
    def assessment_review_type(self, obj):
        return obj.assessment_review_type

    @admin.display(ordering="assessment_system_name", description="System")
    def assessment_system_name(self, obj):
        return obj.assessment_system_name

    @admin.display(ordering="assessment_reference", description="Assessment Ref")
    def assessment_reference(self, obj):
        return obj.assessment_reference

    @admin.display(ordering="assessment_framework", description="Framework")
    def assessment_framework(self, obj):
        return obj.assessment_framework

    @admin.display(ordering="assessment_organisation", description="Organisation")
    def assessment_organisation(self, obj):
        return obj.assessment_organisation

    @admin.display(description="Status")
    def status_badge(self, obj):
        if obj.status == "review":
            return render_to_string(
                "admin/webcaf/tip/partials/review_tag.html",
                {"status": obj.get_status_display(), "status_class": "pending"},
            )
        elif obj.status == "approved":
            return render_to_string(
                "admin/webcaf/tip/partials/review_tag.html",
                {"status": obj.get_status_display(), "status_class": "approved"},
            )
        elif obj.status == "rejected":
            return render_to_string(
                "admin/webcaf/tip/partials/review_tag.html",
                {"status": obj.get_status_display(), "status_class": "rejected"},
            )
        elif obj.status == "completed":
            return render_to_string(
                "admin/webcaf/tip/partials/review_tag.html",
                {"status": obj.get_status_display(), "status_class": "completed"},
            )
        return obj.get_status_display()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            assessment_system_name=F("review__assessment__system__name"),
            assessment_framework=F("review__assessment__framework"),
            assessment_review_type=F("review__assessment__review_type"),
            assessment_reference=F("review__assessment__reference"),
            assessment_organisation=F("review__assessment__system__organisation__name"),
        ).select_related(
            "review", "review__assessment", "review__assessment__system", "review__assessment__system__organisation"
        )

    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            path(
                "<int:tip_id>/download/<str:mode>/",
                self.admin_site.admin_view(self.download_view),
                name="tip_download",
            ),
        ]
        return custom_urls + urls

    def download_view(self, request: HttpRequest, tip_id: int, mode: str):
        """
        Generates and returns a PDF response based on the provided template and recommendations.

        This view fetches a tip object corresponding to the given ID, initializes a
        RecommendationService with required data, and renders a PDF using a specified
        template. Recommendations are categorized as "priority" and "other" and passed
        to the template for rendering.

        :param mode:
        :param request: The HTTP request instance.
        :type request: HttpRequest
        :param tip_id: The ID of the tip object to be fetched and used.
        :type tip_id: int
        :return: An HTTP response containing the rendered PDF.
        :rtype: HttpResponse
        """
        tip = Tip.objects.get(pk=tip_id)
        service = RecommendationService(tip, request)
        if mode == "pdf":
            return service.render_pdf(
                "tip/report.html",
                {
                    "object": tip,
                    "priority_recommendations": service.filter_recommendations("priority"),
                    "other_recommendations": service.filter_recommendations("other"),
                },
            )
        return service.render_excel(
            {
                "object": tip,
                "priority_recommendations": service.filter_recommendations("priority"),
                "other_recommendations": service.filter_recommendations("other"),
            }
        )

    def completed_percentage(self, obj):
        """
        Calculates the completion percentage of an object and returns it as a formatted string.

        :param obj: The object containing the `completed_percentage` attribute.
        :type obj: Any
        :return: A string representing the formatted completion percentage.
        :rtype: str
        """
        return f"{obj.completed_percentage}%"

    def pdf_link(self, obj):
        url = reverse("admin:tip_download", args=[obj.pk, "pdf"])
        return render_to_string("admin/webcaf/tip/partials/link.html", {"url": url, "text": "View PDF"})

    pdf_link.short_description = "PDF download"  # type: ignore[attr-defined]

    def excel_link(self, obj):
        url = reverse("admin:tip_download", args=[obj.pk, "excel"])
        return render_to_string("admin/webcaf/tip/partials/link.html", {"url": url, "text": "View Excel"})

    excel_link.short_description = "Excel download"  # type: ignore[attr-defined]

    def save_model(self, request, obj: Tip, form, change):
        obj.last_updated_by = request.user
        obj.last_updated = timezone.now()
        if "_approve" in request.POST:
            obj.approve(request.user)
        elif "_reject" in request.POST:
            obj.reject(request.user)
        elif "_reopen" in request.POST:
            obj.reopen(request.user)
        super().save_model(request, obj, form, change)

    def has_view_permission(self, request, obj=None):
        """
        Determine if the user has the permission to view the given object.

        This method checks if the user has the view permissions granted explicitly by
        the parent class or if the user has specific permissions to approve or reject
        a tip.

        :param request: The HTTP request object containing information about the
            current request and the user making the request.
        :type request: HttpRequest
        :param obj: The object for which the view permission is being checked.
            Defaults to None if no object is being queried.
        :type obj: Any or None
        :return: A boolean value indicating whether the user has permission to
            view the object.
        :rtype: bool
        """
        return (
            super().has_view_permission(request, obj)
            or request.user.has_perm("webcaf.can_approve_tip")
            or request.user.has_perm("webcaf.can_reject_tip")
        )

    def has_change_permission(self, request, obj=None):
        """
        Determines whether a user has the required permission to change an object. This
        method checks if the user has specific permissions ("webcaf.can_approve_tip" or
        "webcaf.can_reject_tip"). For superusers, additional checks are present to grant
        permissions based on request method or specific post data.

        :param request: The HttpRequest object representing the current request.
        :type request: HttpRequest
        :param obj: The object for which the permission check is performed. Default is None.
        :type obj: Any
        :return: A boolean value indicating whether the user has change permissions for the
            given object.
        :rtype: bool
        """
        # If not superuser, check if user has permission to approve or reject
        if request.user.has_perm("webcaf.can_approve_tip") or request.user.has_perm("webcaf.can_reject_tip"):
            if request.method == "GET":
                return True
            return request.user.is_superuser or "_approve" in request.POST or "_reject" in request.POST
        return super().has_change_permission(request, obj)

    class Media:
        css = {"all": ("webcaf/admin.css",)}
