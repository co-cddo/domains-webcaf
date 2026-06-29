from django import template
from django.urls import reverse

from webcaf.webcaf.models import RecommendationAction, Tip
from webcaf.webcaf.utils.review import Recommendation, RecommendationGroup

register = template.Library()


@register.simple_tag()
def get_recommendation_action(recommendation: Recommendation, tip_object: Tip) -> RecommendationAction | None:
    """
    Get the recommendation action for a given recommendation and object.

    :param recommendation: The recommendation object.
    :param tip_object: The tip object.
    :return: The recommendation action or None if not found.
    """
    return tip_object.get_action(recommendation.id)


@register.simple_tag()
def actioned_and_not_actioned_counts(
    recommendations: list[tuple[Recommendation, RecommendationGroup, RecommendationAction]]
) -> str:
    """
    Calculate the counts of actioned and not actioned recommendations for a tip.

    :return: A dictionary with 'actioned_count' and 'not_actioned_count' keys.
    """
    actioned_count = 0
    not_actioned_count = 0
    for _, _, action in recommendations:
        if action.action_type == "action_planned":
            actioned_count += 1
        else:
            not_actioned_count += 1
    return f"{len(recommendations)} recommendations . {actioned_count} action{'s' if actioned_count != 1 else ''} added"


@register.simple_tag()
def tip_url(tip_id: int, recommendation_id: int, recommendation_type: str, query_string: str) -> str:
    """
    Generates a dynamic URL for a tip recommendation action.

    This function constructs a URL using the provided IDs, recommendation type,
    and a query string. It is mainly used in templates where a dynamic link
    to a tip recommendation action is required.

    :param tip_id: The ID of the tip.
    :type tip_id: int
    :param recommendation_id: The ID of the recommendation.
    :type recommendation_id: int
    :param recommendation_type: The type of recommendation as a string.
    :type recommendation_type: str
    :param query_string: The query string to append to the URL.
    :type query_string: str
    :return: A dynamically generated URL string for the tip recommendation action.
    :rtype: str
    """
    return (
        reverse("tip:recommendation-action", args=[tip_id, recommendation_type, recommendation_id]) + f"?{query_string}"
    )
