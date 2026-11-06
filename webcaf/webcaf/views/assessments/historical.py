import logging
from typing import NamedTuple

from django.urls import reverse
from django.views.generic import TemplateView

from webcaf.webcaf.models import Assessment, Configuration, Review, Tip
from webcaf.webcaf.utils.permission import UserRoleCheckMixin
from webcaf.webcaf.utils.session import SessionUtil


class HistoryData(NamedTuple):
    """
    A named tuple to hold the data for each historical assessment entry.
    """

    assessment: Assessment
    review: Review | None
    tip: Tip | None


class HistoricalAssessmentView(UserRoleCheckMixin, TemplateView):
    """
    View for displaying historical assessments.

    This class is responsible for rendering the historical assessments page,
    providing the necessary context data and breadcrumbs for navigation.

    :ivar template_name: Path to the HTML template used for rendering the view.
    :type template_name: str
    """

    login_url = "/oidc/authenticate/"
    template_name = "assessment/historical-assessments.html"
    logger = logging.getLogger("HistoricalAssessmentView")

    def get_allowed_roles(self) -> list[str]:
        return ["organisation_lead", "organisation_user", "cyber_advisor"]

    def get_context_data(self, **kwargs):
        """
        Extends the context data for the view with additional data such as breadcrumbs,
        systems, and related assessments, reviews, and tips. Retrieves the current
        user profile and organisation, filters assessments based on their status
        and assessment period, and constructs a structured set of data for rendering
        in the view context.

        :param kwargs: Additional keyword arguments passed to the context data.
        :type kwargs: dict
        :return: A dictionary containing extended context data, including breadcrumbs
                 and systems with associated assessments, reviews, and tips.
        :rtype: dict
        """
        data = super().get_context_data(**kwargs)
        data["breadcrumbs"] = [
            {"url": reverse("my-account"), "text": "My account"},
            {"url": "#", "text": "Previous GovAssure submissions"},
        ]
        current_profile = SessionUtil.get_current_user_profile(self.request)
        current_organisation = current_profile.organisation
        # Only show assessments that are not in the current assessment period and in submitted status.
        assessments = {
            assessment.id: assessment
            for assessment in Assessment.objects.filter(
                system__organisation=current_organisation, status__in=["submitted"]
            )
            .exclude(
                assessment_period=Configuration.objects.get_default_config().get_current_assessment_period(),
            )
            .order_by("-created_on")
            .select_related("system", "system__organisation")
        }
        # Get the reviews and tips associated with the assessments, if they exist.
        reviews = {
            review.assessment.id: review
            # We only have one review assigned with each assessment, so we can use the assessment id as the key.
            for review in Review.objects.filter(
                assessment__in=assessments.keys(), status__in=["completed"]
            ).select_related("assessment")
        }
        # Only include tips that have been finalised.
        tips = {
            tip.review.assessment.id: tip
            for tip in Tip.objects.filter(review__assessment__in=assessments.keys())
            .exclude(review__review_data__review_finalised__review_finalised_at=None)
            .select_related("review", "review__assessment")
        }
        systems = {}
        for assessment in assessments.values():
            parts = assessment.assessment_period.split("/")
            key = f"20{parts[0]} to 20{parts[1]}"
            systems.setdefault(key, []).append(
                HistoryData(assessment, reviews.get(assessment.id), tips.get(assessment.id))
            )
        data["systems"] = systems
        data["current_profile"] = current_profile
        return data
