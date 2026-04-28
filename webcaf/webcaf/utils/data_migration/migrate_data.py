"""
Data Migration and Transformation Script for WebCAF Assessment Data

This module handles the migration of legacy WebCAF assessment data to the new format,
making it compatible with the data analytics tools.

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
- `data/assessments-transformed/assessments/{assessment_id}.json`: Transformed assessment data
- `data/assessments-transformed/reviews/{review_id}.json`: Transformed review data
- `data/assessments-transformed/organisations/{organisation_id}.json`: Transformed organisation data
- `data/assessments-transformed/systems/{system_id}.json`: Transformed system data
"""
import json
import re
from functools import cache, partial
from pathlib import Path
from typing import Any, Tuple

from webcaf.webcaf.utils.data_analysis import (
    transform_assessment,
    transform_organisation,
    transform_review,
    transform_system,
)
from webcaf.webcaf.utils.data_migration.assessment_transformer import (
    transform_assessment_v1_to_v2,
)
from webcaf.webcaf.utils.data_migration.data_loading import (
    build_definition_structure,
    get_assessment_data,
    get_id_mappings,
)
from webcaf.webcaf.utils.data_migration.review_transformer import (
    transform_review_v1_to_v2,
)

TRANSFORMED_DATA_DIR = "data/assessments-transformed"

# Output subdirectories
ASSESSMENTS_OUTPUT_DIR = "assessments"
REVIEWS_OUTPUT_DIR = "reviews"
ORGANISATIONS_OUTPUT_DIR = "organisations"
SYSTEMS_OUTPUT_DIR = "systems"
OUTPUT_SUBDIRS = [ASSESSMENTS_OUTPUT_DIR, REVIEWS_OUTPUT_DIR, ORGANISATIONS_OUTPUT_DIR, SYSTEMS_OUTPUT_DIR]


def _build_metadata(
    assessment_meta: dict[str, Any], organisations: dict[str, Any], systems: dict[str, Any]
) -> dict[str, Any]:
    """Build the metadata section of the assessment."""
    meta_fields = [
        "system_profile",
        "assessment_status_description",
        "assessment_version",
        "assessment_status_changed_to_submtd",
        "assessment_last_updated",
        "assessment_progress_organisation",
    ]
    meta_data = {k: v for k, v in assessment_meta.items() if k in meta_fields}
    if organisation := organisations[assessment_meta["hashed_organisation_id"]]:
        meta_data["organisation_id"] = organisation["organisation_id"]
        meta_data["hashed_organisation_id"] = assessment_meta["hashed_organisation_id"]
    if system := systems[assessment_meta["hashed_system_id"]]:
        meta_data["system_id"] = system["system_id"]
        meta_data["hashed_system_id"] = assessment_meta["hashed_system_id"]
    meta_data["assessment_id"] = assessment_meta["assessment_id"]
    meta_data["hashed_assessment_id"] = assessment_meta["hashed_assessment_id"]

    # Set CAF version information
    if assessment_version := assessment_meta["assessment_version"]:
        matched_ = re.match(r"CAF (?P<version>\d.\d)\s+(?P<description>.*)", assessment_version)
        meta_data["caf_version"] = matched_.group("version") if matched_ and matched_.groups() else None
        meta_data["caf_description"] = matched_.group("description") if matched_ and matched_.groups() else None

    # Map the review type
    if review_type := assessment_meta.get("review_type", "not_decided"):
        meta_data["review_type"] = {
            "self_assessment": "self_assessment",
            "third-party-company": "independent",
            "peer-review-organisation": "peer_review",
            "not_decided": "not_decided",
        }.get(review_type, "not_decided")
    else:
        # If ype set to None
        meta_data["review_type"] = "self_assessment"
    meta_data["app_version"] = "webcaf-1"
    return meta_data


def _build_review_metadata(
    assessment_meta: dict[str, Any], organisations: dict[str, Any], systems: dict[str, Any]
) -> dict[str, Any]:
    """Build the metadata section of the review.

    Maps old-format fields to the structure expected by transform_review:
      - review_last_updated  ← assessment_last_updated
      - review_created       ← assessment_status_changed_to_aseing
    Fields not present in the old data format (additional_information, review_completion,
    review_finalised) are omitted and will resolve to empty defaults in the transformer.
    """
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
    meta_data = {k: v for k, v in assessment_meta.items() if k in meta_fields}
    meta_data.update(
        {
            "organisation": organisations[assessment_meta["hashed_organisation_id"]],
            "system": systems[assessment_meta["hashed_system_id"]],
            "assessment_id": assessment_meta["hashed_assessment_id"],
            "review_last_updated": assessment_meta.get("assessment_last_updated"),
            "review_created": assessment_meta.get("assessment_status_changed_to_aseing"),
            "app_version": "webcaf-1",
        }
    )
    return meta_data


@cache
def min_profile_requirements() -> dict[str, dict[str, str]]:
    with open(Path(__file__).parent / "data/profile-lookup/data.json") as file_pointer:
        profile_data = json.load(file_pointer)
    return {entry["key"]: entry for entry in profile_data}


def profile_met_callback(
    current_assessment: dict[str, Any], meta_data: dict[str, Any], outcome_code: str, status: str | None
) -> Tuple[str, str] | None:
    minimum_profile_requirements_data = min_profile_requirements()
    achievement_level_mapping = {"ACH": 3, "PAC": 2, "NAC": 1}
    status_to_display = {"PAC": "Partially achieved", "NAC": "Not achieved", "ACH": "Achieved"}
    display_to_status = {"Partially achieved": "PAC", "Not achieved": "NAC", "Achieved": "ACH"}
    minimum_requirement = minimum_profile_requirements_data.get(outcome_code, {}).get(
        meta_data.get("system_profile", "-non-existant-")
    )

    if status and minimum_requirement:
        is_requirement_met = (
            "Met"
            if achievement_level_mapping[minimum_requirement[0]] <= achievement_level_mapping[display_to_status[status]]
            else "Not met"
        )
        required_status_display = status_to_display[minimum_requirement[0]]
        return is_requirement_met, required_status_display
    return None


def generate_assessment_structure(
    definition_structure: dict[str, dict[str, Any]],
    assessment_meta: dict[str, Any],
    old_assessment_data: list[dict[str, Any]],
    organisations: dict[str, Any],
    systems: dict[str, Any],
) -> Tuple[dict[str, Any], dict[str, Any]]:
    """
    Generate an assessment structure to new format from a definition structure
    and old assessment data
    :param old_assessment_data:
    :param assessment_meta:
    :param definition_structure:
    :param organisations:
    :param systems:
    :return: Tuple of Assessment structure dictionary and Assessment structure in new format
    """
    assessment = transform_assessment_v1_to_v2(definition_structure, assessment_meta, old_assessment_data)
    # Add metadata
    meta_data = _build_metadata(assessment_meta, organisations, systems)
    return (
        transform_assessment(assessment, meta_data, partial(profile_met_callback, assessment, meta_data)),
        assessment,
    )


def generate_review_structure(
    definition_structure: dict[str, dict[str, Any]],
    assessment_meta: dict[str, Any],
    transformed_assessment_data: dict[str, Any],
    old_assessment_data: list[dict[str, Any]],
    organisations: dict[str, Any],
    systems: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate an review structure to new format from a definition structure
    and old assessment data
    :param old_assessment_data:
    :param assessment_meta:
    :param transformed_assessment_data
    :param definition_structure:
    :param organisations:
    :param systems:
    :return: Assessment structure dictionary
    """
    review = transform_review_v1_to_v2(definition_structure, assessment_meta, old_assessment_data)
    meta_data = _build_review_metadata(assessment_meta, organisations, systems)
    return transform_review(
        review,
        meta_data | assessment_meta,
        partial(profile_met_callback, transformed_assessment_data, assessment_meta),
    )


def _create_output_directories() -> None:
    """Create output directories for transformed data."""
    for subdirectory in OUTPUT_SUBDIRS:
        result_path = Path(__file__).parent / TRANSFORMED_DATA_DIR / subdirectory
        result_path.mkdir(parents=True, exist_ok=True)


def _write_transformed_assessment(assessment_id: str, transformed_data: dict[str, Any]) -> None:
    """Write transformed assessment data to file."""
    output_file_path = Path(__file__).parent / TRANSFORMED_DATA_DIR / ASSESSMENTS_OUTPUT_DIR / f"{assessment_id}.json"
    with open(output_file_path, "w") as output_file:
        json.dump(transformed_data, output_file, separators=(",", ":"))


def _write_transformed_review(assessment_id: str, transformed_review_data: dict[str, Any]) -> None:
    """Write transformed review data to file."""
    output_file_path = Path(__file__).parent / TRANSFORMED_DATA_DIR / REVIEWS_OUTPUT_DIR / f"{assessment_id}.json"
    with open(output_file_path, "w") as output_file:
        json.dump(transformed_review_data, output_file, separators=(",", ":"))


def _write_organisations_data(organisations: dict[str, Any]) -> None:
    """Write organisations data to individual files."""
    for org_id, org_data in organisations.items():
        output_file_path = Path(__file__).parent / TRANSFORMED_DATA_DIR / ORGANISATIONS_OUTPUT_DIR / f"{org_id}.json"
        with open(output_file_path, "w") as output_file:
            json.dump(
                transform_organisation(
                    {
                        "organisation_name": org_data["organisation_name"],
                        "organisation_id": org_data["organisation_id"],
                        "app_version": "webcaf-1",
                    }
                ),
                output_file,
                separators=(",", ":"),
            )


def _write_systems_data(systems: dict[str, Any]) -> None:
    """Write systems data to individual files."""
    for system_id, system_data in systems.items():
        output_file_path = Path(__file__).parent / TRANSFORMED_DATA_DIR / SYSTEMS_OUTPUT_DIR / f"{system_id}.json"
        with open(output_file_path, "w") as output_file:
            json.dump(
                transform_system(
                    {
                        "system_name": system_data["system_name"],
                        "system_id": system_data["system_id"],
                        "app_version": "webcaf-1",
                    }
                ),
                output_file,
                separators=(",", ":"),
            )


# ============================================================================
# Main Transformation Logic
# ============================================================================


def _process_assessments(
    assessments: dict[str, list],
    assessments_metadata: dict[str, dict[str, Any]],
    definition_structure: dict[str, dict[str, Any]],
    organisations: dict[str, Any],
    systems: dict[str, Any],
) -> list[str]:
    """
    Process all assessments and generate transformed data.

    Args:
        assessments: Dictionary of assessments by ID
        assessments_metadata: Dictionary of assessment metadata by ID
        definition_structure: Definition structure for transformations
        organisations: Dictionary of organisations
        systems: Dictionary of systems

    Returns:
        List of assessment IDs that were not found
    """
    missing_assessments = []

    for assessment_id, assessment_metadata in assessments_metadata.items():
        assessment_data = assessments.get(assessment_id)

        if assessment_data:
            transformed_data, assessment_v2_data = generate_assessment_structure(
                definition_structure, assessment_metadata, assessment_data, organisations, systems
            )
            transformed_review_data = generate_review_structure(
                definition_structure,
                assessment_metadata,
                transformed_data,
                assessment_data,
                organisations,
                systems,
            )
            _write_transformed_assessment(assessment_id, transformed_data)
            _write_transformed_review(assessment_id, transformed_review_data)
        else:
            missing_assessments.append(assessment_id)

    return missing_assessments


def _report_missing_assessments(missing_assessments: list[str]) -> None:
    """Report assessments that were not found."""
    print(f"Following assessments were not found count: {len(missing_assessments)}")
    for missing_assessment_id in missing_assessments:
        print(f"Assessment not found {missing_assessment_id}")


def main() -> None:
    """Main entry point for the data migration and transformation process."""
    # Load data
    assessments, assessments_metadata = get_assessment_data()
    orgs_and_systems = get_id_mappings()

    organisations = orgs_and_systems["organisations"]
    systems = orgs_and_systems["systems"]

    # Build definition structure
    definition_structure = build_definition_structure()

    # Create output directories
    _create_output_directories()

    # Process assessments
    missing_assessments = _process_assessments(
        assessments, assessments_metadata, definition_structure, organisations, systems
    )

    # Write organisations and systems data
    _write_organisations_data(organisations)
    _write_systems_data(systems)

    # Report results
    _report_missing_assessments(missing_assessments)


if __name__ == "__main__":
    main()
