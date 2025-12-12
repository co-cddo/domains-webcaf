from typing import Any

from django import template
from django.db.models import Q
from django.forms import BaseFormSet
from django.forms.boundfield import BoundField

from webcaf.webcaf.models import Assessment, Assessor, Review

register = template.Library()


@register.simple_tag()
def get_selected_tag(field: BoundField, answered_statements: dict[str, Any]) -> str:
    if answered_statements["indicators"].get(field.name):
        return "selected"
    return "not selected"


@register.simple_tag()
def get_outcome_category_names() -> list[str]:
    return ["achieved", "partially-achieved", "not-achieved"]


@register.simple_tag()
def get_outcome_status(objective_code, outcome_code, review) -> str | None:
    return review.get_outcome_review(objective_code, outcome_code).get("review_decision", None)


@register.filter()
def get_recommendation_count(parent_form: BaseFormSet) -> int:
    return sum(1 for form in parent_form.forms if not form.cleaned_data.get("DELETE"))


@register.simple_tag()
def get_outcome_recommendation_count(review: Review, objective_id: str, outcome_id: str) -> int:
    return len(review.get_outcome_recommendations(objective_id, outcome_id))


@register.simple_tag()
def get_existing_review_assignments(selected_assessment_id: int, assessment: Assessment, assessor: Assessor) -> str:
    """
    Returns a descriptive string about the current or other existing review assignments
    for a given assessment and assessor. It evaluates the `selected_assessment_id` against
    the provided `assessment` to construct the appropriate description of the assessment
    status and the names of assessors with their respective assignment statuses.

    :param selected_assessment_id: ID of the assessment currently being checked.
    :type selected_assessment_id: int
    :param assessment: Assessment object for which the review assignments are being queried.
    :type assessment: Assessment
    :param assessor: Assessor object representing the individual checking or being looked up.
    :type assessor: Assessor
    :return: A string detailing the relevant review assignments, including names of other assessors
             and their statuses or indicating if the assignment is not yet done for the assessor.
    :rtype: str
    """
    if assessor:
        other_reviews = assessment.reviews.exclude(Q(assessed_by=assessor) | Q(assessed_by=None)).all()
        current_review = Review.objects.filter(assessment=assessment, assessed_by=assessor).first()
    else:
        other_reviews = assessment.reviews.exclude(Q(assessed_by=None)).all()
        current_review = None
    if other_reviews:
        return (
            f"({'Also' if selected_assessment_id == assessment.id else 'Currently'} assessed by "
            + (
                "and ".join(
                    f"{review.assessed_by.name} - {review.get_status_display()}"
                    for review in other_reviews
                    if review.assessed_by
                )
            )
            + ")"
        )

    return f"{current_review.get_status_display() if current_review else 'Not assigned'}"


@register.simple_tag()
def is_comment_present(review: Review, objective_id: str, section_id: str) -> bool:
    return review.get_objective_comments(objective_id, section_id) is not None


@register.simple_tag()
def is_review_objective_complete(review: Review, objective_id: str) -> bool:
    return review.is_objective_complete(objective_id)


@register.simple_tag()
def is_review_all_objectives_complete(review: Review) -> bool:
    return review.is_all_objectives_complete()


@register.simple_tag()
def get_review_completed_percentage(review: Review):
    """
    Calculates the percentage of a review's completion based on its completed outcomes
    and other review attributes.

    This function uses the number of completed outcomes relative to the total outcomes in
    a review to compute an initial percentage. It then adds to this percentage based on
    the completion status of other attributes within the review.

    :param review: The review object for which the completion percentage is calculated.
    :type review: Review
    :return: An integer representing the calculated percentage of the review's completion.
    :rtype: int
    """
    info = review.get_completed_outcomes_info()
    # Assign 92% to completed outcomes
    # This is due to the fact we have 4 more steps outside outcome completion steps,  that are considered
    # as part of the review process. Each of these steps contributes 2% to the total completion.
    completed_outcomes_percentage = (
        92 * info.get("completed_outcomes", 0) // info.get("total_outcomes") if info.get("total_outcomes") else 0
    )

    # Calculate the remaining 2% based on the review attributes
    completed_outcomes_percentage += 2 * sum(
        x
        for x in [
            review.is_iar_period_complete(),
            review.is_quality_of_evidence_complete(),
            review.is_review_method_complete(),
            review.is_system_and_scope_complete(),
        ]
    )

    return completed_outcomes_percentage
