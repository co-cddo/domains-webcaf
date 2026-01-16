from typing import Any, Literal, NamedTuple

from django import template
from django.contrib.auth.models import User
from django.forms import BaseFormSet
from django.forms.boundfield import BoundField

from webcaf.webcaf.caf.util import IndicatorStatusChecker
from webcaf.webcaf.models import Organisation, Review
from webcaf.webcaf.templatetags.form_extras import status_to_label

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


# report page tags
@register.simple_tag()
def get_path(review: Review, path: str) -> str | dict[str, Any] | None:
    """
    Determines and retrieves the value located at the specified path within the review's
    nested review data structure. The path is expressed as a dot-separated string of
    keys that indicate the hierarchical location of the desired value. If a key is not
    found or the path is invalid, the function returns None.

    :param review: The review object containing the nested review data. Must be an
        instance of the Review class.
    :type review: Review
    :param path: The dot-separated string that specifies the hierarchy of keys to locate
        the desired value within the review's data.
    :type path: str
    :return: The value located at the specified path within the review data structure.
        Returns None if the key is not found or the path is invalid.
    :rtype: str | dict[str, Any] | None
    """
    parts = path.split(".")
    current_section = review.review_data
    for part in parts:
        current_section = current_section.get(part, None)
        if current_section is None:
            return None
    return current_section


@register.simple_tag()
def get_objectives(review: Review) -> list[dict]:
    """
    Retrieve and return a list of objectives associated with the given review.

    This function fetches all CAF (Cyber Assessment Framework) objectives
    related to the provided review by utilizing the `get_all_caf_objectives`
    method of the assessment associated with the review.

    :param review: An instance of the `Review` class that contains the
        assessment data from which the objectives are retrieved.
    :type review: Review
    :return: A list of dictionaries, where each dictionary represents
        an objective associated with the given review.
    :rtype: list[dict]
    """
    return review.assessment.get_all_caf_objectives()


ReviewStatusInfo = NamedTuple("ReviewStatusInfo", [("status", str), ("review_decision", str)])


@register.simple_tag()
def get_review_outcome_statuses(review: Review, objective_code: str, outcome_code: str) -> ReviewStatusInfo:
    """
    Retrieve the status and review decision for a specific outcome within a given objective of a review.

    :param review: The review instance containing the assessment data.
    :type review: Review
    :param objective_code: The code identifying the objective within the review.
    :type objective_code: str
    :param outcome_code: The code identifying the outcome within the objective.
    :type outcome_code: str
    :return: A named tuple containing the status and review decision for the specified outcome.
    :rtype: ReviewStatusInfo
    """
    return ReviewStatusInfo(
        review.assessment.assessments_data[outcome_code]["confirmation"]["outcome_status"],
        review.review_data["assessor_response_data"][objective_code][outcome_code]["review_data"]["review_decision"],
    )


PrincipleOutcomeStatus = NamedTuple(
    "PrincipleOutcomeStatus",
    [
        ("assessment_status", bool),
        ("review_status", bool),
        ("total", int),
        ("assessment_total_met", int),
        ("review_total_met", int),
    ],
)


@register.simple_tag()
def get_principle_profile_status(review: Review, objective_code: str, principle_code: str) -> PrincipleOutcomeStatus:
    """
    Generate the profile status for a principle based on the review assessments.

    This function evaluates the outcomes within a review’s assessment by iterating
    through objectives, principles, and outcomes in the review. It determines the
    profile status for a specific principle by examining the criteria related to it.
    The principle status is derived from the outcomes connected to the given
    objective and principle codes.

    Outcome decisions contribute to the principle profile status based on whether
    they meet the criteria defined in the assessment. The evaluation considers
    various assessment decisions and categorizes the principle status accordingly.

    :param review: The review object that contains the assessment and assessor
                   response data.
                     - Assessment holds the objectives, principles, and outcomes
                       data.
                     - Assessor responses include decisions on whether outcomes
                       meet minimum requirements.
    :type review: Review
    :param objective_code: The unique code corresponding to the objective under
                           evaluation within the review.
    :type objective_code: str
    :param principle_code: The unique code corresponding to the principle being
                           assessed within the objective.
    :type principle_code: str
    :return: The status of the principle in terms of assessment outcomes as
             influenced by the review decisions and criteria evaluation.
    :rtype: PrincipleOutcomeStatus
    """
    assessment_decision_list = [
        (code, assessments_data["confirmation"]["outcome_status"])
        for code, assessments_data in review.assessment.assessments_data.items()
        if code.startswith(principle_code)
    ]

    review_decision_list = [
        (code, status_to_label(outcome_data["review_data"]["review_decision"]))
        for code, outcome_data in review.review_data["assessor_response_data"][objective_code].items()
        if code.startswith(principle_code)
    ]

    assessment_status_list = list(
        IndicatorStatusChecker.indicator_min_profile_requirement_met(
            review.assessment, principle_code, indicator_code, assessment_status
        )
        for indicator_code, assessment_status in assessment_decision_list
    )

    review_status_list = list(
        IndicatorStatusChecker.indicator_min_profile_requirement_met(
            review.assessment, principle_code, indicator_code, review_status
        )
        for indicator_code, review_status in review_decision_list
    )

    return PrincipleOutcomeStatus(
        all(item == "Yes" for item in assessment_status_list),
        all(item == "Yes" for item in review_status_list),
        len(assessment_status_list),
        len([item for item in assessment_status_list if item == "Yes"]),
        len([item for item in review_status_list if item == "Yes"]),
    )


Recommendation = NamedTuple(
    "Recommendation", [("id", str), ("title", str), ("text", str), ("objective", str), ("outcome", str)]
)


@register.simple_tag()
def get_recommendations(review: Review, mode: Literal["priority", "normal", "all"]) -> list[Recommendation]:
    """
    Generate a list of recommendations based on the assessment review, filtered by the specified mode.

    This function iterates through the objectives, principles, and outcomes within a review’s assessment.
    For each outcome, it evaluates the review decision to determine priority and normal recommendations
    and filters them accordingly to construct a list of recommendations.

    Outcome decision is considered priority if it does not meet the minimum profile requirement

    :param review: The review object that contains the assessment and assessor response data.
    :type review: Review
    :param mode: The filtering mode for recommendations. Possible values are:
                 - "priority": Only include priority recommendations where the review decision
                   is "not-achieved" or "partially-achieved".
                 - "normal": Only include normal recommendations where the review decision is not
                   categorized as priority.
                 - "all": Include all recommendations irrespective of their review decision.
    :type mode: Literal["priority", "normal", "all"]
    :return: A list of filtered recommendations based on the given review and mode.
    :rtype: list[Recommendation]
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
                        review.assessment, principle["code"], outcome["code"], status_to_label(review_decision)
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
                            objective["title"],
                            outcome["title"],
                        )
                    )

    return recommendations_list


ReviewComment = NamedTuple("ReviewComment", [("section", str), ("index", int), ("comment", str)])


@register.simple_tag()
def get_indicator_comments(object_version: Review, objective_code: str, indicator_code: str) -> list[ReviewComment]:
    """
    Retrieve comments for a specific indicator from the review data.
    """
    data_items = {
        k: v
        for k, v in object_version.review_data["assessor_response_data"][objective_code][indicator_code][
            "indicators"
        ].items()
        if k.endswith("_comment")
    }
    comment_data = []
    for section in get_outcome_category_names():
        section_comments = sorted(
            {k: v for k, v in data_items.items() if k.startswith(section)}, key=lambda x: x.split("_")[1]
        )
        for index, comment in enumerate(section_comments):
            if data_items[comment]:
                comment_data.append(ReviewComment(section, index + 1, data_items[comment]))
    return comment_data


@register.simple_tag()
def get_principle(review: Review, objective_code: str, principle_code: str) -> dict:
    """
    Retrieves data associated with a specific principle and objective code from the review object.

    :param review: Review instance containing the assessment data.
    :type review: Review
    :param objective_code: Code representing the objective to look up.
    :type objective_code: str
    :param principle_code: Code representing the principle to retrieve data for.
    :type principle_code: str
    :return: Dictionary containing the data associated with the given principle and objective code.
    :rtype: dict
    """
    return review.review_data["assessor_response_data"][objective_code][principle_code]
