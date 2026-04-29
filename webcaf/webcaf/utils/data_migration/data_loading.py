import gzip
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any


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
            record = json.loads(line.strip())
            assessments[record["hashed_assessment_id"]].append(record)
        print("Assessment data loaded")

    with gzip.open(Path(__file__).parent / "data/assessments-combined/overview/all.json.gz", "rt") as f:
        print("Loading assessments meta data (1)...")
        for line in f:
            record = json.loads(line.strip())
            assessments_metadata[record["hashed_assessment_id"]] = record
        print("Assessment meta data loaded")

    with gzip.open(Path(__file__).parent / "data/hashed_ids/assessments.json.gz", "rt") as f:
        print("Loading assessments meta data (2)...")
        for line in f:
            record = json.loads(line.strip())
            assessments_metadata[record["hashed_assessment_id"]] = (
                assessments_metadata[record["hashed_assessment_id"]] | record
            )
        print("Assessment meta data loaded")

    return assessments, assessments_metadata


def get_id_mappings():
    entries = {}
    for entry_type in ["assessments", "organisations", "systems"]:
        with gzip.open(Path(__file__).parent / f"data/hashed_ids/{entry_type}.json.gz", "r") as f:
            print(f"Loading {entry_type} data...")
            for line in f:
                record = json.loads(line.strip())
                entries.setdefault(entry_type, {})[record[f"hashed_{entry_type[:-1]}_id"]] = record
    return entries


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
    key: str | None = item.get("key", None)
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


# ============================================================================
# Definition Structure Building Functions
# ============================================================================


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
