import logging
from collections import namedtuple
from datetime import datetime
from pathlib import Path

from django.forms import ChoiceField, ModelForm
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic import DetailView, TemplateView, UpdateView
from weasyprint import default_url_fetcher

from webcaf.webcaf.models import Configuration, Review, System
from webcaf.webcaf.utils.session import SessionUtil
from webcaf.webcaf.views.assessor.util import BaseReviewMixin

"""
This module contains the views for the review section of the assessor dashboard.

It is **important** that the BaseReviewMixin is used in all views within this module.
This ensures that only users with the appropriate roles can access the views.

NOTE:
Also, any query for the review object is filtered by the current organisation and role of the user.
This ensures that only reviews for the current organisation are displayed.

"""


class ReviewIndexView(BaseReviewMixin, TemplateView):
    """
    Provides a view for assessors' account page/ list of reviews opened for the current organisation.

    This class-based view is designed for authenticated users to display the assessor's
    account page. It ensures that only logged-in users can access the page, and it provides
    necessary context data such as the current user profile and associated reviews.

    :ivar template_name: Path to the template file that renders the assessor's account page.
    :type template_name: str
    :ivar login_url: URL route to initiate the OIDC login process for unauthenticated users.
    :type login_url: str
    """

    template_name = "review/list.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        configuration = Configuration.objects.get_default_config()
        data["reviews"] = self.get_reviews_for_user(data["current_profile"], configuration)
        return data


class ReviewDetailView(BaseReviewMixin, DetailView):
    """
    Present the high level review steps to the user

    :ivar model: The model associated with this view, representing a review.
    :type model: Review
    :ivar template_name: The template used to render the view for editing reviews.
    :type template_name: str
    :ivar login_url: The URL to redirect users for authentication if they are not logged in.
    :type login_url: str
    """

    model = Review
    template_name = "review/summary.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        configuration = Configuration.objects.get_default_config()
        data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        data["breadcrumbs"] = [
            {
                "url": reverse("my-account"),
                "text": "My account",
            },
            {
                "url": None,
                "text": "Edit draft review",
            },
        ]
        data["current_assessment_period"] = configuration.get_current_assessment_period()
        data["cutoff_time"] = configuration.get_submission_due_date().strftime("%I:%M%p")
        data["cutoff_date"] = configuration.get_submission_due_date().strftime("%d %B %Y")
        data["objectives"] = self.object.assessment.get_router().get_sections()
        return data


class ReviewHistoryView(BaseReviewMixin, UpdateView):
    model = Review
    template_name = "review/revisions.html"
    # No fields to edit, we manually update if needed
    fields = []

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["breadcrumbs"] = [
            {
                "url": reverse("my-account"),
                "text": "My account",
            },
            {
                "text": "Report history",
            },
        ]
        return data

    def form_valid(self, form):
        if not self.object.is_review_complete():
            form.add_error(None, "You cannot edit a review that has not been completed.")
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("reopen-review", kwargs={"pk": self.object.id})


class ReopenReviewView(BaseReviewMixin, UpdateView):
    model = Review
    template_name = "review/reopen-review.html"
    # No fields to edit, we manually update if needed
    fields = []

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["breadcrumbs"] = [
            {
                "url": reverse("my-account"),
                "text": "My account",
            },
            {
                "url": reverse("review-history", kwargs={"pk": self.object.id}),
                "text": "Report history",
            },
            {
                "text": "Open current review",
            },
        ]
        return data

    def form_valid(self, form):
        if not self.object.is_review_complete():
            form.add_error(None, "You cannot edit a review that has not been completed.")
            return self.form_invalid(form)
        form.instance.reopen()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("edit-review", kwargs={"pk": self.object.id})


DetailEntry = namedtuple("DetailEntry", ["name", "value", "can_update"])


class SystemAndScopeForm(ModelForm):
    action = ChoiceField(
        choices=[
            ("confirm", "Review system and scope"),
        ]
    )
    field_to_change = ChoiceField(choices=[], required=False)

    class Meta:
        model = Review
        fields = ["action"]


class SystemAndScopeView(BaseReviewMixin, UpdateView):
    """
    Handles the system and scope confirmation view for the review process.

    This class is a subclass of both UserRoleCheckMixin and UpdateView. It provides
    functionality for managing the confirmation of system and scope details during
    a review process. It ensures role-based access, processes submitted forms, and
    provides the appropriate view context for the template. This view interacts
    with a Review instance and logs activities related to the confirmation process.

    :ivar template_name: Path to the HTML template used for the view.
    :type template_name: str
    :ivar login_url: URL for redirecting unauthorized users to the login page.
    :type login_url: str
    :ivar form_class: Form class used for validating and handling form submissions.
    :type form_class: type[Form]
    :ivar model: Model associated with this view, representing a review.
    :type model: type[Model]
    :ivar logger: Logger object for logging view activities.
    :type logger: logging.Logger
    """

    template_name = "review/system_and_scope.html"
    form_class = SystemAndScopeForm
    model = Review
    logger = logging.Logger("SystemAndScopeView")

    def get_success_url(self):
        return reverse("edit-review", kwargs={"pk": self.object.id})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        assessment = data["object"].assessment
        if assessment.system.organisation != data["current_profile"].organisation:
            raise PermissionError("You do not have access to this review")
        data["breadcrumbs"] = [
            {
                "url": reverse("my-account"),
                "text": "My account",
            },
            {
                "url": reverse("edit-review", kwargs={"pk": self.object.id}),
                "text": "Edit draft review",
            },
            {
                "text": "Review system and scope",
            },
        ]
        data["summary"] = self._get_summary(assessment)
        return data

    def form_valid(self, form):
        """
        Processes a valid form submission and executes logic based on the specified
        action within the form. Handles custom behavior for the "confirm" action
        including processing of system details and review scope, along with updating
        the review's status.

        :param form: The submitted form instance containing cleaned data.
        :type form: Form
        :return: The result of the parent class's form_valid method.
        """
        result = super().form_valid(form)
        action = form.cleaned_data["action"]

        def lower_snake_case(string: str):
            return string.lower().replace(" ", "_")

        if action == "confirm":
            #  This means they agreed to what was displayd on the page.
            #  So build the same data and save it as confirmed.
            summary = self._get_summary(self.object.assessment)
            self.logger.info(f"Updating review {self.object.id} with confirmed system and scope")
            self.object.confirm_system_and_scope_completed(
                {
                    lower_snake_case("System details"): {
                        lower_snake_case(item.name): item.value for item in summary["System details"]
                    },
                    lower_snake_case("The scope of this review"): {
                        lower_snake_case(item.name): item.value for item in summary["The scope of this review"]
                    },
                }
            )

            # Move to in_progress if still in to_do
            if self.object.status == "to_do":
                self.object.status = "in_progress"
                self.logger.info(f"Moving review {self.object.id} to in_progress")
            self.object.save()

        return result

    def _get_summary(self, assessment) -> dict[str, list[DetailEntry]]:
        return {
            "System details": [
                DetailEntry("System name", assessment.system.name, False),
                DetailEntry("System description", assessment.system.get_system_type_display(), True),
                DetailEntry("Previous GovAssure self-assessments", assessment.system.get_last_assessed_display(), True),
                DetailEntry("System ownership", assessment.system.get_system_owner_display(), True),
                DetailEntry("Hosting and connectivity", assessment.system.get_hosting_type_display(), True),
                DetailEntry("Corporate services", assessment.system.get_corporate_services_display(), True),
                DetailEntry("Other corporate services", assessment.system.corporate_services_other, True),
            ],
            "The scope of this review": [
                DetailEntry("Self-assessment reference number", assessment.reference, False),
                DetailEntry("Review type", assessment.get_review_type_display(), False),
                DetailEntry("Government CAF profile", assessment.get_caf_profile_display(), False),
                DetailEntry("CAF version", assessment.get_framework_display(), False),
            ],
        }


class EditReviewSystemView(BaseReviewMixin, UpdateView):
    """
    EditReviewSystemView is a Django class-based view for managing system updates within a review process.

    This view allows retrieving and updating a System object within the context of a specific review.
    It extends functionality for role-based access control, form handling, and managing review-specific
    contextual data to ensure correct modifications during an edit operation.

    The class also logs changes made to the system, records actions for auditing, and leverages dynamic
    form generation for flexibility in field management.

    :ivar model: The model associated with this view.
    :type model: Model
    :ivar template_name: The path to the template used for rendering this view.
    :type template_name: str
    :ivar login_url: The URL redirection path used for users who are not logged in.
    :type login_url: str
    :ivar logger: Logger instance for logging operations and events within the view.
    :type logger: logging.Logger
    """

    model = System
    template_name = "review/edit-system.html"
    logger = logging.Logger("EditReviewSystemView")

    def get_object(self, queryset=None) -> System:
        """
        Get the system object from the review information.
        I am using the review id for this as this is carried out by the review scope.
        :param queryset:
        :return:
        """
        return (
            self.get_reviews_for_user(
                SessionUtil.get_current_user_profile(self.request),  # type: ignore
                configuration=Configuration.objects.get_default_config(),
            )
            .filter(id=self.kwargs["pk"])
            .get()
            .assessment.system
        )

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["breadcrumbs"] = [
            {
                "url": reverse("system-and-scope", kwargs={"pk": self.kwargs["pk"]}),
                "text": "Back",
                "class": "govuk-back-link",
            },
        ]
        data["review"] = (
            self.get_reviews_for_user(
                SessionUtil.get_current_user_profile(self.request),
                configuration=Configuration.objects.get_default_config(),
            )
            .filter(id=self.kwargs["pk"])
            .first()
        )
        data["field_name"] = self.map_to_field(self.kwargs["field_to_change"])
        data["current_assessment_period"] = Configuration.objects.get_default_config().get_current_assessment_period()

        return data

    def get_form_class(self):
        """
        Generates and returns a dynamic form class based on provided field mappings and kwargs.

        This method dynamically creates a form class tailored to include only the fields
        mapped to the key specified in the provided kwargs. The form class is based on
        the ``ModelForm`` class and utilizes the ``System`` model for its configuration.
        Each key in the mapping corresponds to a specific field in the ``System`` model.

        :raises KeyError: If an invalid key is passed in kwargs or if the key does not have
                          a corresponding field in the defined mapping.

        :rtype: Type[ModelForm]
        :return: A dynamically generated form class tailored to the provided field configuration.
        """

        def generate_form(**kwargs):
            """
            Generates a dynamic Django model form class with fields filtered based on a specific
            condition determined by the provided keyword arguments.

            :param kwargs: Arbitrary keyword arguments. Must include "field_to_change" as a key,
                which designates the field that determines the filtered fields in the form.
            :return: The dynamically generated Django model form class based on the input parameters.
            :rtype: Type[ModelForm]
            """

            class DynamicForm(ModelForm):
                class Meta:
                    model = System
                    fields = list(
                        filter(
                            # We need to capture corporate_services_other with corporate_services
                            # thats why we have the startswith check below
                            lambda x: x.startswith(self.map_to_field(kwargs["field_to_change"])),
                            [
                                "last_assessed",
                                "system_type",
                                "system_owner",
                                "hosting_type",
                                "corporate_services",
                                "corporate_services_other",
                            ],
                        )
                    )

                def clean(self):
                    cleaned_data = super().clean()
                    corporate_services = cleaned_data.get("corporate_services")
                    corporate_services_other = cleaned_data.get("corporate_services_other")
                    if corporate_services:
                        if corporate_services[0] == "other":
                            if not corporate_services_other:
                                self.add_error(
                                    "corporate_services_other", "Please enter a description of the corporate services."
                                )
                        else:
                            # No need to keep the other corporate services description.
                            cleaned_data["corporate_services_other"] = ""
                    return cleaned_data

            return DynamicForm

        return generate_form(**self.kwargs)

    def form_valid(self, form):
        result = super().form_valid(form)
        self.record_change(form)
        return result

    def map_to_field(self, key: str) -> str:
        field_mapping = {
            "System description": "system_type",
            "Previous GovAssure self-assessments": "last_assessed",
            "System ownership": "system_owner",
            "Hosting and connectivity": "hosting_type",
            "Corporate services": "corporate_services",
        }
        return field_mapping[key]

    def record_change(self, form: ModelForm):
        """
        Updates a field in a form, records the change with detailed information about the modification,
        and updates the corresponding `Review` object. This function ensures that if the value of a field
        has been modified in the form compared to its initial value, the change is documented along with
        metadata for auditing purposes.

        :param form: The `ModelForm` instance containing the new and initial data for the field that
            may need to be updated.
        :type form: ModelForm

        :return: None
        """
        if self.request.user.is_authenticated:
            field_to_change = self.map_to_field(self.kwargs["field_to_change"])
            if form.cleaned_data[field_to_change] != form.initial[field_to_change]:
                review = (
                    self.get_reviews_for_user(
                        user_profile=SessionUtil.get_current_user_profile(self.request),  # type: ignore
                        configuration=Configuration.objects.get_default_config(),
                    )
                    .filter(id=self.kwargs["pk"])
                    .get()
                )

                self.logger.info(
                    f"Updating review {self.kwargs['pk']} with modified system {field_to_change} "
                    f"value {form.cleaned_data[field_to_change]}"
                    f"from {form.initial[field_to_change]}"
                )

                review.record_assessor_action(
                    "modify",
                    {
                        "what": "system",
                        "id": self.object.id,
                        "when": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        "description": f'Updated the field {self.kwargs["field_to_change"]} : '
                        f"{form.initial[field_to_change]} to {form.cleaned_data[field_to_change]}.",
                    },
                )
                review.last_updated_by = self.request.user
                review.reset_system_and_scope_completed()
                review.save()

    def get_success_url(self):
        return reverse(
            "system-and-scope",
            kwargs={
                "pk": self.kwargs["pk"],
            },
        )


class ShowReportView(BaseReviewMixin, DetailView):
    """
    This view is used to display a detailed report of a specific review in a particular version.

    ShowReportView is a specialized view that inherits from BaseReviewMixin and DetailView.
    It provides context data specific to the review report being displayed, including the
    selected version of the review and breadcrumbs for navigation. This class does not
    allow editing of any fields.

    :ivar model: The model representing the review.
    :type model: Review
    :ivar template_name: The template used for rendering the review report view.
    :type template_name: str
    :ivar fields: A list of fields that can be edited in this view.
    :type fields: list
    """

    model = Review
    template_name = "review/review-report.html"
    # No fields to edit, we manually update if needed
    fields: list[str] = []

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        version = self.kwargs["version"]
        data["object_version"] = self.object.get_version(version).instance
        data["version"] = version
        data["breadcrumbs"] = [
            {
                "url": reverse("my-account"),
                "text": "My account",
            },
            {
                "url": reverse("review-history", kwargs={"pk": self.object.id}),
                "text": "Report history",
            },
            {
                "text": "View Report",
            },
        ]
        return data


class DownloadReport(ShowReportView):
    """
    Handles the PDF generation and response for a downloadable report.

    This class is responsible for rendering a report's HTML as a PDF and serving it
    as an HTTP response. It integrates with Django templates and uses WeasyPrint
    for PDF generation. The purpose of the class is to provide a mechanism for users
    to download specific versions of a report in PDF format. The generated PDF
    includes references to static assets (e.g., CSS, images), which are resolved
    using absolute paths.

    :ivar logger: Logger instance used for logging in the class.
    :type logger: logging.Logger
    """

    logger: logging.Logger = logging.getLogger("DownloadReport")

    def get(self, request, *args, **kwargs):
        # Local import to avoid crashing the app if the dependency is not installed
        # on the developer machines
        from django.conf import settings
        from weasyprint import HTML

        # Disable style warnings from weasyprint
        logging.getLogger("weasyprint").setLevel(logging.ERROR)
        obj = self.get_object()
        version = kwargs["version"]
        obj = obj.get_version(version).instance
        context = {"object_version": obj, "object": obj, "version": version, "pdf_printing": True}

        html_string = render_to_string(self.template_name, context, request=request)

        # Generate PDF
        # Need to set the absolute path to the static files as pdf generation does not work with relative paths
        def custom_url_fetcher(url, timeout=10, ssl_context=None, http_headers=None):
            return default_url_fetcher(
                Path(settings.STATIC_ROOT + "/" + url.split("assets/")[-1]).as_uri(), timeout, ssl_context, http_headers
            )

        pdf = HTML(string=html_string, url_fetcher=custom_url_fetcher, base_url=Path(settings.STATIC_ROOT)).write_pdf()

        # Return as PDF response
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="UK-OFFICIAL-SENSITIVE-{obj.reference}.pdf"'
        return response
