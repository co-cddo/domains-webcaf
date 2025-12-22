from typing import Any

from django import template
from django.contrib.auth.models import User
from django.forms import BaseFormSet
from django.forms.boundfield import BoundField

from webcaf.webcaf.models import Organisation, Review

register = template.Library()


@register.simple_tag()
def get_selected_tag(field: BoundField, answered_statements: dict[str, Any]) -> str:
    if answered_statements["indicators"].get(field.name):
        return "selected"
    return "did not select"


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
def get_user_role(user: User, organisation: Organisation) -> str:
    """
    Retrieve the display name of the user's role within a specific organisation.

    This function iterates through the user's profiles associated with the given
    organisation. If a profile matches the organisation, it fetches the display
    name of the role assigned to that user within the organisation.

    :param user: The user whose role is to be retrieved.
    :type user: User
    :param organisation: The organization for which the user's role should be determined.
    :type organisation: Organisation
    :return: The display name of the user's role within the specified organisation.
    :rtype: str
    """
    if user:
        for profile in user.profiles.filter(organisation=organisation):
            if profile.organisation == organisation:
                return profile.get_role_display()
    return "-"


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
    # Assign 90% to completed outcomes
    # This is due to the fact we have 5 more steps outside outcome completion steps, that are considered
    # as part of the review process. Each of these steps contributes 2% to the total completion.
    completed_outcomes_percentage = (
        90 * info.get("completed_outcomes", 0) // info.get("total_outcomes") if info.get("total_outcomes") else 0
    )

    # Calculate the remaining 2% based on the review attributes
    completed_outcomes_percentage += 2 * sum(
        x
        for x in [
            review.is_iar_period_complete(),
            review.is_quality_of_evidence_complete(),
            review.is_review_method_complete(),
            review.is_system_and_scope_complete(),
            review.is_company_details_complete(),
        ]
    )

    return completed_outcomes_percentage
