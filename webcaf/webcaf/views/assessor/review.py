import logging
from collections import namedtuple

from django.db.models import QuerySet
from django.forms import ChoiceField, ModelForm
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, TemplateView, UpdateView

from webcaf.webcaf.models import Assessor, Configuration, Review, System, UserProfile
from webcaf.webcaf.utils.permission import UserRoleCheckMixin
from webcaf.webcaf.utils.session import SessionUtil

"""
This module contains the views for the review section of the assessor dashboard.

It is **important** that the BaseReviewMixin is used in all views within this module.
This ensures that only users with the appropriate roles can access the views.

NOTE:
Also, any query for the review object is filtered by the current organisation and role of the user.
This ensures that only reviews for the current organisation are displayed.

"""


class BaseReviewMixin(UserRoleCheckMixin):
    """
    Mixin providing base functionality for review-related user role management.

    The purpose of this class is to handle user access control for review-related
    features by enforcing and verifying role-based permissions.

    :ivar login_url: URL used for routing users to the appropriate login page for
        authentication.
    :type login_url: str
    """

    login_url = reverse_lazy("oidc_authentication_init")  # OIDC login route

    def get_allowed_roles(self) -> list[str]:
        return [
            "cyber_advisor",
            "organisation_lead",
            "reviewer",
            "assessor",
        ]

    def get_reviews_for_user(self, user_profile: UserProfile, configuration: Configuration) -> QuerySet[Review, Review]:
        """
        Retrieve reviews associated with a given user profile and configuration.

        This method fetches reviews from the database based on the user's role
        and the organisation's assessment period. It distinguishes between users
        holding certain roles (e.g., "organisation_lead", "cyber_advisor") and
        others, to filter assessments accordingly. The filtering criteria include
        the status of the assessment, whether the assessor is active, the
        organisation associated with the assessment system, and the current
        assessment period.

        :param user_profile: Represents the user's profile, containing information
            about roles and the organisation the user is associated with.
        :type user_profile: UserProfile
        :param configuration: Configuration settings, including methods to retrieve
            the current assessment period.
        :type configuration: Configuration
        :return: A queryset of reviews filtered according to the provided user profile
            and configuration.
        :rtype: QuerySet[Review, Review]
        """
        base_filter = Review.objects.filter(
            assessed_by__is_active=True,
            assessment__status__in=["submitted"],
            assessment__system__organisation=user_profile.organisation,
            assessment__assessment_period=configuration.get_current_assessment_period(),
        )
        if user_profile.role in ["organisation_lead", "cyber_advisor"]:
            return base_filter

        return base_filter.filter(
            assessed_by__in=Assessor.objects.filter(
                members=user_profile,
                organisation=user_profile.organisation,
                is_active=True,
            )
        )


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

    def get_queryset(self):
        return self.get_reviews_for_user(
            SessionUtil.get_current_user_profile(self.request), configuration=Configuration.objects.get_default_config()
        )

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

    def get_queryset(self):
        return self.get_reviews_for_user(
            SessionUtil.get_current_user_profile(self.request), configuration=Configuration.objects.get_default_config()
        )

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
                "url": reverse("my-account"),
                "text": "My account",
            },
            {
                "url": reverse("edit-review", kwargs={"pk": self.kwargs["pk"]}),
                "text": "Edit draft review",
            },
            {
                "text": "Review system and scope",
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
