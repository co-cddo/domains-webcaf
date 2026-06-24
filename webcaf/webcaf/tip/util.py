"""
This module contains a mixin class for handling user role management in tip-related views.
**Important**: This mixin should be used in all tip-related views.
"""
import logging
from functools import cached_property
from pathlib import Path
from typing import Any, Literal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import QuerySet
from django.db.transaction import atomic
from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone

from webcaf.webcaf.models import Configuration, RecommendationAction, Tip, UserProfile
from webcaf.webcaf.utils.permission import UserRoleCheckMixin
from webcaf.webcaf.utils.review import (
    Recommendation,
    RecommendationGroup,
    get_review_recommendations,
)
from webcaf.webcaf.utils.session import SessionUtil
from webcaf.webcaf.utils.to_spreadsheet import (
    review_to_tip_template_excel,
    tip_to_excel,
)

RecommendationType = Literal["priority", "other", "all"]
InternalRecommendationType = Literal["priority", "normal", "all"]

# Maps the view-facing recommendation type to the value expected by get_review_recommendations.
_REVIEW_FILTER_BY_TYPE: dict[RecommendationType, InternalRecommendationType] = {
    "priority": "priority",
    "other": "normal",
    "all": "all",
}


def get_recommendation_list(tip: Tip, recommendation_type: RecommendationType) -> list[RecommendationGroup]:
    """
    Find the correct recommendation group based on the specified recommendation type.
    :param tip: The tip object for which recommendations are being retrieved.
    :param recommendation_type: The type of recommendation to filter by, either "priority", "other", or "all".
    :return: A list of RecommendationGroup objects that match the specified recommendation type.
    """
    try:
        review_filter: InternalRecommendationType = _REVIEW_FILTER_BY_TYPE[recommendation_type]
    except KeyError as exc:
        raise ValueError(f"Invalid recommendation type: {recommendation_type}") from exc
    return list(get_review_recommendations(tip.review, review_filter))


class RecommendationService:
    """
    Handles recommendation services, including filtering, retrieving, and exporting
    recommendation data, as well as generating summary reports and rendering PDFs
    or Excel files for reports.

    This service integrates and filters recommendation data for a given tip and
    HTTP request context. It supports generating and exporting reports in various
    formats, allowing interaction with filtered datasets based on custom criteria.
    The class acts as a layer for processing, filtering, and presenting recommendations
    alongside user preferences and defined statuses.

    :ivar object: The tip associated with the recommendation service.
    :type object: Tip
    :ivar request: The current HTTP request context.
    :type request: HttpRequest
    :ivar objective_code: The objective code extracted from the GET query parameter.
    :type objective_code: str | None
    :ivar outcome_code: The outcome code extracted from the GET query parameter.
    :type outcome_code: str | None
    :ivar filter_status: The status filter extracted from the GET query parameter.
    :type filter_status: str | None
    """

    def __init__(self, tip: Tip, request: HttpRequest):
        self._review_filter_by_type = _REVIEW_FILTER_BY_TYPE
        self.object = tip
        self.request = request
        self.objective_code = request.GET.get("objective", None)
        self.outcome_code = request.GET.get("outcome", None)
        self.filter_status = request.GET.get("status", None)

    @property
    def logger(self):
        return logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def find_recommendation(
        self, recommendation_id: str, recommendation_type: RecommendationType
    ) -> tuple[Recommendation | None, RecommendationGroup | None]:
        """
        Finds a recommendation and its corresponding group based on the specified recommendation type.

        :param recommendation_id:
        :param recommendation_type: A string indicating the type of recommendation to search for.
            Accepts "priority" or "other".
        :return: A tuple containing the matched Recommendation object and its corresponding
            RecommendationGroup, or None if no match is found.
        """
        for recommendation, recommendation_group, _ in self.filter_recommendations(recommendation_type):
            if recommendation.id == recommendation_id:
                return recommendation, recommendation_group
        return None, None

    def find_next_recommendation(
        self, current_recommendation_id: str | None, recommendation_type: RecommendationType
    ) -> Recommendation | None:
        """
        Find the next recommendation after ``current_recommendation_id`` within the
        currently applied filters. Returns ``None`` if there is no successor or the
        current id is not in the filtered list.
        """
        if not current_recommendation_id:
            return None
        filtered = self.filter_recommendations(recommendation_type)
        for index, (recommendation, _, _) in enumerate(filtered):
            if recommendation.id == current_recommendation_id and index < len(filtered) - 1:
                return filtered[index + 1][0]
        return None

    def filter_recommendations(
        self, recommendation_type: RecommendationType
    ) -> list[tuple[Recommendation, RecommendationGroup, RecommendationAction | None]]:
        """
        Filters a list of recommendations grouped with their respective recommendation
        groups based on specified objective and status criteria.

        This method applies two levels of filtering:
        1. Filters recommendations by their associated objective if an objective code
           is specified in the GET parameters.
        2. Further refines the results based on the status of the recommendations
           (e.g., "not_reviewed" or specific action types) if a status is provided.

        :param recommendation_type:
        :return: A filtered list of tuples containing recommendations and their associated
            groups that match the provided filtering criteria.
        :rtype: list[tuple[Recommendation, RecommendationGroup,RecommendationAction]]
        """

        # First level filtering by objective / outcome
        recommendation_with_group = [
            (r, g, a)
            for r, g, a in self.recommendations_with_actions(recommendation_type)
            if (not self.objective_code or r.objective == self.objective_code)
            and (not self.outcome_code or r.outcome == self.outcome_code)
        ]

        if not self.filter_status:
            return recommendation_with_group

        # Filter the remaining data based on the status:
        #   - "not_reviewed" matches recommendations with no recorded action
        #   - any other status matches a recorded action of that action_type
        filtered_by_status: list[tuple[Recommendation, RecommendationGroup, RecommendationAction | None]] = []
        for recommendation, group, action in recommendation_with_group:
            if action is None:
                if self.filter_status == "not_reviewed":
                    filtered_by_status.append((recommendation, group, None))
            elif self.filter_status == "in_progress":
                if not action.is_reviewed:
                    filtered_by_status.append((recommendation, group, action))
            elif self.filter_status == action.action_type:
                filtered_by_status.append((recommendation, group, action))
        return filtered_by_status

    def generate_tag_line(self) -> str:
        """Return the summary tag line for a tip. Callers may pass a pre-flattened
        list of (recommendation, group) tuples to avoid a redundant lookup."""
        recommendation_with_group = self.recommendations_with_actions("all")

        no_action_count = 0
        actioned_count = 0
        not_reviewed_count = 0
        in_progress_count = 0
        for recommendation, _group, _ in recommendation_with_group:
            action = self.object.get_action(recommendation.id)
            if action is None:
                not_reviewed_count += 1
            elif action.recommendation_reviewed == "no":
                in_progress_count += 1
            elif action.action_type == "action_planned":
                actioned_count += 1
            else:
                no_action_count += 1
        return (
            f"{actioned_count} actions added · {in_progress_count} in progress · "
            f"{no_action_count} no action planned · {not_reviewed_count} not read yet"
        )

    def recommendations_with_actions(
        self, review_filter: RecommendationType
    ) -> list[tuple[Recommendation, RecommendationGroup, RecommendationAction | None]]:
        """Flatten review recommendations and pair each with its recorded action (if any)."""
        return [
            (r, g, self.object.get_action(r.id))
            for g in get_recommendation_list(self.object, review_filter)
            for r in g.recommendations
        ]

    def render_pdf(self, template_name: str, context: dict[str, Any]) -> HttpResponse:
        # Local imports to avoid crashing the app if weasyprint is not installed
        # on developer machines.
        from django.conf import settings
        from weasyprint import HTML, default_url_fetcher

        context["pdf_printing"] = True
        self.logger.info(f"Downloading tip {self.object.pk} for user {self.request.user.pk}")
        html_string = render_to_string(template_name, context, request=self.request)

        # Resolve static asset URLs to absolute file paths — weasyprint cannot
        # fetch them via the relative URLs Django emits.
        def custom_url_fetcher(url, timeout=10, ssl_context=None, http_headers=None):
            return default_url_fetcher(
                Path(settings.STATIC_ROOT + "/" + url.split("assets/")[-1]).as_uri(),
                timeout,
                ssl_context,
                http_headers,
            )

        pdf_file = HTML(
            string=html_string, url_fetcher=custom_url_fetcher, base_url=Path(settings.STATIC_ROOT)
        ).write_pdf()

        reference = self.object.review.assessment.reference
        self.logger.info(f"Generated TIP PDF for assessment {reference}")
        response = HttpResponse(pdf_file, content_type="application/pdf")
        response["Content-Disposition"] = f"filename=UK-OFFICIAL-SENSITIVE-TIP_{reference}.pdf"
        return response

    def render_excel(self, context: dict[str, Any]) -> HttpResponse:
        """
        Generates the XLS representation of the TIP
        :param context:
        :return:
        """
        response = HttpResponse(
            tip_to_excel(self.object, context),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'filename="UK-OFFICIAL-SENSITIVE-TIP_{self.object.reference}.xlsx"'
        return response

    def render_template(self, context: dict[str, Any]) -> HttpResponse:
        """
        Generates the XLS template to be used
        for offline information gathering
        :param context:
        :return:
        """
        response = HttpResponse(
            review_to_tip_template_excel(self.object.review),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'filename="UK-OFFICIAL-SENSITIVE-TIP_{self.object.reference}_TEMPLATE.xlsx"'
        return response


class BaseTipMixin(UserRoleCheckMixin):
    """
    Mixin providing base functionality for tip-related user role management.

    The purpose of this class is to handle user access control for tip-related
    features by enforcing and verifying role-based permissions.

    :ivar login_url: URL used for routing users to the appropriate login page for
        authentication.
    :type login_url: str
    """

    login_url = reverse_lazy("oidc_authentication_init")  # OIDC login route
    logger: logging.Logger
    request: HttpRequest

    def __init_subclass__(cls, **kwargs):
        """
        Method that is automatically called when a class is subclassed. It allows customization
        of behavior for the subclass. This implementation sets up a logger instance for the
        subclass, giving it a logger named after the class.

        :param kwargs: Arbitrary keyword arguments passed to the subclass initialization.
        """
        super().__init_subclass__(**kwargs)
        cls.logger = logging.getLogger(cls.__name__)

    @cached_property
    def recommendation_service(self) -> RecommendationService:
        return RecommendationService(
            self.get_object(),
            self.request,
        )

    def get_allowed_roles(self) -> list[str]:
        return ["cyber_advisor", "organisation_lead", "organisation_user"]

    def get_tip_for_user(self, user_profile: UserProfile | None, configuration: Configuration) -> QuerySet[Tip, Tip]:
        """
        Determines and filters the queryset of `Tip` instances accessible to a given user profile based on their organizational
        context and associated assessments' statuses. This method ensures access restrictions depending on the user profile and
        relies on appropriate filtering based on the configuration and role.

        :param user_profile: An optional user profile object representing the individual whose accessible tips are being queried.
                            If not provided, an exception is raised.
        :type user_profile: UserProfile | None

        :param configuration: A configuration object used to adjust or define criteria related to the querying process for tips.
        :type configuration: Configuration

        :return: A filtered queryset of tips adhering to the specified organizational and status-based constraints.
        :rtype: QuerySet[Tip, Tip]
        """

        if not user_profile:
            raise PermissionDenied("User profile not found")

        # Confirm the tip belongs to the user's organization
        # and its review is finalised
        base_filter = (
            Tip.objects.filter(
                review__assessment__status__in=["submitted"],
                review__assessment__system__organisation=user_profile.organisation,
                review__assessment__review_type="independent",
            )
            .exclude(review__review_data__review_finalised__review_finalised_at=None)
            .select_related("review", "review__assessment")
        )

        # All other roles (org lead and the cyber advisor) will see everything
        return base_filter

    def get_queryset(self):
        configuration = Configuration.objects.get_default_config()
        return self.get_tip_for_user(SessionUtil.get_current_user_profile(self.request), configuration)

    def get_object(self, queryset=None):
        """
        Override the get_object method to set the can_edit flag based on user role and tip status.
        """
        obj = super().get_object(queryset)
        if obj:
            current_profile = SessionUtil.get_current_user_profile(self.request)
            # Set the editable flag here
            # current profile role will always be one of the allowed roles (see get_allowed_roles), we just need make
            # sure this role is not in the read only roles
            obj.can_edit = current_profile and current_profile.role not in self.get_read_only_roles()
            # If it is submitted, then we cannot edit it
            if obj.is_submitted:
                obj.can_edit = False
        return obj

    def get_read_only_roles(self):
        return [
            "cyber_advisor",
        ]

    @atomic
    def form_valid(self, form):
        """
        Handle form validation and save the form instance.

        This method overrides the default form_valid behavior to catch ValidationErrors
        raised by the Review model's save() method. If a ValidationError occurs, it adds
        the error message to the form and returns form_invalid.

        The Review model's save() method can raise ValidationErrors for:
        - Attempting to modify review_data on a completed review
        - Attempting to save when can_edit is False
        - Attempting to save when the data has been updated by another user (optimistic locking)

        :param form: The form instance to validate and save
        :type form: Form
        :return: Response redirecting to success_url or rendering form with errors
        :rtype: HttpResponse
        """
        try:
            current_profile = SessionUtil.get_current_user_profile(self.request)
            form.instance.last_updated_by = current_profile.user
            # Pass the user and the action time to the form data
            form.cleaned_data["actioned_by"] = current_profile.user.id
            form.cleaned_data["actioned_time"] = timezone.now().isoformat()
            return super().form_valid(form)
        except ValidationError as e:
            # Add the validation error to the form's non-field errors
            # ValidationError.messages contains the list of error messages
            if hasattr(e, "message"):
                form.add_error(None, e.message)
            else:
                # For ValidationErrors with multiple messages or dict-based errors
                for message in e.messages:
                    form.add_error(None, message)
            return self.form_invalid(form)
