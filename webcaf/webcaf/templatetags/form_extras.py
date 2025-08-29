from typing import Any

from django import template

from webcaf.webcaf.models import Assessment
from webcaf.webcaf.views.util import ConfigHelper, IndicatorStatusChecker

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
def get_comment_field(form, field_name, choice):
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
    :param choice: The choice identifier to narrow down the field search. All
        matching fields should end with this choice followed by "_comment".
    :type choice: str
    :return: The matched form field if found, otherwise None.
    :rtype: Optional[Any]
    """
    matched_fields = [
        field for field in form if field.name.startswith(field_name) and field.name.endswith(f"_{choice}_comment")
    ]
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
def get_assessment(request):
    """
    Fetches an assessment object based on the draft assessment ID stored in the
    session of the given request. If no draft assessment or assessment ID is
    present, returns None.

    :param request: The HTTP request object containing session data.
    :type request: HttpRequest
    :return: The assessment object retrieved from the database based on the
        draft assessment ID, or None if no valid assessment is found.
    :rtype: Assessment or None
    """
    draft_assessment = request.session.get("draft_assessment", {})
    if draft_assessment:
        assessment_id = draft_assessment.get("assessment_id")
        if assessment_id:
            return Assessment.objects.get(id=assessment_id)
    return None


@register.simple_tag()
def is_final_objective(objetive_id):
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
    objective_ids = [objective["code"] for objective in ConfigHelper.get_objectives()]
    idx = objective_ids.index(objetive_id)
    return idx == len(objective_ids) - 1


@register.simple_tag()
def next_objective(objetive_id):
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
    objective_ids = [objective["code"] for objective in ConfigHelper.get_objectives()]
    idx = objective_ids.index(objetive_id)
    return f"objective_{objective_ids[idx + 1]}" if idx < len(objective_ids) - 2 else None


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
    sections = assessment.get_sections_by_objective_id(objective_id)
    return _check_objective_complete(sections, objective_id)


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
    assessment = Assessment.objects.get(id=assessment_id)
    for objective in ConfigHelper.get_objectives():
        objective_id = objective["code"]
        sections = assessment.get_sections_by_objective_id(objective_id)
        if not _check_objective_complete(sections, objective_id):
            return False
    return True


def _check_objective_complete(
    sections: list[tuple[str, Any]] | None,
    objective_id: str,
):
    """
    Checks if an objective is completed based on provided sections. An objective is considered complete
    if all its outcomes have a corresponding "confirmation" in the provided sections.

    :param objective_id: The unique identifier of the objective to check.
    :type objective_id: str
    :param sections: A list of tuples where each tuple represents a completed section and
        its associated confirmation status.
    :type sections: list[tuple[str, Any]] | None
    :return: True if the objective is complete, otherwise False.
    :rtype: bool
    """
    if sections:
        objective = ConfigHelper.get_objective(objective_id)
        all_outcomes = [
            outcome["code"]
            for principle in objective["principles"].values()
            for outcome in principle["outcomes"].values()
        ]
        completed_outcomes = [
            completed_section[0] for completed_section in sections if "confirmation" in completed_section[1]
        ]
        return set(all_outcomes) == set(completed_outcomes)
    return False
