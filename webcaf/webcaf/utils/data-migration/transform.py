"""
Data Migration and Transformation Script for WebCAF Assessment Data

This module handles the migration of legacy WebCAF assessment data to the new format,
making it compatible with modern data analytics tools.

Overview:
---------
The transformation process follows these main steps:

1. **Definition Structure Building** (`build_definition_structure`):
   - Reads compressed assessment definitions from `data/assessment-definitions/`
   - Builds a hierarchical structure: Objectives → Principles → Outcomes → Indicators
   - Each indicator is categorized by achievement type (ACH, PAC, NAC)

2. **Assessment Data Parsing** (`_parse_old_assessment_data`):
   - Extracts group comments, outcomes, and supplementary questions from legacy data
   - Distinguishes between outcome-level data (key format: A1.a) and indicator-level data (A1.a.1)

3. **Assessment Structure Generation** (`generate_assessment_structure`):
   - Transforms old assessment data using the definition structure
   - Processes indicators by achievement type (achieved/partially-achieved/not-achieved)
   - Collects and deduplicates comments from multiple sources
   - Generates metadata including organization and system information

4. **Review Structure Generation** (`generate_review_structure`):
   - Similar to assessment generation but focused on review/assessor data
   - Includes review decisions and assessor comments

Data Structure:
--------------
- **Objectives**: Top-level CAF goals (e.g., A, B, C)
- **Principles**: Sub-categories under objectives (e.g., A1, A2)
- **Outcomes**: Contributing outcomes under principles (e.g., A1.a, A1.b)
- **Indicators**: IGP (Indicators of Good Practice) statements that define achievement levels

Achievement Types:
-----------------
- ACH: Achieved
- PAC: Partially Achieved
- NAC: Not Achieved

Input Files:
-----------
- `data/assessment-definitions/*.gz`: Compressed definition files
- `data/assessments-combined/cos-igps/all.json.gz`: Assessment indicator data
- `data/assessments-combined/overview/all.json.gz`: Assessment metadata
- `data/hashed_ids/{assessments,organisations,systems}.json.gz`: ID mappings

Output Files:
------------
- `data/assessments-transformed/{assessment_id}.json`: Transformed assessment data
- `data/assessments-transformed/{assessment_id}-review.json`: Transformed review data
"""

import gzip
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from webcaf.webcaf.utils.transformer import (
    assessment_transform_to_outcome_format,
    review_transform_to_outcome_format,
)


def _create_objective_entry(item: dict[str, Any]) -> dict[str, Any]:
    """
    Create an objective entry from item data.

    Args:
        item: Dictionary containing objective data with keys: key, title, additional_text

    Returns:
        Dictionary with objective structure including code, title, description, and empty principles dict
    """
    return {
        "code": item.get("key"),
        "title": item.get("title"),
        "description": item.get("additional_text", ""),
        "principles": {},
    }


def _create_principle_entry(item: dict[str, Any]) -> dict[str, Any]:
    """Create a principle entry from item data."""
    return {
        "code": item.get("key"),
        "title": item.get("title"),
        "description": item.get("additional_text", ""),
        "outcomes": {},
        "external_links": item.get("external_links", {}),
    }


def _create_outcome_entry(item: dict[str, Any]) -> dict[str, Any]:
    """Create an outcome entry from item data."""
    return {
        "code": item.get("key"),
        "title": item.get("title"),
        "description": item.get("additional_text", ""),
        "indicators": {"achieved": {}, "partially-achieved": {}, "not-achieved": {}},
        "external_links": item.get("external_links", {}),
    }


def _create_indicator_entry(item: dict[str, Any]) -> dict[str, Any]:
    """Create an indicator entry from item data."""
    return {
        "description": item.get("title"),
        "ncsc-index": item.get("key"),
    }


def _add_indicator_to_outcome(outcome: dict[str, Any], item: dict[str, Any]) -> None:
    """Add an indicator to the outcome based on its achievement type."""
    achieved_type = item.get("achieved_type_id", "")
    key = item.get("key")
    indicator_entry = _create_indicator_entry(item)

    if achieved_type == "ACH":
        outcome["indicators"]["achieved"][key] = indicator_entry
    elif achieved_type == "PAC":
        outcome["indicators"]["partially-achieved"][key] = indicator_entry
    elif achieved_type == "NAC":
        outcome["indicators"]["not-achieved"][key] = indicator_entry


def _process_item(
    item: dict[str, Any],
    objectives: dict[str, Any],
    current_objective: str | None,
    current_principle: str | None,
    current_outcome: str | None,
) -> tuple[str | None, str | None, str | None]:
    """
    Process a single item and update objectives structure.
    Returns updated (current_objective, current_principle, current_outcome) tuple.
    """
    display_type = item.get("display_type")
    key: str = item.get("key", None)
    if not key:
        raise ValueError("Item key cannot be None or empty")

    if display_type == "Objective":
        objectives[key] = _create_objective_entry(item)
        return key, None, None

    if display_type == "Principle":
        if current_objective and current_objective in objectives:
            objectives[current_objective]["principles"][key] = _create_principle_entry(item)
        return current_objective, key, None

    if display_type == "Contributing Outcome":
        if current_objective and current_principle:
            if current_objective in objectives and current_principle in objectives[current_objective]["principles"]:
                objectives[current_objective]["principles"][current_principle]["outcomes"][key] = _create_outcome_entry(
                    item
                )
        return current_objective, current_principle, key

    if display_type == "IGP":
        if current_objective and current_principle and current_outcome:
            outcome = (
                objectives.get(current_objective, {})
                .get("principles", {})
                .get(current_principle, {})
                .get("outcomes", {})
                .get(current_outcome)
            )
            if outcome:
                _add_indicator_to_outcome(outcome, item)
        return current_objective, current_principle, current_outcome

    return current_objective, current_principle, current_outcome


def build_definition_structure() -> dict[str, dict[str, Any]]:
    """
    Build hierarchical definition structure from compressed assessment definition files.

    Reads all .gz files from data/assessment-definitions/ and constructs a nested
    structure of Objectives → Principles → Outcomes → Indicators.

    Returns:
        Dictionary keyed by assessment_version_id, each containing:
        - assessment_version_id: Version identifier
        - display_name: Human-readable version name
        - objectives: Nested dict of objectives, principles, outcomes, and indicators

    Example structure:
        {
            "v3.0": {
                "assessment_version_id": "v3.0",
                "display_name": "CAF v3.0",
                "objectives": {
                    "A": {
                        "code": "A",
                        "title": "Managing security risk",
                        "principles": {
                            "A1": {
                                "code": "A1",
                                "title": "Governance",
                                "outcomes": {...}
                            }
                        }
                    }
                }
            }
        }
    """
    definitions_dir = "data/assessment-definitions"
    structure = {}

    # Read all JSON files in the directory
    for filename in os.listdir(definitions_dir):
        if not filename.endswith(".gz"):
            continue

        filepath = os.path.join(definitions_dir, filename)
        with gzip.open(filepath, "r") as f:
            data = json.load(f)

        # Build nested structure: objectives > principles > outcomes > indicators
        objectives: dict[str, dict[str, Any]] = {}
        current_objective = None
        current_principle = None
        current_outcome = None

        for item in data.get("items", []):
            current_objective, current_principle, current_outcome = _process_item(
                item, objectives, current_objective, current_principle, current_outcome
            )

        # Store with version as key
        structure[data.get("assessment_version_id")] = {
            "assessment_version_id": data.get("assessment_version_id"),
            "display_name": data.get("display_name"),
            "objectives": objectives,
        }

    return structure


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
    g_key = entry.get("group_key")
    if g_key and g_key in group_comments:
        return "\n\n".join(group_comments[g_key])
    return entry.get("org_comment") or ""


def _process_indicator_entry(
    ind_id: str, indicator_entries: list[dict[str, Any]], group_comments: dict[str, list]
) -> tuple[str, str]:
    """Process a single indicator entry and return answer and comment."""
    entry = next((e for e in indicator_entries if e.get("key") == ind_id), None)
    if entry is None:
        raise ValueError(f"Indicator entry not found for ID: {ind_id}")
    answer = entry.get("answer")
    if answer is None:
        raise ValueError(f"Indicator answer not found for ID: {ind_id}")
    comment = _get_indicator_comment(entry, group_comments)
    return answer, comment


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
            val, comment = _process_indicator_entry(ind_id, indicator_entries, group_comments)
            indicators_dict[f"{indicator_type}_{ind_id}"] = val == "Yes"
            indicators_dict[f"{indicator_type}_{ind_id}_comment"] = comment
        except ValueError as ve:
            print(f"Indicator is not found: {ve}")
    return indicators_dict


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


def _map_supplementary_questions(supplementary_questions: list) -> list[dict[str, Any]]:
    """Map supplementary questions to the expected format."""
    mapped_questions = []
    for question_list in supplementary_questions:
        for t, question in question_list:
            mapped_questions.append({"key": question["key"], "answer": question["answer"]})
    return mapped_questions


def _collect_outcome_comments(outcome_entry: dict[str, Any], group_comments: dict[str, list]) -> str:
    """Collect all unique comments for an outcome."""
    all_outcome_comments = []
    seen_comments = set()

    g_key = outcome_entry.get("group_key")
    if g_key and g_key in group_comments:
        for c in group_comments[g_key]:
            if c not in seen_comments:
                all_outcome_comments.append(c)
                seen_comments.add(c)
    elif outcome_entry.get("org_comment"):
        c = outcome_entry.get("org_comment")
        if c not in seen_comments:
            all_outcome_comments.append(c)
            seen_comments.add(c)

    return "\n\n".join(all_outcome_comments) if all_outcome_comments else ""


def _process_outcome(
    outcome_key: str,
    outcome: dict[str, Any],
    outcomes: dict[str, list],
    supplementary_questions: dict[str, list],
    group_comments: dict[str, list],
    status_map: dict[str, str],
) -> dict[str, Any] | None:
    """Process a single outcome and return its assessment structure."""
    outcome_data = outcomes.get(outcome_key, [])

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


def _build_metadata(
    assessment_meta: dict[str, Any], organisations: dict[str, Any], systems: dict[str, Any]
) -> dict[str, Any]:
    """Build the metadata section of the assessment."""
    meta_fields = [
        "system_profile",
        "review_type",
        "assessment_status_description",
        "assessment_version",
        "assessment_status_changed_to_submtd",
        "assessment_last_updated",
        "assessment_progress_organisation",
        "assessment_review_type",
    ]
    return {k: v for k, v in assessment_meta.items() if k in meta_fields} | {
        "organisation": organisations[assessment_meta["hashed_organisation_id"]],
        "system": systems[assessment_meta["hashed_system_id"]],
    }


def _build_review_metadata(
    assessment_meta: dict[str, Any], organisations: dict[str, Any], systems: dict[str, Any]
) -> dict[str, Any]:
    """Build the metadata section of the assessment."""
    meta_fields = [
        "system_profile",
        "review_type",
        "assessment_status_description",
        "assessment_version",
        "assessment_status_changed_to_aseing",
        "assessment_last_updated",
        "assessment_progress_assessor",
        "assessment_review_type",
    ]
    return {k: v for k, v in assessment_meta.items() if k in meta_fields} | {
        "organisation": organisations[assessment_meta["hashed_organisation_id"]],
        "system": systems[assessment_meta["hashed_system_id"]],
    }


def generate_assessment_structure(
    definition_structure: dict[str, dict[str, Any]],
    assessment_meta: dict[str, Any],
    old_assessment_data: list[dict[str, Any]],
    organisations: dict[str, Any],
    systems: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate an assessment structure to new format from a definition structure
    and old assessment data
    :param old_assessment_data:
    :param assessment_meta:
    :param definition_structure:
    :param organisations:
    :param systems:
    :return: Assessment structure dictionary
    """
    assessment = {}
    version_key = assessment_meta.get("assessment_version_id", "unknown")
    status_map = {"ACH": "Achieved", "P_ACH": "Partially achieved", "N_ACH": "Not achieved"}

    # Parse old assessment data
    group_comments, outcomes, supplementary_questions = _parse_old_assessment_data(old_assessment_data)

    # Process all outcomes
    objectives = definition_structure[version_key].get("objectives", {})
    for objective_key, objective in objectives.items():
        for principle_key, principle in objective.get("principles", {}).items():
            for outcome_key, outcome in principle.get("outcomes", {}).items():
                outcome_structure = _process_outcome(
                    outcome_key, outcome, outcomes, supplementary_questions, group_comments, status_map
                )
                if outcome_structure:
                    assessment[outcome_key] = outcome_structure

    # Add metadata
    assessment["meta_data"] = _build_metadata(assessment_meta, organisations, systems)

    return assessment_transform_to_outcome_format(assessment)


def generate_review_structure(
    definition_structure: dict[str, dict[str, Any]],
    assessment_meta: dict[str, Any],
    old_assessment_data: list[dict[str, Any]],
    organisations: dict[str, Any],
    systems: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate an review structure to new format from a definition structure
    and old assessment data
    :param old_assessment_data:
    :param assessment_meta:
    :param definition_structure:
    :param organisations:
    :param systems:
    :return: Assessment structure dictionary
    """
    review: dict[str, Any] = {}
    version_key = assessment_meta.get("assessment_version_id", "unknown")
    status_map = {"ACH": "Achieved", "P_ACH": "Partially achieved", "N_ACH": "Not achieved"}

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
    review["meta_data"] = _build_review_metadata(assessment_meta, organisations, systems)
    return review_transform_to_outcome_format(review)


def get_assessment_data():
    """
    Load the zip file contents in to individual dicts
    :return:
    """
    assessments = defaultdict(list)
    assessments_metadata = defaultdict(dict)
    with gzip.open(Path(__file__).parent / "data/assessments-combined/cos-igps/all.json.gz", "rt") as f:
        print("Loading assessments data...")
        for line in f:
            data = json.loads(line.strip())
            assessments[data["hashed_assessment_id"]].append(data)
        print("Assessment data loaded")

    with gzip.open(Path(__file__).parent / "data/assessments-combined/overview/all.json.gz", "rt") as f:
        print("Loading assessments meta data...")
        for line in f:
            data = json.loads(line.strip())
            assessments_metadata[data["hashed_assessment_id"]] = data
        print("Assessment meta data loaded")
    return assessments, assessments_metadata


def get_id_mappings():
    entries = {}
    for entry_type in ["assessments", "organisations", "systems"]:
        with gzip.open(Path(__file__).parent / f"data/hashed_ids/{entry_type}.json.gz", "r") as f:
            print(f"Loading {entry_type} data...")
            for line in f:
                data = json.loads(line.strip())
                entries.setdefault(entry_type, {})[data[f"hashed_{entry_type[:-1]}_id"]] = data
    return entries


# Load the assessments and its metadata
assessments, assessments_metadata = get_assessment_data()
orgs_and_systems = get_id_mappings()

organisations = orgs_and_systems["organisations"]
systems = orgs_and_systems["systems"]

missing_assessments = []

for assessment_id, assessment_metadata in assessments_metadata.items():
    assessment_data = assessments.get(assessment_id)
    if assessment_data:
        transformed_data = generate_assessment_structure(
            build_definition_structure(), assessment_metadata, assessment_data, organisations, systems
        )
        transformed_review_data = generate_review_structure(
            build_definition_structure(), assessment_metadata, assessment_data, organisations, systems
        )
        with open(Path(__file__).parent / f"data/assessments-transformed/{assessment_id}.json", "w") as output_file:
            json.dump(transformed_data, output_file, indent=4)
        with open(
            Path(__file__).parent / f"data/assessments-transformed/{assessment_id}-review.json", "w"
        ) as output_file:
            json.dump(transformed_review_data, output_file, indent=4)
    else:
        missing_assessments.append(assessment_id)

print(f"Following assessments were not found count: {len(missing_assessments)}")
for id in missing_assessments:
    print(f"Assessment not found {id}")
