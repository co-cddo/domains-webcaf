from collections import defaultdict
from typing import Any


def transform_assessment_v1_to_v2(
    definition_structure: dict[str, dict[str, Any]],
    assessment_meta: dict[str, Any],
    old_assessment_data: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Transforms assessment data from version 1 format to version 2 format.

    This function takes a definition structure, assessment metadata, and old assessment
    data and generates a new structured assessment object.

    :param definition_structure: A dictionary defining the structure of the assessment
        in version 2.
    :type definition_structure: dict[str, dict[str, Any]]
    :param assessment_meta: Metadata related to the assessment, such as version
        identifiers.
    :type assessment_meta: dict[str, Any]
    :param old_assessment_data: The previous assessment data containing outcomes,
        indicators, and other related fields.
    :type old_assessment_data: list[dict[str, Any]]
    :return: A dictionary representing the transformed assessment in version 2 format.
    :rtype: dict[str, Any]
    """
    assessment = {}
    version_key = assessment_meta.get("assessment_version_id", "unknown")

    # Parse old assessment data
    group_comments, outcomes, supplementary_questions = _parse_old_assessment_data(old_assessment_data)

    # Process all outcomes
    objectives = definition_structure[version_key].get("objectives", {})
    for objective_key, objective in objectives.items():
        for principle_key, principle in objective.get("principles", {}).items():
            for outcome_key, outcome in principle.get("outcomes", {}).items():
                outcome_structure = _process_outcome(
                    outcome_key,
                    outcome,
                    outcomes,
                    supplementary_questions,
                    group_comments,
                )
                if outcome_structure:
                    assessment[outcome_key] = outcome_structure

    return assessment


def _process_outcome(
    outcome_key: str,
    outcome: dict[str, Any],
    outcomes: dict[str, list],
    supplementary_questions: dict[str, list],
    group_comments: dict[str, list],
) -> dict[str, Any] | None:
    """
    Processes the outcome data, indicators, and supplementary questions for a given outcome key. It compiles the processed
    data into a structured dictionary, including indicators, supplementary questions, and an outcome confirmation section.

    :param outcome_key: Unique identifier for the outcome being processed.
    :type outcome_key: str
    :param outcome: Dictionary containing outcome-related definition information and associated indicators
    for the current outcome being processed.
    :type outcome: dict[str, Any]
    :param outcomes: Assessment data in Dictionary mapping outcome keys to lists of grouped data tuples categorized by type (e.g.,
                     "indicator" or "outcome").
    :type outcomes: dict[str, list]
    :param supplementary_questions: Dictionary mapping keys associated with outcomes to lists of supplementary questions.
    :type supplementary_questions: dict[str, list]
    :param group_comments: Dictionary mapping keys to lists of group comments associated with outcomes or indicators.
    :type group_comments: dict[str, list]
    :return: A dictionary containing processed indicator data, supplementary question mappings, and confirmation details
             for the specified outcome, or None if no relevant outcome entry exists.
    :rtype: dict[str, Any] | None
    """
    outcome_data = outcomes.get(outcome_key, [])
    status_map = {
        "ACH": "Achieved",
        "P_ACH": "Partially achieved",
        "N_ACH": "Not achieved",
        "PAC": "Partially achieved",
        "NAC": "Not achieved",
    }
    indicator_entries = [e for t, e in outcome_data if t == "indicator"]
    outcome_entry = next((e for t, e in outcome_data if t == "outcome"), None)
    outcome_supplementary_questions = [
        e for k, e in supplementary_questions.items() if k.startswith(f"G_{outcome_key}")
    ]

    achieved_indicators = outcome.get("indicators", {}).get("achieved", {})
    partially_achieved_indicators = outcome.get("indicators", {}).get("partially-achieved", {})
    not_achieved_indicators = outcome.get("indicators", {}).get("not-achieved", {})

    # Process all indicator types
    indicators_dict = {}
    indicators_dict.update(
        _process_indicators_by_type(achieved_indicators, "achieved", indicator_entries, group_comments)
    )
    indicators_dict.update(
        _process_indicators_by_type(
            partially_achieved_indicators, "partially-achieved", indicator_entries, group_comments
        )
    )
    indicators_dict.update(
        _process_indicators_by_type(not_achieved_indicators, "not-achieved", indicator_entries, group_comments)
    )

    if not outcome_entry:
        return None

    # Determine outcome status
    outcome_status = status_map.get(outcome_entry.get("achievement", ""), "N/A")
    confirm_comment = _collect_outcome_comments(outcome_entry, group_comments)

    return {
        "indicators": indicators_dict,
        "supplementary_questions": _map_supplementary_questions(outcome_supplementary_questions),
        "confirmation": {
            "outcome_status": outcome_status,
            "confirm_outcome": "confirm",
            "outcome_status_message": "",
            "confirm_outcome_confirm_comment": confirm_comment,
        },
    }


def _process_indicators_by_type(
    indicators: dict[str, Any],
    indicator_type: str,
    indicator_entries: list[dict[str, Any]],
    group_comments: dict[str, list],
) -> dict[str, Any]:
    """Process all indicators of a specific type (achieved, partially-achieved, not-achieved)."""
    indicators_dict: dict[str, Any] = {}
    for ind_id in indicators:
        try:
            answer_value, comment = _process_indicator_entry(ind_id, indicator_entries, group_comments)
            indicators_dict[f"{indicator_type}_{ind_id}"] = answer_value == "Yes"
            indicators_dict[f"{indicator_type}_{ind_id}_comment"] = comment
        except ValueError as ve:
            print(f"Indicator is not found: {ve}")
    return indicators_dict


def _parse_old_assessment_data(
    old_assessment_data: list[dict[str, Any]]
) -> tuple[dict[str, list], dict[str, list], dict[str, list]]:
    """Parse old assessment data into group comments, outcomes, and supplementary questions."""
    group_comments = defaultdict(list)
    outcomes = defaultdict(list)
    supplementary_questions = defaultdict(list)

    for entry in old_assessment_data:
        key = entry.get("key")
        group_key = entry.get("group_key")
        org_comment = entry.get("org_comment")

        if group_key and org_comment:
            group_comments[group_key].append(org_comment)

        # Outcome keys (e.g., A1.a) or Indicator keys (e.g., A1.a.1)
        if key and key.count(".") == 1:
            if "-SQ" in key:
                supplementary_questions[entry["group_key"]].append(("supplementary_question", entry))
            else:
                outcomes[key].append(("outcome", entry))
        elif key and key.count(".") == 2:
            outcome_key = ".".join(key.split(".")[:2])
            outcomes[outcome_key].append(("indicator", entry))

    return group_comments, outcomes, supplementary_questions


def _get_indicator_comment(entry: dict[str, Any], group_comments: dict[str, list]) -> str:
    """Extract comment from indicator entry."""
    g_key: str | None = entry.get("group_key")
    if g_key and g_key in group_comments:
        return "\n\n".join(group_comments[g_key])
    return entry.get("org_comment") or ""


def _process_indicator_entry(
    ind_id: str, indicator_entries: list[dict[str, Any]], group_comments: dict[str, list]
) -> tuple[str, str]:
    """Process a single indicator entry and return answer and comment."""
    entry: dict[str, Any] | None = next((e for e in indicator_entries if e.get("key") == ind_id), None)
    if entry is None:
        raise ValueError(f"Indicator entry not found for ID: {ind_id}")
    answer: str | None = entry.get("answer")
    if answer is None:
        raise ValueError(f"Indicator answer not found for ID: {ind_id}")
    comment: str = _get_indicator_comment(entry, group_comments)
    return answer, comment


def _map_supplementary_questions(supplementary_questions: list) -> list[dict[str, Any]]:
    """Map supplementary questions to the expected format."""
    mapped_questions = []
    for question_entries in supplementary_questions:
        for entry_type, question_entry in question_entries:
            mapped_questions.append({"key": question_entry["key"], "answer": question_entry["answer"]})
    return mapped_questions


def _collect_outcome_comments(outcome_entry: dict[str, Any], group_comments: dict[str, list]) -> str:
    """Collect all unique comments for an outcome."""
    outcome_comments = []
    seen_comments = set()

    group_key = outcome_entry.get("group_key")
    if group_key and group_key in group_comments:
        for comment in group_comments[group_key]:
            if comment not in seen_comments:
                outcome_comments.append(comment)
                seen_comments.add(comment)
    elif outcome_entry.get("org_comment"):
        comment = outcome_entry.get("org_comment")
        if comment not in seen_comments:
            outcome_comments.append(comment)
            seen_comments.add(comment)

    return "\n\n".join(outcome_comments) if outcome_comments else ""
