import datetime
import logging

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView, TemplateView, UpdateView

from webcaf.webcaf.models import Configuration, Tip, TipStatus
from webcaf.webcaf.tip.forms import (
    RecommendationActionForm,
    TipBulkReviewForm,
    TipReviewAnswersForm,
    TipSubmitForm,
)
from webcaf.webcaf.tip.util import (
    BaseTipMixin,
    RecommendationService,
    RecommendationType,
)
from webcaf.webcaf.utils.review import get_review_recommendations
from webcaf.webcaf.utils.session import SessionUtil


class TipIndexView(BaseTipMixin, TemplateView):
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

    template_name = "tip/list.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        data["breadcrumbs"] = [
            {
                "url": reverse("my-account"),
                "text": "Back",
                "class": "govuk-back-link",
            },
        ]
        configuration = Configuration.objects.get_default_config()
        data["tips"] = self.get_tip_for_user(data["current_profile"], configuration)
        return data


class TipDetailView(BaseTipMixin, DetailView):
    """
    View for displaying a single TIP summary information.
    Allow the user to select the priority and other recommendations to be
    reviewed and actioned.
    """

    model = Tip
    template_name = "tip/summary.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        data["breadcrumbs"] = [
            {
                "url": reverse("tip:list"),
                "text": "My account",
            },
            {
                "url": None,
                "text": "Edit draft TIP",
            },
        ]
        data["priority_recommendations_count"] = sum(
            1 for g in get_review_recommendations(self.object.review, "priority") for _ in g.recommendations
        )
        data["other_recommendations_count"] = sum(
            1 for g in get_review_recommendations(self.object.review, "normal") for _ in g.recommendations
        )
        data["tag_line"] = self.recommendation_service.generate_tag_line()
        return data


class TipRecommendationsView(BaseTipMixin, UpdateView):
    """
    View for managing TIP review recommendations.

    Displays the list of priority or other recommendations to be reviewed and actioned.
    """

    model = Tip
    template_name = "tip/recommendations.html"
    form_class = TipBulkReviewForm

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @property
    def recommendation_service(self):
        return RecommendationService(self.object, self.request)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        recommendation_type = self.kwargs.get("recommendation_type", "priority")

        data["breadcrumbs"] = [
            {
                "url": reverse("tip:list"),
                "text": "My account",
            },
            {
                "url": reverse(
                    "tip:edit",
                    kwargs={
                        "pk": self.object.pk,
                    },
                ),
                "text": "Edit draft TIP",
            },
            {
                "url": None,
                "text": "Priority recommendation and action"
                if recommendation_type == "priority"
                else "Other recommendations",
            },
        ]
        data["recommendation_type"] = recommendation_type
        data["caf_profile"] = self.object.review.assessment.caf_profile

        all_recommendations_with_actions = self.recommendation_service.recommendations_with_actions(recommendation_type)

        data["total_recommendations"] = len(all_recommendations_with_actions)
        filter_recommendations = self.recommendation_service.filter_recommendations(recommendation_type)
        data["all_recommendations"] = filter_recommendations
        data["objective_list"] = sorted({r.objective for r, _, _ in all_recommendations_with_actions})
        data["outcome_list"] = sorted({r.outcome for r, _, _ in all_recommendations_with_actions})
        data["objective"] = self.recommendation_service.objective_code or ""
        data["outcome"] = self.recommendation_service.outcome_code or ""
        data["status"] = self.recommendation_service.filter_status or ""
        data["tag_line"] = self.recommendation_service.generate_tag_line()

        if recommendation_type == "other":
            reviewed_count = sum(1 for r, _, action in filter_recommendations if action)
            if reviewed_count != len(filter_recommendations):
                data["show_bulk_update"] = True
        return data

    def form_valid(self, form: TipBulkReviewForm) -> HttpResponse:
        if form.cleaned_data["confirm_bulk_review"] != "yes":
            self.logger.info(  # type: ignore [attr-defined]
                f"User declined to mark remaining other recommendations as reviewed with no action planned for tip {self.object.id}"
            )
            return redirect("tip:edit", pk=self.object.id)

        recommendation_type_: RecommendationType = self.kwargs["recommendation_type"]
        # Only other recommendations can be actioned in bulk
        if recommendation_type_ != "other":
            return super().form_invalid(form)

        form.cleaned_data["filtered_recommendations_with_group"] = self.recommendation_service.filter_recommendations(
            recommendation_type_
        )
        successful_form_submission = super().form_valid(form)
        self.logger.info(
            f"Marked remaining other recommendations as reviewed with no action planned for tip {self.object.id}"
        )
        messages.success(
            self.request,
            "All remaining other recommendations have been marked as reviewed with no action planned.",
        )
        return successful_form_submission

    def get_success_url(self):
        base_url = reverse(
            "tip:recommendations",
            kwargs={"pk": self.kwargs["pk"], "recommendation_type": self.kwargs["recommendation_type"]},
        )
        query_string = QueryDict(self.request.META.get("QUERY_STRING", "")).urlencode()
        return f"{base_url}?{query_string}" if query_string else base_url


class TipRecommendationActionView(BaseTipMixin, UpdateView):
    """
    Action an individual recommendation for a tip.
    """

    form_class = RecommendationActionForm
    template_name = "tip/recommendation_action.html"
    model = Tip

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        recommendation_type = self.kwargs.get("recommendation_type", "priority")

        data["breadcrumbs"] = [
            {
                "url": reverse("tip:list"),
                "text": "My account",
            },
            {
                "url": reverse(
                    "tip:edit",
                    kwargs={
                        "pk": self.object.pk,
                    },
                ),
                "text": "Edit draft TIP",
            },
            {
                "url": reverse(
                    "tip:recommendations", kwargs={"pk": self.object.pk, "recommendation_type": recommendation_type}
                ),
                "text": "Respond to priority recommendation"
                if recommendation_type == "priority"
                else "Review other recommendation",
            },
            {
                "url": None,
                "text": self.kwargs.get("recommendation_id"),
            },
        ]
        data["recommendation_type"] = recommendation_type
        current_recommendation, current_group = self.recommendation_service.find_recommendation(
            self.kwargs.get("recommendation_id"), recommendation_type
        )
        data["current_recommendation"] = current_recommendation
        data["current_recommendation_group"] = current_group
        current_id = current_recommendation.id if current_recommendation else None
        data["next_recommendation"] = self.recommendation_service.find_next_recommendation(
            current_id, recommendation_type
        )
        data["tag_line"] = self.recommendation_service.generate_tag_line()
        data["mode"] = self.request.GET.get("mode", "view")
        return data

    _ACTION_DETAIL_FIELDS = (
        "action_not_planned_reason",
        "action_taken_description",
        "action_owner",
        "target_date_provided",
        "target_day_day",
        "target_day_month",
        "target_day_year",
        "target_date_unavailable_reason",
        "budget_available",
        "resources_available",
    )

    def get_initial(self):
        action_data = self.object.get_action(self.kwargs.get("recommendation_id"))
        if not action_data:
            # This is the first time this recommendation has been actioned.
            # Go through the last actioned filled and pick up the person the action
            # was assigned to, we use that as the default action owner
            last_actioned = list(
                sorted(
                    self.object.get_actions_with_owners().values(),
                    key=lambda x: datetime.datetime.fromisoformat(x["actioned_time"]),
                    reverse=True,
                )
            )
            return {"action_owner": last_actioned[0]["action_details"].get("action_owner") if last_actioned else ""}
        details = action_data.action_details or {}
        initial = {
            "recommendation_category": action_data.recommendation_category,
            "recommendation_actioned": action_data.action_type,
            "recommendation_id": action_data.recommendation_id,
            "recommendation_reviewed": action_data.recommendation_reviewed,
        }
        initial.update((field, details.get(field)) for field in self._ACTION_DETAIL_FIELDS)
        return initial

    def get_object(self, queryset: QuerySet | None = None) -> Tip:
        """
        Retrieves and returns an object, applying additional edit permissions based
        on the object's status.

        :param queryset: A QuerySet object to filter or retrieve the desired object.
                         If None, the default queryset is used.
        :type queryset: QuerySet | None
        :return: The retrieved object with updated edit permissions.
        :rtype: Tip
        """
        the_object: Tip = super().get_object(queryset)
        the_object.can_edit &= the_object.is_editable  # type: ignore [attr-defined]
        return the_object

    def form_invalid(self, form):
        return super().form_invalid(form)

    def form_valid(self, form: RecommendationActionForm):
        self.logger.info(
            f"Saving recommendation {form.cleaned_data.get('recommendation_id')} action for tip {self.kwargs['pk']}"
        )
        if self.object.is_answers_confirmed:
            self.logger.info(f"This will reset the answer confirmation for tip {self.kwargs['pk']}")
        return super().form_valid(form)

    def get_success_url(self) -> str:
        submit_action = self.request.POST.get("submit_action", "back_to_summary")
        recommendation_type_ = self.kwargs["recommendation_type"]

        if submit_action.endswith("back_to_summary"):
            base_url = reverse(
                "tip:recommendations",
                kwargs={"pk": self.kwargs["pk"], "recommendation_type": recommendation_type_},
            )
        elif submit_action.endswith("next_recommendation"):
            base_url = reverse(
                "tip:recommendation-action",
                kwargs={
                    "pk": self.kwargs["pk"],
                    "recommendation_id": self.request.POST.get("next_recommendation"),
                    "recommendation_type": recommendation_type_,
                },
            )
        elif submit_action.endswith("back_to_answers"):
            base_url = reverse(
                "tip:review-answers",
                kwargs={
                    "pk": self.kwargs["pk"],
                },
            )
        else:
            raise ValueError(f"Invalid submit action: {submit_action}")

        query_string = QueryDict(self.request.META.get("QUERY_STRING", "")).urlencode()
        return f"{base_url}?{query_string}" if query_string else base_url


class TipReviewAnswersView(BaseTipMixin, UpdateView):
    """
    Display the list of the answers the user provided and get
    their confirmation on their review of the TIP.
    """

    template_name = "tip/review_answers.html"
    model = Tip
    form_class = TipReviewAnswersForm

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        data["breadcrumbs"] = [
            {
                "url": reverse("tip:list"),
                "text": "My account",
            },
            {
                "url": reverse(
                    "tip:edit",
                    kwargs={
                        "pk": self.object.pk,
                    },
                ),
                "text": "Edit draft TIP",
            },
            {
                "url": None,
                "text": "Review answers",
            },
        ]

        data["priority_recommendations"] = self.recommendation_service.filter_recommendations("priority")
        data["other_recommendations"] = self.recommendation_service.filter_recommendations("other")
        data["tag_line"] = self.recommendation_service.generate_tag_line()
        return data

    def get_object(self, queryset: QuerySet | None = None) -> Tip:
        """
        Retrieve and customize the current object based on the user profile and object status.

        This method retrieves the object from the provided queryset or the default queryset if none is provided.
        The retrieved object is further updated to indicate if it can be edited, depending on the role
        of the current user's profile and the object's current status.

        :param queryset: Optional queryset used to retrieve the object. If None, the default queryset
                         is used.
        :type queryset: QuerySet | None
        :return: The retrieved object with its `can_edit` attribute updated based on the user's role
                 and the object's status.
        :rtype: Tip
        """
        user_profile = SessionUtil.get_current_user_profile(self.request)
        current_object: Tip = super().get_object(queryset)
        # Only organisation lead can edit
        if not user_profile or user_profile.role != "organisation_lead":
            current_object.can_edit = False  # type: ignore [attr-defined]

        current_object.can_edit &= current_object.status in [  # type: ignore [attr-defined]
            TipStatus.IN_PROGRESS,
        ]
        return current_object

    def form_valid(self, form: TipBulkReviewForm):
        """
        Handle form submission for bulk review of answers
        """
        if form.cleaned_data["submit_action"] == "yes":
            confirmed_by = SessionUtil.get_current_user_profile(self.request)
            self.logger.info(
                f"Confirming answers for TIP {self.object.pk} Assessment {self.object.review.assessment.reference}"
            )
            if not confirmed_by:
                raise ValueError("Cannot confirm answers without submitting user")
            form.cleaned_data["confirmed_by"] = confirmed_by.user.id
            form.cleaned_data["confirmed_at"] = timezone.now().isoformat()
            form.cleaned_data["confirmation_role"] = confirmed_by.role
            return super().form_valid(form)
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "tip:edit",
            kwargs={
                "pk": self.object.pk,
            },
        )


class TipSubmitView(BaseTipMixin, UpdateView):
    """
    After the answers have been reviewed, allow the user to submit the TIP for review.
    """

    template_name = "tip/submit.html"
    model = Tip
    form_class = TipSubmitForm

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        data["breadcrumbs"] = [
            {
                "url": reverse("tip:list"),
                "text": "My account",
            },
            {
                "url": reverse(
                    "tip:edit",
                    kwargs={
                        "pk": self.object.pk,
                    },
                ),
                "text": "Edit draft TIP",
            },
            {
                "url": None,
                "text": "Submit TIP",
            },
        ]
        return data

    def get_object(self, queryset=None) -> Tip:
        tip_object: Tip = super().get_object(queryset)
        if not tip_object.is_ready_to_submit:
            raise PermissionDenied("TIP is not ready to submit")
        return tip_object

    def form_valid(self, form: TipSubmitForm):
        if not form.cleaned_data["confirm"]:
            form.add_error("confirm", "You must confirm before submitting")
            return self.form_invalid(form)
        current_profile = SessionUtil.get_current_user_profile(self.request)
        form.cleaned_data["current_profile"] = current_profile
        self.logger.info(f"Submitted TIP for assessment {form.instance.review.assessment.reference}")
        return super().form_valid(form)

    def get_read_only_roles(self):
        return ["organisation_user", "cyber_advisor"]

    def get_success_url(self):
        return reverse("tip:confirmation", kwargs={"pk": self.object.pk})


class TipSubmissionConfirmationView(BaseTipMixin, DetailView):
    """
    Display the confirmation page after submitting.

    Shows the referfence and any additional information.
    """

    template_name = "tip/confirmation.html"
    model = Tip

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        return data


class TipReportView(BaseTipMixin, DetailView):
    """
    View for generating a report for a TIP.

    Displays the TIP details and any associated information for reporting purposes.
    This has three formats
     - default is the HTML report
     - PDF - the pdf version of the above htm
     - EXCEL - the excel representation of the data
    """

    template_name = "tip/report.html"
    model = Tip

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["current_profile"] = SessionUtil.get_current_user_profile(self.request)
        data["breadcrumbs"] = [
            {
                "url": reverse("tip:list"),
                "text": "My account",
            },
            {
                "url": None,
                "text": ("Draft " if self.object.status != "approved" else "") + "Targeted Improvement Plan (TIP)",
            },
        ]
        data["priority_recommendations"] = self.recommendation_service.filter_recommendations("priority")
        data["other_recommendations"] = self.recommendation_service.filter_recommendations("other")
        data["tag_line"] = self.recommendation_service.generate_tag_line()
        return data

    def get(self, request: HttpRequest, *args, **kwargs):
        self.object: Tip = self.get_object()
        mode = request.GET.get("mode")
        if mode == "pdf":
            return self.recommendation_service.render_pdf(self.template_name, self.get_context_data())
        if mode == "excel":
            return self.recommendation_service.render_excel(self.get_context_data())
        if mode == "template":
            return self.recommendation_service.render_template(self.get_context_data())
        return super().get(request, *args, **kwargs)
