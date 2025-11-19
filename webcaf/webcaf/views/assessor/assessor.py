from typing import Optional

from django.forms import ChoiceField, Form
from django.forms.models import ModelForm, ModelMultipleChoiceField
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    DeleteView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from webcaf.webcaf.models import Assessment, Assessor, Review, UserProfile
from webcaf.webcaf.utils.permission import UserRoleCheckMixin
from webcaf.webcaf.utils.session import SessionUtil


class YesNoForm(Form):
    """
    Represents a form for selecting Yes or No.
    """

    yes_no = ChoiceField(choices=[("yes", "Yes"), ("no", "No")], required=True, label="")

    def __init__(self, *args, **kwargs):
        yes_no_label = kwargs.pop("yes_no_label", "")
        super().__init__(*args, **kwargs)
        self.fields["yes_no"].initial = "no"
        self.fields["yes_no"].label = yes_no_label


class AssessorIndexView(UserRoleCheckMixin, TemplateView):
    """
    Provides a view for assessors' account page.

    This class-based view is designed for authenticated users to display the assessor's
    account page. It ensures that only logged-in users can access the page, and it provides
    necessary context data such as the current user profile and associated reviews.

    :ivar template_name: Path to the template file that renders the assessor's account page.
    :type template_name: str
    :ivar login_url: URL route to initiate the OIDC login process for unauthenticated users.
    :type login_url: str
    """

    template_name = "user-pages/assessor/my-account.html"
    login_url = reverse_lazy("oidc_authentication_init")  # OIDC login route

    def get_allowed_roles(self) -> list[str]:
        return [
            "cyber_advisor",
            "organisation_lead",
            "reviewer",
            "assessor",
        ]

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        data["reviews"] = Review.objects.filter(
            assessed_by__is_active=True,
            assessment__status__in=["submitted"],
            assessment__system__organisation=data["current_profile"].organisation,
        )
        return data


class AssessorsView(UserRoleCheckMixin, ListView):
    """
    Handles the view for assessors, allowing access to respective roles and rendering a list of assessment-related
    information. Provides context data including current user profile, breadcrumbs, and forms for the template.

    The view ensures that only authorized user roles can access the information and retrieves a queryset of active
    organisations assessed by the current user's profile.

    :ivar model: The model used for the view, which is Assessor.
    :type model: Model
    :ivar template_name: The template used for rendering the view.
    :type template_name: str
    """

    model = Assessor
    template_name = "assessor/list.html"

    def get_allowed_roles(self) -> list[str]:
        return [
            "cyber_advisor",
            "organisation_lead",
        ]

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        data["breadcrumbs"] = [{"url": reverse("my-account"), "text": "Back", "class": "govuk-back-link"}]
        data["form"] = YesNoForm
        return data

    def get_queryset(self):
        """
        Retrieves and returns a queryset of active organisations assessed by the current user's profile,
        ordered by activity status, last update time, and name.

        :return: A queryset of active organisations assessed by the current user's profile,
                 sorted by `is_active`, `last_updated`, and `name`.
        :rtype: QuerySet
        """
        return (
            SessionUtil.get_current_user_profile(self.request)
            .organisation.assessors.filter(is_active=True)
            .order_by("-last_updated", "name")
        )


class AssessorForm(ModelForm):
    """
    Representation of a form for managing `Assessor` model objects.

    This class defines a form with configuration for the `Assessor` model. It includes
    both standard fields directly from the model and additional custom fields for enhanced
    functionality. The form is designed to allow editing, validation, and submission of
    `Assessor` model data while providing optional relationships with assessments.

    :ivar assessments: Represents a selectable field for related assessments. Non-mandatory and allows
        the filtering of assessments by `status=submitted` and their associated organisational system.
    :type assessments: ModelMultipleChoiceField
    """

    assessments = ModelMultipleChoiceField(required=False, queryset=Assessment.objects.none(), label="Assessments")

    class Meta:
        model = Assessor
        fields = ["name", "email", "contact_name", "phone_number", "address", "assessor_type", "members", "assessments"]

    def __init__(self, *args, **kwargs):
        """
        Initializes the form with the provided arguments and keyword arguments.
        Customizes the behavior and initial values of specific fields such as
        `members` and `assessments`, ensuring the form dynamically filters and
        sets initial field values based on the current context.

        :param args: Positional arguments for the form initialization.
        :type args: tuple
        :param kwargs: Keyword arguments for the form initialization.
            The `current_user_profile` is expected in `kwargs`, which is used to
            prefilter the queryset for the `assessments` field.
        :type kwargs: dict
        """

        current_user_profile: UserProfile = kwargs.pop("current_user_profile")  # type: ignore
        super().__init__(*args, **kwargs)
        self.fields["members"].required = False
        self.fields["assessments"].required = False
        self.fields["assessments"].queryset = Assessment.objects.filter(
            status__in=["submitted"], system__organisation=current_user_profile.organisation
        )
        if self.instance.pk:
            # Set the initial values for the form fields
            self.fields["assessments"].initial = [review.assessment for review in self.instance.reviews.all()]


class EditAssessorView(UserRoleCheckMixin, UpdateView):
    """
    Manages the creation and update processes for Assessor objects, handling specific
    role-based access and data associations with the logged-in user's organisation.

    This view allows users with specific roles to manage Assessor objects. It integrates
    role checking, context data injection, and associations between Assessors, organisation
    members, and assessments. It provides custom success handling and supports dynamic
    form generation for the related objects.

    :ivar form_class: The Django form class used for handling Assessor data.
    :type form_class: AssessorForm
    :ivar template_name: The template used to render the view.
    :type template_name: str
    """

    models = Assessor
    form_class = AssessorForm
    template_name = "assessor/details.html"

    def get_form_kwargs(self):
        # Pass the current user profile to the form
        # this is needed for filtering the assessments queryset
        return super().get_form_kwargs() | {"current_user_profile": SessionUtil.get_current_user_profile(self.request)}

    def get_allowed_roles(self) -> list[str]:
        return [
            "cyber_advisor",
            "organisation_lead",
        ]

    def get_object(self, queryset=None):
        if "pk" in self.kwargs:
            # If editing an Assessor, filter by organisation to make sure we only edit allowed Assessors
            return Assessor.objects.filter(
                id=self.kwargs["pk"],
                id__in=SessionUtil.get_current_user_profile(self.request)
                .organisation.assessors.filter(is_active=True)
                .values_list("id", flat=True),
            ).first()
        return None

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["assessor_types"] = Assessor.ASSESSOR_TYPES
        data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        data["breadcrumbs"] = [{"url": reverse("assessor-list"), "text": "Back", "class": "govuk-back-link"}]
        return data

    def get_success_url(self):
        return reverse_lazy("assessor-list")

    def form_valid(self, form):
        """
        Processes the form data when valid and performs actions related to updating
        and associating data with the current form instance and associated objects.

        :param form: The form instance containing data to process.
        :type form: Form
        :return: The result of the parent's form_valid method.
        :rtype: HttpResponseRedirect
        """
        # Set the current user as the last_updated_by field
        form.instance.last_updated_by = self.request.user
        form.instance.organisation = SessionUtil.get_current_user_profile(self.request).organisation
        return_value = super().form_valid(form)
        if form.cleaned_data.get("members"):
            # Go through all the members and add the current assessor to them.
            members_to_add = []
            for member in form.cleaned_data["members"]:
                if member.organisation == self.object.organisation and member.role in ["assessor", "reviewer"]:
                    members_to_add.append(member)
            self.object.members.set(members_to_add)
        if form.cleaned_data.get("assessments"):
            # Go through all the selected assessments and add the current assessor to them.
            assigned_reviews = []
            for assessment in form.cleaned_data["assessments"]:
                review, created_ = Review.objects.get_or_create(assessment=assessment, assessed_by=self.object)
                assigned_reviews.append(review)
            self.object.reviews.set(assigned_reviews)

        return return_value


class RemoveAssessorView(UserRoleCheckMixin, DeleteView):
    model = Assessor
    form_class = YesNoForm
    template_name = "assessor/delete-assessor.html"

    object: Optional[Assessor]  # explicitly type self.object for mypy

    def get_allowed_roles(self) -> list[str]:
        return [
            "cyber_advisor",
            "organisation_lead",
        ]

    def get_success_url(self):
        return reverse_lazy("assessor-list")

    def get_object(self, queryset=...):
        # Make sure the assessor belongs to the current organisation
        def raise_Http404(msg):
            raise Http404(msg)

        return Assessor.objects.filter(
            id=self.kwargs["pk"],
            id__in=SessionUtil.get_current_user_profile(self.request)
            .organisation.assessors.filter(is_active=True)
            .values_list("id", flat=True),
        ).first() or raise_Http404("Object does not exist")

    def form_valid(self, form):
        success_url = self.get_success_url()
        if form.cleaned_data.get("yes_no") == "yes":
            self.object.last_updated_by = self.request.user
            self.object.is_active = False
            self.object.save()
        return HttpResponseRedirect(success_url)


class CreateOrSkipAssessorView(UserRoleCheckMixin, FormView):
    """
    Utility action to decide to create a new assessor or go back to the
    home screen.
    """

    form_class = YesNoForm
    template_name = "assessor/list.html"

    def get_allowed_roles(self) -> list[str]:
        return ["cyber_advisor", "organisation_lead"]

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {"yes_no_label": "Add new assessor?"}

    def get_success_url(self):
        if self.request.POST.get("yes_no") == "yes":
            return reverse("add-assessor")
        else:
            return reverse("my-account")

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        data["assessor_list"] = data["current_profile"].organisation.assessed_by
        return data
