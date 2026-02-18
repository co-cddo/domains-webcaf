"""
Recommendation is a named tuple representing a single recommendation with fields for id, title, text, objective (code),
and outcome (code).
On the UI, the title field is labelled as 'Risk' and this is the primary identifier for the recommendation.
"""
from typing import Any, Generator, Literal, NamedTuple

from webcaf.webcaf.caf.util import IndicatorStatusChecker
from webcaf.webcaf.models import Review

Recommendation = NamedTuple(
    "Recommendation", [("id", str), ("title", str), ("text", str), ("objective", str), ("outcome", str)]
)


class RecommendationGroup:
    """
    Represents a group of recommendations with a title and an index.

    The RecommendationGroup class is designed to organize and manage a collection
    of recommendations under a specified title. Each group is further indexed with
    a unique identifier for ordering or categorization purposes.

    :ivar title: The title of the recommendation group.
    :type title: str
    :ivar recommendations: A list of recommendations within the group.
    :type recommendations: list[Recommendation]
    :ivar group_index: The unique index of the recommendation group.
    :type group_index: int
    """

    def __init__(self, title: str, recommendations: list[Recommendation], group_index: int):
        self.title = title
        self.recommendations = recommendations
        self.group_index = group_index


def review_status_to_label(status):
    """
    Utility function to convert keys to labels
    :param status:
    :return:
    """
    return {
        "draft": "Draft",
        "submitted": "Submitted",
        "review": "In review",
        "published": "Published",
        "cancelled": "Cancelled",
        "achieved": "Achieved",
        "not-achieved": "Not achieved",
        "partially-achieved": "Partially achieved",
    }.get(status, status)


def get_review_recommendations(
    review: Review, mode: Literal["priority", "normal", "all"]
) -> Generator[RecommendationGroup, Any, None]:
    """
    Generate a list of recommendations based on the assessment review, filtered by the specified mode.

    This function iterates through the objectives, principles, and outcomes within a review’s assessment.
    For each outcome, it evaluates the review decision to determine priority and normal recommendations
    and filters them accordingly to construct a list of recommendations.

    Outcome decision is considered a priority if it does not meet the minimum profile requirement.

    :param review: The review object that contains the assessment and assessor response data.
    :type review: Review
    :param mode: The filtering mode for recommendations. Possible values are:
                 - "priority": Only include priority recommendations where the review decision
                   is "not-achieved" or "partially-achieved".
                 - "normal": Only includes normal recommendations where the review decision is not
                   categorized as a priority.
                 - "all": Includes all recommendations irrespective of their review decision.
    :type mode: Literal[ "priority", "normal", "all"]
    :return: A list of filtered recommendations based on the given review and mode. They are ordered by the
    contributing outcome and then by title. Within a given contributing outcome, the risk with the most
    recommendation count is prioritized, and the group with the maximum recommendation count comes first.
    :rtype: list[RecommendationGroup]
    """
    recommendations_list = []
    for objective in review.assessment.get_all_caf_objectives():
        for principle in objective["principles"].values():
            for outcome in principle["outcomes"].values():
                data = review.get_assessor_response()[objective["code"]][outcome["code"]]
                review_decision = data["review_data"]["review_decision"]

                # It is considered a priority if the review decision is not met the minimum profile requirement
                is_priority = (
                    IndicatorStatusChecker.indicator_min_profile_requirement_met(
                        review.assessment, principle["code"], outcome["code"], review_status_to_label(review_decision)
                    )
                    != "Yes"
                )

                if mode == "priority" and not is_priority:
                    continue
                if mode == "normal" and is_priority:
                    continue

                recommendations = data.get("recommendations", [])
                rec_id_prefix = f"REC-{outcome['code']}".replace(".", "").upper()
                for idx, recommendation in enumerate(recommendations):
                    recommendations_list.append(
                        Recommendation(
                            f"{rec_id_prefix}{idx + 1}",
                            recommendation["title"],
                            recommendation["text"],
                            objective["code"],
                            outcome["code"],
                        )
                    )

    recommendations_by_contributing_outcome: dict[str, dict[str, RecommendationGroup]] = {}
    group_index = 1
    # Groups recommendations; increments group index when needed
    for r in recommendations_list:
        recommendation_groups = recommendations_by_contributing_outcome.setdefault(r.outcome, {})
        recommendation_groups.setdefault(
            r.title.strip(), RecommendationGroup(r.title, [], group_index)
        ).recommendations.append(r)
        if len(recommendation_groups[r.title.strip()].recommendations) == 1:
            group_index += 1

    # Sort the list based on the number of recommendations in each group
    # Also reindex the group id based on sort ordering
    group_index = 1
    for _, recommendation_groups in recommendations_by_contributing_outcome.items():
        # For each outcome, sort recommendation groups by the number of recommendations
        for group in sorted(recommendation_groups.values(), key=lambda g: len(g.recommendations), reverse=True):
            # Reindex the group id based on sort ordering
            group.group_index = group_index
            group_index += 1
            # Yield the recommendation group for efficiency
            yield group
