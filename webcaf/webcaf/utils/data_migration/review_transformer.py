from typing import Any

from webcaf.webcaf.utils.data_migration.assessment_transformer import (
    _parse_old_assessment_data,
)


def transform_review_v1_to_v2(
    definition_structure: dict[str, dict[str, Any]],
    assessment_meta: dict[str, Any],
    old_assessment_data: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Generate a review structure to new format from a definition structure
    and old assessment data
    :param old_assessment_data:
    :param assessment_meta:
    :param definition_structure:
    :return: Assessment structure dictionary
    """
    review: dict[str, Any] = {}
    version_key = assessment_meta.get("assessment_version_id", "unknown")
    status_map = {"ACH": "achieved", "PAC": "partially-achieved", "NAC": "not-achieved"}

    # Parse old assessment data
    group_comments, outcomes, supplementary_questions = _parse_old_assessment_data(old_assessment_data)

    # Process all outcomes
    objectives = definition_structure[version_key].get("objectives", {})
    for objective_key, objective in objectives.items():
        objective_entry = review.setdefault(objective_key, {})
        for principle_key, principle in objective.get("principles", {}).items():
            for outcome_key, outcome in principle.get("outcomes", {}).items():
                outcome_structure = _process_review_outcome(outcome_key, outcome, outcomes, status_map)
                if outcome_structure:
                    objective_entry[outcome_key] = outcome_structure
    return review


def _process_review_outcome(
    outcome_key: str,
    outcome: dict[str, Any],
    outcomes: dict[str, list],
    status_map: dict[str, str],
) -> dict[str, Any] | None:
    """Process a single outcome and return its assessment structure."""
    outcome_data = outcomes.get(outcome_key, [])

    indicator_entries = [e for t, e in outcome_data if t == "indicator"]
    outcome_entry = next((e for t, e in outcome_data if t == "outcome"), None)

    achieved_indicators = outcome.get("indicators", {}).get("achieved", {})
    partially_achieved_indicators = outcome.get("indicators", {}).get("partially-achieved", {})
    not_achieved_indicators = outcome.get("indicators", {}).get("not-achieved", {})

    # Process all indicator types
    indicators_dict = {}
    indicators_dict.update(_process_review_indicators_by_type(achieved_indicators, "achieved", indicator_entries))
    indicators_dict.update(
        _process_review_indicators_by_type(partially_achieved_indicators, "partially-achieved", indicator_entries)
    )
    indicators_dict.update(
        _process_review_indicators_by_type(not_achieved_indicators, "not-achieved", indicator_entries)
    )

    if not outcome_entry:
        return None

    review_decision = status_map.get(outcome_entry.get("assessor_achievement", ""), "N/A")
    outcome_status = status_map.get(outcome_entry.get("achievement", ""), "N/A")
    assessor_comment = outcome_entry.get("assessor_comment", "")

    return {
        "indicators": indicators_dict,
        "review_data": {
            "outcome_status": outcome_status,
            "review_decision": review_decision,
            "review_comment": assessor_comment,
        },
        "recommendations": [],
    }


def _process_review_indicators_by_type(
    indicators: dict[str, Any],
    indicator_type: str,
    indicator_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Process all indicators of a specific type (achieved, partially-achieved, not-achieved)."""
    indicators_dict: dict[str, Any] = {}
    for ind_id in indicators:
        try:
            entry = next(filter(lambda x: x["key"] == ind_id, indicator_entries))
            indicators_dict[f"{indicator_type}_{ind_id}"] = entry["assessor_answer"] or ""
            indicators_dict[f"{indicator_type}_{ind_id}_comment"] = entry["assessor_comment"] or ""
        except StopIteration:
            print(f"Indicator is not found: Indicator entry not found for ID: {ind_id}")
    return indicators_dict
