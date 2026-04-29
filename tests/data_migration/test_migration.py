"""
Tests for WebCAF data transformation: output structure and calculated field values.

Criteria:
1. Comprehensive output structure — all necessary data from input is present in output
2. Calculated field values (status mappings, metadata population) are correct
"""

import unittest
from typing import Any, Dict, List
from unittest.mock import patch

from webcaf.webcaf.utils.data_migration.migrate_data import (
    _build_metadata,
    _build_review_metadata,
    generate_assessment_structure,
    generate_review_structure,
)

MOCK_TRANSFORM_PATH = "webcaf.webcaf.utils.data_migration.migrate_data.transform_assessment"

# Realistic IDs matching the actual data format from overview/all.json and cos-igps/all.json
_HASH_ORG_ID = "06b840861a2cb236d6deebd4d50769b7d2d8e97166ab78d4908b3ee15e49e564"
_ORG_ID = 11111
_HASH_SYS_ID = "4442313c0c83a40d1c8193b3cfa5f07c19cf8bdd50baffdb0e6929a5fad2fc6c"
_SYS_ID = 22222
_HASH_ASSESSMENT_ID = "48e91912409f6e5d83c0ebfdaa2d78f041b51c9efb7b0efe377a3b6301f75910"
_ASSESSMENT_ID = 33333


# ============================================================================
# Shared Test Data Helpers
# ============================================================================


def _make_definition_structure() -> Dict[str, Any]:
    return {
        "v3.0": {
            "assessment_version_id": "v3.0",
            "display_name": "CAF v3.0",
            "objectives": {
                "A": {
                    "code": "A",
                    "title": "Governance and risk management",
                    "description": "Comprehensive security risk management",
                    "principles": {
                        "A1": {
                            "code": "A1",
                            "title": "Security governance",
                            "description": "Establish governance framework",
                            "outcomes": {
                                "A1.a": {
                                    "code": "A1.a",
                                    "title": "Governance outcome",
                                    "description": "Effective governance in place",
                                    "indicators": {
                                        "achieved": {
                                            "A1.a.1": {
                                                "description": "Board oversees security",
                                                "ncsc-index": "A1.a.1",
                                            },
                                            "A1.a.2": {
                                                "description": "Security policies approved",
                                                "ncsc-index": "A1.a.2",
                                            },
                                        },
                                        "partially-achieved": {
                                            "A1.a.3": {"description": "Partial oversight", "ncsc-index": "A1.a.3"}
                                        },
                                        "not-achieved": {
                                            "A1.a.4": {"description": "No formal governance", "ncsc-index": "A1.a.4"}
                                        },
                                    },
                                    "external_links": {},
                                },
                                "A1.b": {
                                    "code": "A1.b",
                                    "title": "Risk management outcome",
                                    "description": "Risk management processes established",
                                    "indicators": {
                                        "achieved": {},
                                        "partially-achieved": {},
                                        "not-achieved": {},
                                    },
                                    "external_links": {},
                                },
                            },
                            "external_links": {},
                        }
                    },
                },
                "B": {
                    "code": "B",
                    "title": "Information security",
                    "description": "Information security management",
                    "principles": {
                        "B1": {
                            "code": "B1",
                            "title": "Information classification",
                            "description": "Classify information",
                            "outcomes": {
                                "B1.a": {
                                    "code": "B1.a",
                                    "title": "Classification outcome",
                                    "description": "Information properly classified",
                                    "indicators": {
                                        "achieved": {
                                            "B1.a.1": {
                                                "description": "Classification policy exists",
                                                "ncsc-index": "B1.a.1",
                                            }
                                        },
                                        "partially-achieved": {},
                                        "not-achieved": {},
                                    },
                                    "external_links": {},
                                }
                            },
                            "external_links": {},
                        }
                    },
                },
            },
        }
    }


def _make_complete_assessment_data() -> List[Dict[str, Any]]:
    """
    Assessment indicator data matching the schema of cos-igps/all.json.
    Each entry mirrors the real format: hashed_assessment_id, group_key, key,
    answer/assessor_answer, achievement/assessor_achievement, org_comment/assessor_comment.
    Group keys follow the G_{outcome}_{n} convention from the real data.
    """
    return [
        # Outcome A1.a — ACH
        {
            "hashed_assessment_id": _HASH_ASSESSMENT_ID,
            "key": "A1.a",
            "group_key": "G_A1.a",
            "answer": None,
            "assessor_answer": None,
            "achievement": "ACH",
            "assessor_achievement": None,
            "org_comment": "Board actively oversees security",
            "assessor_comment": None,
        },
        # Indicators for A1.a — achieved
        {
            "hashed_assessment_id": _HASH_ASSESSMENT_ID,
            "key": "A1.a.1",
            "group_key": "G_A1.a_1",
            "answer": "Yes",
            "assessor_answer": None,
            "achievement": None,
            "assessor_achievement": None,
            "org_comment": "Board has documented security oversight",
            "assessor_comment": None,
        },
        {
            "hashed_assessment_id": _HASH_ASSESSMENT_ID,
            "key": "A1.a.2",
            "group_key": "G_A1.a_2",
            "answer": "Yes",
            "assessor_answer": None,
            "achievement": None,
            "assessor_achievement": None,
            "org_comment": "Security policies are board approved",
            "assessor_comment": None,
        },
        # Indicator for A1.a — partially-achieved
        {
            "hashed_assessment_id": _HASH_ASSESSMENT_ID,
            "key": "A1.a.3",
            "group_key": "G_A1.a_3",
            "answer": "No",
            "assessor_answer": None,
            "achievement": None,
            "assessor_achievement": None,
            "org_comment": "Some oversight gaps identified",
            "assessor_comment": None,
        },
        # Indicator for A1.a — not-achieved
        {
            "hashed_assessment_id": _HASH_ASSESSMENT_ID,
            "key": "A1.a.4",
            "group_key": "G_A1.a_4",
            "answer": "No",
            "assessor_answer": None,
            "achievement": None,
            "assessor_achievement": None,
            "org_comment": "Not formally implemented",
            "assessor_comment": None,
        },
        # Supplementary question for A1.a
        {
            "hashed_assessment_id": _HASH_ASSESSMENT_ID,
            "key": "A1.a-SQ",
            "group_key": "G_A1.a",
            "answer": "Quarterly board meetings",
            "assessor_answer": None,
            "achievement": None,
            "assessor_achievement": None,
            "org_comment": "",
            "assessor_comment": None,
        },
        # Outcome A1.b — PAC
        {
            "hashed_assessment_id": _HASH_ASSESSMENT_ID,
            "key": "A1.b",
            "group_key": "G_A1.b",
            "answer": None,
            "assessor_answer": None,
            "achievement": "PAC",
            "assessor_achievement": None,
            "org_comment": "Risk management framework in place",
            "assessor_comment": None,
        },
        # Outcome B1.a — ACH
        {
            "hashed_assessment_id": _HASH_ASSESSMENT_ID,
            "key": "B1.a",
            "group_key": "G_B1.a",
            "answer": None,
            "assessor_answer": None,
            "achievement": "ACH",
            "assessor_achievement": None,
            "org_comment": "Classification scheme established",
            "assessor_comment": None,
        },
        # Indicator for B1.a — achieved
        {
            "hashed_assessment_id": _HASH_ASSESSMENT_ID,
            "key": "B1.a.1",
            "group_key": "G_B1.a_1",
            "answer": "Yes",
            "assessor_answer": None,
            "achievement": None,
            "assessor_achievement": None,
            "org_comment": "Policy document created",
            "assessor_comment": None,
        },
    ]


def _make_partial_assessment_data() -> List[Dict[str, Any]]:
    """Partial data: only A1.a with two of its four indicators. A1.b and B1.a absent."""
    return [
        {
            "hashed_assessment_id": _HASH_ASSESSMENT_ID,
            "key": "A1.a",
            "group_key": "G_A1.a",
            "answer": None,
            "assessor_answer": None,
            "achievement": "PAC",
            "assessor_achievement": None,
            "org_comment": "Partially implemented governance",
            "assessor_comment": None,
        },
        {
            "hashed_assessment_id": _HASH_ASSESSMENT_ID,
            "key": "A1.a.1",
            "group_key": "G_A1.a_1",
            "answer": "Yes",
            "assessor_answer": None,
            "achievement": None,
            "assessor_achievement": None,
            "org_comment": "Board exists but not formal",
            "assessor_comment": None,
        },
        {
            "hashed_assessment_id": _HASH_ASSESSMENT_ID,
            "key": "A1.a.3",
            "group_key": "G_A1.a_3",
            "answer": "No",
            "assessor_answer": None,
            "achievement": None,
            "assessor_achievement": None,
            "org_comment": "Gaps in oversight",
            "assessor_comment": None,
        },
    ]


def _make_assessment_metadata() -> Dict[str, Any]:
    """
    Assessment metadata matching the schema of overview/all.json.
    system_profile uses uppercase (BASELINE) as in the real data.
    assessment_version_id uses a synthetic key matching the test definition structure.
    """
    return {
        "hashed_assessment_id": _HASH_ASSESSMENT_ID,
        "hashed_organisation_id": _HASH_ORG_ID,
        "hashed_system_id": _HASH_SYS_ID,
        "assessment_id": _ASSESSMENT_ID,
        "organisation_id": _ORG_ID,
        "system_id": _SYS_ID,
        "assessment_version_id": "v3.0",  # synthetic — matches test definition structure key
        "system_profile": "BASELINE",
        "review_type": None,
        "assessment_status_description": "Assessing",
        "assessment_version": "CAF 3.1 GovAssure (Full)",
        "assessment_status_changed_to_submtd": "2023-03-06 13:26:53.221870",
        "assessment_last_updated": "2023-03-06 13:26:53.221870",
        "assessment_progress_organisation": 3.44,
        "assessment_review_type": None,
        "assessment_progress_assessor": 0.0,
        "assessment_status_changed_to_aseing": None,
    }


def _make_assessment_metadata_with_review_info() -> Dict[str, Any]:
    """
    Metadata extended with review-specific fields (additional_information,
    review_completion, review_finalised) to exercise review_details and metadata
    population in generate_review_structure.
    """
    return {
        **_make_assessment_metadata(),
        "additional_information": {
            "iar_period": {"start_date": "01/01/2023", "end_date": "31/12/2023"},
            "company_details": {"company_name": "Test Assessor Ltd"},
            "review_method": "Remote assessment",
            "quality_of_evidence": "Good evidence provided",
        },
        "review_completion": {"review_completed_at": "2023-06-15T12:00:00"},
        "review_finalised": {"review_finalised_at": "2023-06-20T10:00:00"},
    }


def _make_review_assessment_data() -> List[Dict[str, Any]]:
    """
    Review indicator data matching the schema of cos-igps/all.json.
    Assessor fields (assessor_answer, assessor_comment, assessor_achievement) are populated.
    """
    return [
        {
            "hashed_assessment_id": _HASH_ASSESSMENT_ID,
            "key": "A1.a",
            "group_key": "G_A1.a",
            "achievement": "ACH",
            "assessor_achievement": "ACH",
            "org_comment": "Board actively oversees security",
            "assessor_comment": "Assessment is accurate. Evidence well documented.",
        },
        {
            "hashed_assessment_id": _HASH_ASSESSMENT_ID,
            "key": "A1.a.1",
            "group_key": "G_A1.a_1",
            "answer": "Yes",
            "assessor_answer": "Yes",
            "assessor_comment": "Confirmed through board meeting minutes",
        },
        {
            "hashed_assessment_id": _HASH_ASSESSMENT_ID,
            "key": "A1.a.2",
            "group_key": "G_A1.a_2",
            "answer": "Yes",
            "assessor_answer": "Yes",
            "assessor_comment": "Policy signatures verified",
        },
        {
            "hashed_assessment_id": _HASH_ASSESSMENT_ID,
            "key": "A1.a.3",
            "group_key": "G_A1.a_3",
            "answer": "No",
            "assessor_answer": "No",
            "assessor_comment": "Minor gaps noted, acceptable",
        },
        {
            "hashed_assessment_id": _HASH_ASSESSMENT_ID,
            "key": "A1.a.4",
            "group_key": "G_A1.a_4",
            "answer": "No",
            "assessor_answer": "No",
            "assessor_comment": "Not formally required for this organization",
        },
        {
            "hashed_assessment_id": _HASH_ASSESSMENT_ID,
            "key": "A1.b",
            "group_key": "G_A1.b",
            "achievement": "PAC",
            "assessor_achievement": "PAC",
            "org_comment": "Risk processes exist but need refinement",
            "assessor_comment": "Risk processes exist but need refinement",
        },
    ]


def _make_organisations() -> Dict[str, Any]:
    return {
        _HASH_ORG_ID: {
            "hashed_organisation_id": _HASH_ORG_ID,
            "organisation_id": _ORG_ID,
            "name": "Test Organization",
            "sector": "Finance",
        }
    }


def _make_systems() -> Dict[str, Any]:
    return {
        _HASH_SYS_ID: {
            "hashed_system_id": _HASH_SYS_ID,
            "system_id": _SYS_ID,
            "name": "Core Banking System",
        }
    }


# ============================================================================
# Base Test Class
# ============================================================================


class TransformTestBase(unittest.TestCase):
    """Base class providing shared test data for all transform test classes."""

    def setUp(self):
        self.maxDiff = None
        self.definition_structure = _make_definition_structure()
        self.complete_assessment_data = _make_complete_assessment_data()
        self.partial_assessment_data = _make_partial_assessment_data()
        self.assessment_metadata = _make_assessment_metadata()
        self.review_assessment_data = _make_review_assessment_data()
        self.organisations = _make_organisations()
        self.systems = _make_systems()


# ============================================================================
# Test Cases: Metadata Building
# ============================================================================


class TestMetadataBuilding(TransformTestBase):
    """Metadata passed to the transformer contains all required fields."""

    def test_build_assessment_metadata_required_fields(self):
        """All required assessment metadata fields are present."""
        metadata = _build_metadata(self.assessment_metadata, self.organisations, self.systems)

        for field in (
            "system_profile",
            "review_type",
            "assessment_status_description",
            "assessment_version",
            "assessment_last_updated",
        ):
            self.assertIn(field, metadata)

    def test_build_assessment_metadata_organisation_and_system_ids(self):
        """organisation_id and system_id are looked up and embedded in metadata."""
        metadata = _build_metadata(self.assessment_metadata, self.organisations, self.systems)

        self.assertEqual(metadata["organisation_id"], _ORG_ID)
        self.assertEqual(metadata["system_id"], _SYS_ID)
        self.assertEqual(metadata["assessment_id"], _ASSESSMENT_ID)

    def test_build_assessment_metadata_excludes_review_only_fields(self):
        """Assessment metadata does not include review-specific fields."""
        metadata = _build_metadata(self.assessment_metadata, self.organisations, self.systems)

        self.assertNotIn("assessment_progress_assessor", metadata)
        self.assertNotIn("assessment_status_changed_to_aseing", metadata)

    def test_build_review_metadata_assessor_fields(self):
        """Review metadata includes assessor-specific fields."""
        metadata = _build_review_metadata(self.assessment_metadata, self.organisations, self.systems)

        self.assertIn("assessment_progress_assessor", metadata)
        self.assertIn("assessment_status_changed_to_aseing", metadata)

    def test_build_review_metadata_organisation_embedded(self):
        """Organisation data is correctly embedded in review metadata."""
        metadata = _build_review_metadata(self.assessment_metadata, self.organisations, self.systems)

        self.assertEqual(metadata["organisation"]["name"], "Test Organization")
        self.assertEqual(metadata["organisation"]["hashed_organisation_id"], _HASH_ORG_ID)

    def test_build_review_metadata_system_embedded(self):
        """System data is correctly embedded in review metadata."""
        metadata = _build_review_metadata(self.assessment_metadata, self.organisations, self.systems)

        self.assertEqual(metadata["system"]["hashed_system_id"], _HASH_SYS_ID)

    def test_build_review_metadata_excludes_assessment_only_fields(self):
        """Review metadata does not include assessment-only date fields."""
        metadata = _build_review_metadata(self.assessment_metadata, self.organisations, self.systems)

        self.assertNotIn("assessment_status_changed_to_submtd", metadata)
        self.assertNotIn("assessment_progress_organisation", metadata)

    def test_build_review_metadata_maps_review_last_updated(self):
        """review_last_updated is mapped from assessment_last_updated."""
        metadata = _build_review_metadata(self.assessment_metadata, self.organisations, self.systems)

        self.assertEqual(
            metadata["review_last_updated"],
            self.assessment_metadata["assessment_last_updated"],
        )

    def test_build_review_metadata_maps_review_created(self):
        """review_created is mapped from assessment_status_changed_to_aseing."""
        metadata = _build_review_metadata(self.assessment_metadata, self.organisations, self.systems)

        self.assertEqual(
            metadata["review_created"],
            self.assessment_metadata["assessment_status_changed_to_aseing"],
        )


# ============================================================================
# Test Cases: Assessment Structure Generation (raw output)
# ============================================================================


class TestAssessmentGeneration(TransformTestBase):
    """Intermediate assessment dict produced by generate_assessment_structure."""

    @patch(MOCK_TRANSFORM_PATH)
    def test_complete_assessment_contains_all_outcomes(self, mock_transform):
        """All three outcomes from source data appear in the generated structure."""
        mock_transform.return_value = {"mocked": True}

        _, assessment = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.complete_assessment_data,
            self.organisations,
            self.systems,
        )

        self.assertIn("A1.a", assessment)
        self.assertIn("A1.b", assessment)
        self.assertIn("B1.a", assessment)

    @patch(MOCK_TRANSFORM_PATH)
    def test_complete_assessment_outcome_has_required_keys(self, mock_transform):
        """Each outcome dict has indicators, supplementary_questions, and confirmation."""
        mock_transform.return_value = {"mocked": True}

        _, assessment = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.complete_assessment_data,
            self.organisations,
            self.systems,
        )

        outcome = assessment["A1.a"]
        self.assertIn("indicators", outcome)
        self.assertIn("supplementary_questions", outcome)
        self.assertIn("confirmation", outcome)

    @patch(MOCK_TRANSFORM_PATH)
    def test_partial_assessment_excludes_missing_outcomes(self, mock_transform):
        """Outcomes absent from source data are not included in the structure."""
        mock_transform.return_value = {"mocked": True}

        _, assessment = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.partial_assessment_data,
            self.organisations,
            self.systems,
        )

        self.assertIn("A1.a", assessment)
        self.assertNotIn("B1.a", assessment)

    @patch(MOCK_TRANSFORM_PATH)
    def test_partial_assessment_outcome_status(self, mock_transform):
        """PAC achievement code maps to 'Partially achieved'."""
        mock_transform.return_value = {"mocked": True}

        _, assessment = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.partial_assessment_data,
            self.organisations,
            self.systems,
        )

        self.assertEqual(assessment["A1.a"]["confirmation"]["outcome_status"], "Partially achieved")

    @patch(MOCK_TRANSFORM_PATH)
    def test_indicator_keys_follow_type_id_pattern(self, mock_transform):
        """Indicator keys are formatted as {achievement-type}_{indicator-id}."""
        mock_transform.return_value = {"mocked": True}

        _, assessment = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.complete_assessment_data,
            self.organisations,
            self.systems,
        )

        indicators = assessment["A1.a"]["indicators"]
        self.assertIn("achieved_A1.a.1", indicators)
        self.assertIn("achieved_A1.a.2", indicators)
        self.assertIn("partially-achieved_A1.a.3", indicators)
        self.assertIn("not-achieved_A1.a.4", indicators)

    @patch(MOCK_TRANSFORM_PATH)
    def test_indicator_yes_answer_is_true(self, mock_transform):
        """An indicator answered 'Yes' is stored as boolean True."""
        mock_transform.return_value = {"mocked": True}

        _, assessment = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.complete_assessment_data,
            self.organisations,
            self.systems,
        )

        self.assertTrue(assessment["A1.a"]["indicators"]["achieved_A1.a.1"])

    @patch(MOCK_TRANSFORM_PATH)
    def test_indicator_no_answer_is_false(self, mock_transform):
        """An indicator answered 'No' is stored as boolean False."""
        mock_transform.return_value = {"mocked": True}

        _, assessment = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.complete_assessment_data,
            self.organisations,
            self.systems,
        )

        self.assertFalse(assessment["A1.a"]["indicators"]["partially-achieved_A1.a.3"])


# ============================================================================
# Test Cases: Review Structure Generation
# ============================================================================


class TestReviewGeneration(TransformTestBase):
    """Review output produced by generate_review_structure."""

    def test_review_has_outcomes_key(self):
        """The review structure has a top-level 'outcomes' list."""
        transformed, raw = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.complete_assessment_data,
            self.organisations,
            self.systems,
        )
        review = generate_review_structure(
            self.definition_structure,
            self.assessment_metadata,
            transformed,
            self.review_assessment_data,
            self.organisations,
            self.systems,
        )

        self.assertIn("outcomes", review)
        self.assertIsInstance(review["outcomes"], list)

    def test_review_outcomes_list_is_non_empty(self):
        """The outcomes list contains at least one entry."""
        transformed, raw = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.complete_assessment_data,
            self.organisations,
            self.systems,
        )
        review = generate_review_structure(
            self.definition_structure,
            self.assessment_metadata,
            transformed,
            self.review_assessment_data,
            self.organisations,
            self.systems,
        )

        self.assertGreater(len(review["outcomes"]), 0)

    def test_review_outcome_fields(self):
        """Each outcome entry in the review has the required fields."""
        transformed, raw = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.complete_assessment_data,
            self.organisations,
            self.systems,
        )
        review = generate_review_structure(
            self.definition_structure,
            self.assessment_metadata,
            transformed,
            self.review_assessment_data,
            self.organisations,
            self.systems,
        )

        a1a_outcome = next(o for o in review["outcomes"] if o.get("outcome_id") == "A1.a")
        for field in ("outcome_id", "review_decision", "review_comment", "indicators"):
            self.assertIn(field, a1a_outcome)

    def test_review_comment_preserved(self):
        """The assessor comment from source data is included in the review outcome."""
        transformed, raw = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.complete_assessment_data,
            self.organisations,
            self.systems,
        )
        review = generate_review_structure(
            self.definition_structure,
            self.assessment_metadata,
            transformed,
            self.review_assessment_data,
            self.organisations,
            self.systems,
        )

        a1a_outcome = next(o for o in review["outcomes"] if o.get("outcome_id") == "A1.a")
        self.assertIn("Assessment is accurate", a1a_outcome["review_comment"])


# ============================================================================
# Test Cases: Status Mapping (calculated values)
# ============================================================================


class TestStatusMapping(TransformTestBase):
    """Achievement status codes are correctly mapped to display strings."""

    @patch(MOCK_TRANSFORM_PATH)
    def test_ach_maps_to_achieved(self, mock_transform):
        """ACH maps to 'Achieved'."""
        mock_transform.return_value = {"mocked": True}

        _, assessment = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.complete_assessment_data,
            self.organisations,
            self.systems,
        )

        self.assertEqual(assessment["A1.a"]["confirmation"]["outcome_status"], "Achieved")

    @patch(MOCK_TRANSFORM_PATH)
    def test_pac_maps_to_partially_achieved(self, mock_transform):
        """PAC maps to 'Partially achieved'."""
        mock_transform.return_value = {"mocked": True}

        _, assessment = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.complete_assessment_data,
            self.organisations,
            self.systems,
        )

        self.assertEqual(assessment["A1.b"]["confirmation"]["outcome_status"], "Partially achieved")

    @patch(MOCK_TRANSFORM_PATH)
    def test_nac_maps_to_not_achieved(self, mock_transform):
        """NAC maps to 'Not achieved'."""
        mock_transform.return_value = {"mocked": True}
        nac_data = [
            {
                "hashed_assessment_id": _HASH_ASSESSMENT_ID,
                "key": "A1.a",
                "group_key": "G_A1.a",
                "answer": None,
                "achievement": "NAC",
                "org_comment": "Not implemented",
                "assessor_comment": None,
            },
            {
                "hashed_assessment_id": _HASH_ASSESSMENT_ID,
                "key": "A1.a.1",
                "group_key": "G_A1.a_1",
                "answer": "No",
                "org_comment": "",
                "assessor_comment": None,
            },
            {
                "hashed_assessment_id": _HASH_ASSESSMENT_ID,
                "key": "A1.a.2",
                "group_key": "G_A1.a_2",
                "answer": "No",
                "org_comment": "",
                "assessor_comment": None,
            },
            {
                "hashed_assessment_id": _HASH_ASSESSMENT_ID,
                "key": "A1.a.3",
                "group_key": "G_A1.a_3",
                "answer": "No",
                "org_comment": "",
                "assessor_comment": None,
            },
            {
                "hashed_assessment_id": _HASH_ASSESSMENT_ID,
                "key": "A1.a.4",
                "group_key": "G_A1.a_4",
                "answer": "No",
                "org_comment": "",
                "assessor_comment": None,
            },
        ]

        _, assessment = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            nac_data,
            self.organisations,
            self.systems,
        )

        self.assertEqual(assessment["A1.a"]["confirmation"]["outcome_status"], "Not achieved")

    @patch(MOCK_TRANSFORM_PATH)
    def test_missing_achievement_maps_to_na(self, mock_transform):
        """An unrecognised achievement code results in 'N/A'."""
        mock_transform.return_value = {"mocked": True}
        unknown_data = [
            {
                "hashed_assessment_id": _HASH_ASSESSMENT_ID,
                "key": "A1.a",
                "group_key": "G_A1.a",
                "answer": None,
                "achievement": "UNKNOWN",
                "org_comment": "Unknown status",
                "assessor_comment": None,
            },
            {
                "hashed_assessment_id": _HASH_ASSESSMENT_ID,
                "key": "A1.a.1",
                "group_key": "G_A1.a_1",
                "answer": "Yes",
                "org_comment": "",
                "assessor_comment": None,
            },
            {
                "hashed_assessment_id": _HASH_ASSESSMENT_ID,
                "key": "A1.a.2",
                "group_key": "G_A1.a_2",
                "answer": "Yes",
                "org_comment": "",
                "assessor_comment": None,
            },
            {
                "hashed_assessment_id": _HASH_ASSESSMENT_ID,
                "key": "A1.a.3",
                "group_key": "G_A1.a_3",
                "answer": "No",
                "org_comment": "",
                "assessor_comment": None,
            },
            {
                "hashed_assessment_id": _HASH_ASSESSMENT_ID,
                "key": "A1.a.4",
                "group_key": "G_A1.a_4",
                "answer": "No",
                "org_comment": "",
                "assessor_comment": None,
            },
        ]

        _, assessment = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            unknown_data,
            self.organisations,
            self.systems,
        )

        self.assertEqual(assessment["A1.a"]["confirmation"]["outcome_status"], "N/A")


# ============================================================================
# Test Cases: Edge Cases
# ============================================================================


class TestEdgeCases(TransformTestBase):
    """Output structure is correct for edge-case inputs."""

    @patch(MOCK_TRANSFORM_PATH)
    def test_empty_assessment_data_has_no_outcomes(self, mock_transform):
        """An empty source data list produces no outcome entries."""
        mock_transform.return_value = {"mocked": True}

        _, assessment = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            [],
            self.organisations,
            self.systems,
        )

        self.assertEqual(len(assessment), 0)

    @patch(MOCK_TRANSFORM_PATH)
    def test_outcome_in_definition_but_not_in_data_is_excluded(self, mock_transform):
        """An outcome that exists in the definition but has no source data is omitted."""
        mock_transform.return_value = {"mocked": True}

        _, assessment = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.partial_assessment_data,
            self.organisations,
            self.systems,
        )

        self.assertNotIn("A1.b", assessment)
        self.assertNotIn("B1.a", assessment)


# ============================================================================
# Test Cases: Data Integrity
# ============================================================================


class TestDataIntegrity(TransformTestBase):
    """All input data is preserved intact in the output structure."""

    @patch(MOCK_TRANSFORM_PATH)
    def test_all_indicators_present_in_assessment(self, mock_transform):
        """All four indicator entries from A1.a source data appear in the output."""
        mock_transform.return_value = {"mocked": True}

        _, assessment = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.complete_assessment_data,
            self.organisations,
            self.systems,
        )

        indicators = assessment["A1.a"]["indicators"]
        non_comment_keys = [k for k in indicators if not k.endswith("_comment")]
        self.assertGreaterEqual(len(non_comment_keys), 4)

    @patch(MOCK_TRANSFORM_PATH)
    def test_outcome_comment_preserved_in_confirmation(self, mock_transform):
        """The outcome-level org_comment is stored in confirm_outcome_confirm_comment."""
        mock_transform.return_value = {"mocked": True}

        _, assessment = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.complete_assessment_data,
            self.organisations,
            self.systems,
        )

        confirm_comment = assessment["A1.a"]["confirmation"]["confirm_outcome_confirm_comment"]
        self.assertIn("Board actively oversees security", confirm_comment)

    @patch(MOCK_TRANSFORM_PATH)
    def test_supplementary_questions_included(self, mock_transform):
        """Supplementary questions are included for the relevant outcome."""
        mock_transform.return_value = {"mocked": True}

        _, assessment = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.complete_assessment_data,
            self.organisations,
            self.systems,
        )

        self.assertGreater(len(assessment["A1.a"]["supplementary_questions"]), 0)

    @patch(MOCK_TRANSFORM_PATH)
    def test_supplementary_question_preserves_answer(self, mock_transform):
        """The supplementary question answer from source data is preserved."""
        mock_transform.return_value = {"mocked": True}

        _, assessment = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.complete_assessment_data,
            self.organisations,
            self.systems,
        )

        sq = next(q for q in assessment["A1.a"]["supplementary_questions"] if "A1.a-SQ" in q.get("key", ""))
        self.assertEqual(sq["answer"], "Quarterly board meetings")

    @patch(MOCK_TRANSFORM_PATH)
    def test_each_indicator_has_a_corresponding_comment_key(self, mock_transform):
        """For every indicator key there is a matching _comment key."""
        mock_transform.return_value = {"mocked": True}

        _, assessment = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.complete_assessment_data,
            self.organisations,
            self.systems,
        )

        indicators = assessment["A1.a"]["indicators"]
        for key in (k for k in indicators if not k.endswith("_comment")):
            self.assertIn(f"{key}_comment", indicators)


# ============================================================================
# Comprehensive end-to-end: Assessment output structure and calculated values
# ============================================================================


class TestAssessmentOutputStructure(TransformTestBase):
    """
    End-to-end tests (real transformer, no mocks) verifying that
    generate_assessment_structure produces a correctly populated output with:
      - self_assessment: metadata sourced from assessment_meta, outcomes list
      - assessment_details: assessment_id, caf_version, government_caf_profile,
                            review_type populated from metadata
      - organisation_id / system_id correctly looked up
    """

    def setUp(self):
        super().setUp()
        self.transformed, self.raw = generate_assessment_structure(
            self.definition_structure,
            self.assessment_metadata,
            self.complete_assessment_data,
            self.organisations,
            self.systems,
        )

    def test_top_level_keys_present(self):
        """Output has self_assessment, assessment_details, organisation_id, system_id."""
        for key in ("assessment_details", "organisation_id", "system_id"):
            self.assertIn(key, self.transformed)

    def test_metadata_last_updated_sourced_from_metadata(self):
        """metadata.last_updated comes from assessment_last_updated."""
        self.assertEqual(
            self.transformed["metadata"]["last_updated"],
            self.assessment_metadata["assessment_last_updated"],
        )

    def test_metadata_completed_sourced_from_metadata(self):
        """metadata.completed comes from assessment_status_changed_to_submtd."""
        self.assertEqual(
            self.transformed["metadata"]["completed"],
            self.assessment_metadata["assessment_status_changed_to_submtd"],
        )

    def test_outcomes_present(self):
        """outcomes contains entries for all input outcomes."""
        outcome_ids = {o["outcome_id"] for o in self.transformed["outcomes"]}
        self.assertIn("A1.a", outcome_ids)
        self.assertIn("A1.b", outcome_ids)
        self.assertIn("B1.a", outcome_ids)

    def test_assessment_details_assessment_id(self):
        """assessment_details.assessment_id matches the hashed_assessment_id."""
        self.assertEqual(
            self.transformed["assessment_id"],
            _ASSESSMENT_ID,
        )

    def test_assessment_details_caf_version(self):
        """assessment_details.caf_version matches assessment_version from metadata."""
        self.assertEqual(
            self.transformed["assessment_details"]["caf_version"],
            "3.1",
        )

    def test_assessment_details_government_caf_profile_capitalised(self):
        """
        assessment_details.government_caf_profile is the system_profile with only the
        first letter capitalised — 'BASELINE' in the raw data becomes 'Baseline'.
        """
        self.assertEqual(
            self.transformed["assessment_details"]["government_caf_profile"],
            "Baseline",
        )

    def test_organisation_id_and_system_id_correctly_mapped(self):
        """organisation_id and system_id are the hashed IDs from the lookup tables."""
        self.assertEqual(self.transformed["organisation_id"], _ORG_ID)
        self.assertEqual(self.transformed["system_id"], _SYS_ID)

    def test_outcome_fields_complete(self):
        """
        Each outcome in outcomes contains all required fields
        carrying data from the input: outcome_id, outcome_status, indicators,
        supplementary_questions, outcome_confirm_comment.
        """
        a1a = next(o for o in self.transformed["outcomes"] if o["outcome_id"] == "A1.a")
        for field in (
            "outcome_id",
            "outcome_status",
            "outcome_status_message",
            "outcome_confirm_comment",
            "indicators",
            "supplementary_questions",
        ):
            self.assertIn(field, a1a)

    def test_outcome_status_correct(self):
        """outcome_status in the transformed output is derived from the ACH achievement code."""
        a1a = next(o for o in self.transformed["outcomes"] if o["outcome_id"] == "A1.a")
        self.assertEqual(a1a["outcome_status"], "Achieved")

    def test_indicators_carry_values_and_comments(self):
        """
        Each indicator in outcomes[A1.a].indicators has value (bool)
        and comment sourced from the input data.
        """
        a1a = next(o for o in self.transformed["outcomes"] if o["outcome_id"] == "A1.a")
        ind_ids = {i["indicator_id"] for i in a1a["indicators"]}
        self.assertIn("A1.a.1", ind_ids)
        self.assertIn("A1.a.2", ind_ids)
        self.assertIn("A1.a.3", ind_ids)
        self.assertIn("A1.a.4", ind_ids)

        a1a1 = next(i for i in a1a["indicators"] if i["indicator_id"] == "A1.a.1")
        self.assertIsInstance(a1a1["value"], bool)
        self.assertTrue(a1a1["value"])  # answer was "Yes"
        self.assertIsInstance(a1a1["comment"], str)


# ============================================================================
# Comprehensive end-to-end: Review output structure and calculated values
# ============================================================================


class TestReviewOutputStructure(TransformTestBase):
    """
    End-to-end tests (real transformer, no mocks) verifying that
    generate_review_structure produces a correctly populated output with:
      - review_details: populated when additional_information is in metadata
      - metadata: review_completed / review_finalised sourced from metadata
      - outcomes: review_decision mapped, indicators carried through
    """

    def _run_review(self, assessment_meta=None):
        meta = assessment_meta or self.assessment_metadata
        transformed, raw = generate_assessment_structure(
            self.definition_structure,
            meta,
            self.complete_assessment_data,
            self.organisations,
            self.systems,
        )
        return generate_review_structure(
            self.definition_structure,
            meta,
            transformed,
            self.review_assessment_data,
            self.organisations,
            self.systems,
        )

    def test_top_level_keys_present(self):
        """Output has review_details, outcomes, and metadata."""
        review = self._run_review()
        for key in ("review_details", "outcomes", "metadata"):
            self.assertIn(key, review)

    def test_review_details_sub_keys_present(self):
        """review_details contains all required sub-keys even when fields are None."""
        review = self._run_review()
        for key in ("company_name", "review_method", "review_period", "quality_self_assessment"):
            self.assertIn(key, review["review_details"])

    def test_metadata_sub_keys_present(self):
        """metadata contains all required sub-keys."""
        review = self._run_review()
        for key in ("review_last_updated", "review_created", "review_completed", "review_finalised"):
            self.assertIn(key, review["metadata"])

    def test_metadata_review_last_updated_mapped_from_assessment_last_updated(self):
        """
        review_last_updated is sourced from assessment_last_updated in the old data format
        (review-specific last-updated timestamps are not available in overview/all.json).
        """
        review = self._run_review()
        self.assertEqual(
            review["metadata"]["review_last_updated"],
            self.assessment_metadata["assessment_last_updated"],
        )

    def test_metadata_review_created_mapped_from_assessment_status_changed_to_aseing(self):
        """
        review_created is sourced from assessment_status_changed_to_aseing, the closest
        proxy for when review work began in the old data format.
        """
        review = self._run_review()
        self.assertEqual(
            review["metadata"]["review_created"],
            self.assessment_metadata["assessment_status_changed_to_aseing"],
        )

    def test_review_details_populated_from_additional_information(self):
        """
        When assessment_meta includes additional_information, review_details fields
        are sourced from it correctly.
        """
        meta = _make_assessment_metadata_with_review_info()
        review = self._run_review(assessment_meta=meta)

        self.assertEqual(review["review_details"]["company_name"], "Test Assessor Ltd")
        self.assertEqual(review["review_details"]["review_method"], "Remote assessment")
        self.assertEqual(review["review_details"]["quality_self_assessment"], "Good evidence provided")
        self.assertEqual(
            review["review_details"]["review_period"],
            {"start_date": "01/01/2023", "end_date": "31/12/2023"},
        )

    def test_metadata_review_completed_sourced_from_review_completion(self):
        """metadata.review_completed comes from review_completion.review_completed_at."""
        meta = _make_assessment_metadata_with_review_info()
        review = self._run_review(assessment_meta=meta)

        self.assertEqual(review["metadata"]["review_completed"], "2023-06-15T12:00:00")

    def test_metadata_review_finalised_sourced_from_review_finalised(self):
        """metadata.review_finalised comes from review_finalised.review_finalised_at."""
        meta = _make_assessment_metadata_with_review_info()
        review = self._run_review(assessment_meta=meta)

        self.assertEqual(review["metadata"]["review_finalised"], "2023-06-20T10:00:00")

    def test_review_outcomes_contain_all_input_outcomes(self):
        """outcomes list contains an entry for each outcome present in review data."""
        review = self._run_review()
        outcome_ids = {o["outcome_id"] for o in review["outcomes"]}
        self.assertIn("A1.a", outcome_ids)
        self.assertIn("A1.b", outcome_ids)

    def test_review_decision_ach_maps_correctly(self):
        """assessor_achievement 'ACH' maps to the 'Achieved' label in review_decision."""
        review = self._run_review()
        a1a = next(o for o in review["outcomes"] if o["outcome_id"] == "A1.a")
        self.assertEqual(a1a["review_decision"], "Achieved")

    def test_review_indicators_carry_boolean_values(self):
        """
        Review indicators have boolean values derived from assessor_answer
        ('Yes' → True, 'No' → False).
        """
        review = self._run_review()
        a1a = next(o for o in review["outcomes"] if o["outcome_id"] == "A1.a")
        ind_by_id = {i["indicator_id"]: i for i in a1a["indicators"]}

        self.assertTrue(ind_by_id["A1.a.1"]["value"])  # assessor_answer = "Yes"
        self.assertFalse(ind_by_id["A1.a.3"]["value"])  # assessor_answer = "No"

    def test_review_indicators_carry_comments(self):
        """Review indicator comments are sourced from assessor_comment in input data."""
        review = self._run_review()
        a1a = next(o for o in review["outcomes"] if o["outcome_id"] == "A1.a")
        a1a1 = next(i for i in a1a["indicators"] if i["indicator_id"] == "A1.a.1")
        self.assertIn("board meeting minutes", a1a1["comment"])


if __name__ == "__main__":
    unittest.main()
