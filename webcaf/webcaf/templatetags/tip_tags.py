from django import template

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
    return f"{actioned_count} actions added {not_actioned_count} no action reasons recorded"
