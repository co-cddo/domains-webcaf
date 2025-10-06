import re
from collections import namedtuple
from typing import Any, Literal, Optional

from django import template
from django.forms import Form

from webcaf.webcaf.caf.util import IndicatorStatusChecker
from webcaf.webcaf.models import Assessment, System, UserProfile
from webcaf.webcaf.utils.session import SessionUtil

register = template.Library()


@register.filter
def filter_fields(form, prefix):
    """
    Filter the fields of a form based on a specific prefix. This function retrieves all fields
    from the provided form whose names start with the given prefix and do not end with
    "_comment".

    :param form: The form instance containing the fields to filter.
    :type form: Any
    :param prefix: The prefix string used to filter the field names.
    :type prefix: str
    :return: A list of filtered fields that match the criteria.
    :rtype: list
    """
    return [field for field in form if field.name.startswith(prefix) and not field.name.endswith("_comment")]


@register.simple_tag
def get_comment_field(form, field_name, prefix: Optional[str] = None):
    """
    Retrieve a comment field from the given form based on the specified field name and choice.

    This function searches through the fields in the form for a field whose name
    matches the pattern of starting with the given field_name and ending with
    the specified choice and "_comment". If such a field exists, it returns the
    matching field. If no matching field is found, it returns None.

    :param form: The form object containing multiple fields.
    :type form: Iterable
    :param field_name: The base name of the field to search for. All matching
        fields should start with this base name.
    :type field_name: str
    :param prefix: The choice identifier to narrow down the field search. All
        matching fields should end with this choice followed by "_comment".
    :type prefix: str
    :return: The matched form field if found, otherwise None.
    :rtype: Optional[Any]
    """
    if prefix is None:
        suffix = "_comment"
    else:
        suffix = f"_{prefix}_comment"

    matched_fields = [field for field in form if field.name.startswith(field_name) and field.name.endswith(suffix)]
    if matched_fields:
        return matched_fields[0]
    return None


@register.simple_tag()
def get_outcome_details(assessment, outcome_id):
    """
    Retrieve outcome details for a specific outcome ID within an assessment.

    This function gathers details related to a specific outcome within the provided
    assessment based on the given outcome ID. It checks if the outcome section contains
    a confirmation and provides additional status information if the section exists.

    :param assessment: The assessment object containing multiple sections and outcomes.
    :type assessment: Assessment
    :param outcome_id: The unique identifier of the outcome for which details are retrieved.
    :type outcome_id: str
    :return: A dictionary containing the completion status and additional indicator statuses
        if the section exists; otherwise, an empty dictionary.
    :rtype: dict
    """
    outcome_details = {}
    section = assessment.get_section_by_outcome_id(outcome_id)
    # Confirmation is present in the data
    outcome_details["complete"] = "confirmation" in section if section else False

    return outcome_details | IndicatorStatusChecker.get_status_for_indicator(section) if section else {}


@register.simple_tag()
def get_assessment(request, status="draft"):
    """
    Fetches an assessment object based on the draft assessment ID stored in the
    session of the given request. If no draft assessment or assessment ID is
    present, returns None.

    :param status:
    :param request: The HTTP request object containing session data.
    :type request: HttpRequest
    :return: The assessment object retrieved from the database based on the
        draft assessment ID, or None if no valid assessment is found.
    :rtype: Assessment or None
    """
    return SessionUtil.get_current_assessment(request, status)


@register.simple_tag()
def is_final_objective(objective_id, assessment):
    """
    Determine if the given objective ID corresponds to the final objective.

    This function checks whether the provided `objetive_id` is the final ID
    in a predefined sequence of objective identifiers. It returns `True`
    if `objetive_id` is the final objective, and `False` otherwise.

    :param objetive_id: The identifier of the objective to check.
    :type objetive_id: str
    :return: A boolean value indicating whether the `objetive_id`
             corresponds to the final objective.
    :rtype: bool
    """

    objective_ids = [objective["code"] for objective in assessment.get_router().get_sections()]
    idx = objective_ids.index(objective_id)
    return idx == len(objective_ids) - 1


@register.simple_tag()
def next_objective(objective_id, assessment):
    """
    Retrieves the identifier for the next objective based on the current objective ID. The function
    uses a predefined list of objective IDs to determine the next item in sequence. If the current
    objective ID is the last in the list, None is returned.

    :param objetive_id: The current objective ID.
    :type objetive_id: str
    :return: The identifier for the next objective in sequence or None if the current objective ID
             is the last in the list.
    :rtype: str or None
    """
    objective_ids = [objective["code"] for objective in assessment.get_router().get_sections()]
    idx = objective_ids.index(objective_id)
    return objective_ids[idx + 1] if idx < len(objective_ids) - 1 else None


@register.simple_tag()
def is_objective_complete(assessment_id, objective_id):
    """
    Determines whether all outcomes associated with a specific objective in a given assessment
    have been completed. It evaluates the sections associated with the objective and checks
    if all the required outcomes have been confirmed as completed.

    :param assessment_id: ID of the assessment to be evaluated
    :type assessment_id: int
    :param objective_id: ID of the objective to check for completion
    :type objective_id: str
    :return: True if all outcomes of the objective are complete, False otherwise
    :rtype: bool
    """
    assessment = Assessment.objects.get(id=assessment_id)
    return assessment.is_objective_complete(objective_id)


@register.simple_tag()
def is_all_objectives_complete(assessment_id):
    """
    Determines if all objectives for a given assessment are complete.

    This function checks each objective defined in the configuration and confirms whether
    it is completed for a specified assessment (identified by its ID). If any objective is
    found incomplete, the function returns False. Otherwise, it returns True.

    :param assessment_id: The unique identifier of the assessment to be checked.
    :type assessment_id: int
    :return: Boolean indicating whether all objectives for the specified assessment
        are complete (True) or not (False).
    :rtype: bool
    """
    if assessment_id:
        return Assessment.objects.get(id=assessment_id).is_complete()

    return False


@register.filter
def get_display(instance: object, field_name: str):
    """Return the get_FOO_display value for a choices field"""
    method_name = f"get_{field_name}_display"
    if hasattr(instance, method_name):
        return getattr(instance, method_name)()
    return getattr(instance, field_name, "")


@register.filter
def split(value: str, delimiter: str = ","):
    """Split a string by the given delimiter (default: comma)."""
    if value:
        return [item.strip() for item in value.split(delimiter)]
    return []


@register.filter
def safe_id(value):
    """

    :param value:
    :return:
    """
    if not isinstance(value, str):
        value = str(value)
    return re.sub(r"[^a-zA-Z0-9_-]", "_", value)


@register.filter
def get_system_name_from_id(system_id: int):
    """
    takes the system id and returns the name
    """
    system = System.objects.get(id=system_id)
    return system.name


@register.simple_tag()
def get_tag_for_status(status: str) -> str:
    """Function to retrieve a color code based on the given status.

    :param status: A string indicating the current status.
    :return: A string representing the color code for the status.
    """
    if status == "Achieved":
        return "green"
    elif status == "Partially achieved":
        return "yellow"
    elif status == "Not met":
        return "grey"
    else:
        return "red"


@register.simple_tag()
def get_when_the_status_changed(assessment: Assessment, indicator_id: str, status: str) -> Assessment | None:
    return IndicatorStatusChecker.get_when_the_status_changed(assessment, indicator_id, status)


@register.simple_tag()
def indicator_min_profile_requirement_met(
    assessment: Assessment, principal_id: str, indicator_id: str, status: str
) -> str:
    return IndicatorStatusChecker.indicator_min_profile_requirement_met(assessment, principal_id, indicator_id, status)


@register.simple_tag()
def is_duplicate_questions_present(form: Form) -> bool:
    """Determines whether any question fields in the provided form are labeled as identical to others.

    :param form: The Django form instance to check.
    :return: True if any question fields have a label suffix indicating they are identical to another field, False otherwise.
    """
    for field_name, field in form.fields.items():
        if field.label_suffix and field.label_suffix.startswith("identical to"):
            return True
    return False


@register.simple_tag
def generate_assessment_progress_indicators(assessment: Assessment, principle_question: str = "") -> dict[str, Any]:
    """
    Returns a dict of figures calculated to show caf assessment progress calucluated using the
    caf and the saved assessment

    :param assessment: The assessment model contianing the data for the current assessment being completed
    :type assessment: Assessment
    :param principle_question: This is the question code of the principle for the page the user is currently
        on, e.g. B1.a
    :type principle_question: str
    """
    from webcaf.webcaf.frameworks import routers

    progress_dict: dict[str, Any] = {}
    router = routers["caf32"]
    sections = router.get_sections()

    if principle_question:
        section = principle_question[0]
        section_detail = next((s for s in sections if s["code"] == section))
        principle = principle_question.split(".")[0]
        question_number = principle[1:]
        progress_dict["question_number"] = question_number
        progress_dict["principles_in_section"] = len(section_detail.get("principles", []))
        progress_dict["principle"] = principle
        progress_dict["principle_name"] = section_detail["principles"][principle]["title"]

    # calculate the number of completed outcomes across the whole assessment, this is indicative of
    # having completed a previous indicator page and confirming it's completion
    completed_outcomes = len(
        [
            p
            for p in assessment.assessments_data
            if assessment.assessments_data[p].get("confirmation", {}).get("confirm_outcome") == "confirm"
        ]
    )
    # calculate the number of total outcomes across the whole caf
    total_outcomes = len([k for s in sections for p in s["principles"].values() for k in p["outcomes"]])
    progress_dict["percentage"] = int((completed_outcomes / total_outcomes) * 100)

    return progress_dict


OutcomeAnswers = namedtuple("OutcomeAnswers", ["answers", "confirm_comment", "total_questions"])
Answer = namedtuple("Answer", ["idx", "answer", "comment", "indicator_txt"])
QuestionCategory = namedtuple("QuestionCategory", ["category", "label"])


@register.simple_tag
def get_answers(
    assessment: Assessment, outcome: dict[str, Any], category: Literal["achieved", "partially-achieved", "not-achieved"]
) -> OutcomeAnswers:
    """
    Retrieve and process indicator answers for a given assessment outcome and category.

    This function identifies and processes answers related to a specified category
    ('achieved', 'partially-achieved', 'not-achieved') from the assessments data stored
    in the given assessment. It filters relevant indicators, retrieves descriptions and
    optional comments linked to those indicators, and computes the total number of
    questions for the provided category.

    :param assessment: The assessment object containing assessment data.
    :type assessment: Assessment
    :param outcome: A dictionary containing the assessment outcome details, including
        outcome code and indicator information.
    :type outcome: dict[str, Any]
    :param category: The category of indicators to process, limited to 'achieved',
        'partially-achieved', or 'not-achieved'.
    :type category: Literal['achieved', 'partially-achieved', 'not-achieved']
    :return: An OutcomeAnswers object containing the processed list of answers, the
        outcome confirmation comment, and the total questions count for the category.
    :rtype: OutcomeAnswers
    """
    indicators_ = assessment.assessments_data[outcome["code"]]["indicators"]
    category_answers = [i for i in indicators_ if i.startswith(category) and not i.endswith("comment")]
    ticked_answers = []
    total_questions = 0
    for idx, answer in enumerate(category_answers, start=1):
        if indicators_[answer]:
            indicator_txt = outcome["indicators"][category][answer.replace(f"{category}_", "")]["description"]
            # We do indicators_.get(f"{answer}_comment","") as we do not have
            # comments for not-achieved indicators
            ticked_answers.append(Answer(idx, answer, indicators_.get(f"{answer}_comment", ""), indicator_txt))
        total_questions += 1
    return OutcomeAnswers(
        ticked_answers,
        assessment.assessments_data[outcome["code"]]["confirmation"]["confirm_outcome_confirm_comment"],
        total_questions=total_questions,
    )


@register.simple_tag
def get_question_categories() -> list[QuestionCategory]:
    """
    Generates a list of question categories as tuples containing a category identifier
    and its corresponding human-readable name.

    :return: A list of tuples representing question categories with their identifiers
        and human-readable names.
    :rtype: list[QuestionCategory]
    """
    return [
        QuestionCategory("achieved", "Achieved"),
        QuestionCategory("partially-achieved", "Partially achieved"),
        QuestionCategory("not-achieved", "Not achieved"),
    ]


@register.filter()
def get_role_display(role_key: str):
    """
    Convert the role key to a display name
    :param role_key:
    :return:
    """
    return UserProfile.get_role_label(role_key)
