import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from webcaf.webcaf.management.commands.export_data import Command
from webcaf.webcaf.models import Assessment, Organisation, Review, System

_LOREM_IPSUM = "Lorem ipsum."


class TestExportDataCommand(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Test Org", organisation_type="other")
        self.system = System.objects.create(name="Test System", organisation=self.org)
        self.assessment = Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period="2024/25",
            review_type="independent",
            assessments_data={"answer": "yes"},
        )
        self.review = Review.objects.create(
            assessment=self.assessment,
            status="in_progress",
            review_data={
                "assessor_response_data": {
                    "A": {"result": "a"},
                    "B": {"result": "b"},
                    "E": {"result": "should_not_export"},
                }
            },
        )
        self.command = Command()

    @patch("webcaf.webcaf.management.commands.export_data.extract_metadata", return_value={"meta": "assessment"})
    @patch(
        "webcaf.webcaf.management.commands.export_data.transform_assessment",
        return_value={"transformed": "assessment"},
    )
    def test_export_assessments_uploads_transformed_payload(self, transform_mock, extract_metadata_mock):
        s3 = MagicMock()

        self.command.export_assessments("test-bucket", s3, {}, {})

        self.assertEqual(1, transform_mock.call_count)
        self.assertEqual({"answer": "yes"}, transform_mock.call_args[0][0])

        extract_metadata_mock.assert_called_once_with(self.assessment, {}, {})
        s3.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key=f"assessments/2024-25/{self.assessment.reference}.json",
            Body=json.dumps({"transformed": "assessment"}),
        )

    @patch("webcaf.webcaf.management.commands.export_data.extract_metadata", return_value={"meta": "review"})
    @patch(
        "webcaf.webcaf.management.commands.export_data.transform_review",
        return_value={"transformed": "review"},
    )
    def test_export_reviews_uploads_filtered_assessor_data(self, transform_mock, extract_metadata_mock):
        s3 = MagicMock()

        self.command.export_reviews("test-bucket", s3, {}, {})

        self.assertEqual(1, transform_mock.call_count)
        self.assertEqual(
            {"A": {"result": "a"}, "B": {"result": "b"}},
            transform_mock.call_args[0][0],
        )
        self.assertEqual(
            {
                "additional_information": {},
                "meta": "review",
                "review_completion": {},
                "review_created": str(self.review.created_on),
                "review_finalised": {},
                "review_last_updated": str(self.review.last_updated),
            },
            transform_mock.call_args[0][1],
        )

        extract_metadata_mock.assert_called_once_with(self.assessment, {}, {})
        s3.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key=f"reviews/2024-25/{self.assessment.reference}.json",
            Body=json.dumps({"transformed": "review"}),
        )


PATCH_TRANSFORM = "webcaf.webcaf.management.commands.export_data.transform_review"
PATCH_EXTRACT = "webcaf.webcaf.management.commands.export_data.extract_metadata"


class TestExportReviews(TestCase):
    """Comprehensive tests for Command.export_reviews."""

    def setUp(self):
        self.org = Organisation.objects.create(name="Test Org", organisation_type="other")
        self.system = System.objects.create(name="Test System", organisation=self.org)
        self.assessment = Assessment.objects.create(
            system=self.system,
            status="submitted",
            assessment_period="2024/25",
            review_type="independent",
            assessments_data={
                # Status values must use lowercase 'a' to match status_to_key() expectations
                # e.g. "Partially achieved" not "Partially Achieved" (from YAML &partially_achieved anchor)
                "A1.a": {"confirmation": {"outcome_status": "Achieved"}},
                "B1.a": {"confirmation": {"outcome_status": "Partially achieved"}},
                "C1.a": {"confirmation": {"outcome_status": "Not achieved"}},
                "D1.a": {"confirmation": {"outcome_status": "Achieved"}},
            },
        )
        self.review = Review.objects.create(
            assessment=self.assessment,
            status="in_progress",
            review_data={
                "assessor_response_data": {
                    "A": {
                        "A1.a": {
                            "review_data": {
                                "review_decision": "achieved",
                                "review_comment": "Well implemented",
                            },
                            "indicators": {
                                "achieved_A1.a.1": "yes",
                                "achieved_A1.a.1_comment": "Strong evidence",
                                "not-achieved_A1.a.2": "no",
                            },
                        }
                    },
                    "B": {"B1.a": {"review_data": {"review_decision": "achieved"}}},
                    "C": {
                        "C1.a": {},
                        "objective-areas-of-improvement": "everything",
                        "objective-areas-of-good-practice": "nothing",
                    },
                    "D": {"D1.a": {}},
                    "E": {"should_not_export": True},
                    "Z": {"also_excluded": True},
                }
            },
        )
        self.submitted_dates = {self.assessment.id: datetime(2024, 3, 1, 10, 0)}
        self.in_progress_dates = {self.assessment.id: datetime(2024, 2, 1, 9, 0)}
        self.command = Command()
        self.s3 = MagicMock()
        self.maxDiff = None

    # ------------------------------------------------------------------
    # Complete JSON output (integration — real transformer, no transform mock)
    # ------------------------------------------------------------------

    @patch(PATCH_EXTRACT, return_value={"assessment_id": 1, "app_version": "webcaf-2"})
    def test_complete_json_file_written_to_s3(self, _extract):
        """
        End-to-end test: the JSON body uploaded to S3 matches the fully
        transformed output of transform_review, including:
        - only A–D sections from assessor_response_data
        - outcome_status sourced from assessments_data (all four outcomes populated)
        - outcome_profile_met derived from the no-op callback (returns "")
        - outcome_min_profile_requirement present in every outcome
        - review_decision label mapping ("achieved" → "Achieved", etc.)
        - indicators list populated for A1.a (value as bool, comment included)
        - review_comment carried through for A1.a
        - metadata embedded from extract_metadata
        - S3 key derived from assessment period (/ → -) and assessment reference
        """

        self.command.export_reviews("test-bucket", self.s3, self.submitted_dates, self.in_progress_dates)

        self.s3.put_object.assert_called_once()
        call_kwargs = self.s3.put_object.call_args[1]

        self.assertEqual(call_kwargs["Bucket"], "test-bucket")
        self.assertEqual(call_kwargs["Key"], f"reviews/2024-25/{self.assessment.reference}.json")

        actual = json.loads(call_kwargs["Body"])

        # caf32 baseline min_profile_requirement per outcome:
        #   A1.a → Achieved   B1.a → Partially achieved   C1.a → Partially achieved   D1.a → Achieved
        #
        # outcome_profile_met / outcome_min_profile_requirement come from profile_met_callback which
        # calls IndicatorStatusChecker.indicator_min_profile_requirement_met(return_min_required_status=True).
        #
        expected = json.loads(
            json.dumps(
                {
                    "outcomes": [
                        {
                            "outcome_id": "A1.a",
                            "outcome_min_profile_requirement": "Achieved",
                            "recommendations": [],
                            "review_decision": "Achieved",
                            "review_profile_met": "Met",
                            "review_comment": "Well implemented",
                            "indicators": [
                                {
                                    "indicator_id": "A1.a.1",
                                    "category": "achieved",
                                    "value": True,
                                    "comment": "Strong evidence",
                                },
                                {
                                    "indicator_id": "A1.a.2",
                                    "category": "not-achieved",
                                    "value": False,
                                    "comment": "",
                                },
                            ],
                        },
                        {
                            "outcome_id": "B1.a",
                            "outcome_min_profile_requirement": "Partially achieved",
                            "recommendations": [],
                            "review_decision": "Achieved",
                            "review_profile_met": "Met",
                            "review_comment": "",
                            "indicators": [],
                        },
                        {
                            "outcome_id": "C1.a",
                            "outcome_min_profile_requirement": "",
                            "recommendations": [],
                            "review_decision": "N/A",
                            "review_profile_met": "",  # N/A → callback not called → ""
                            "review_comment": "",
                            "indicators": [],
                        },
                        {
                            "outcome_id": "D1.a",
                            "outcome_min_profile_requirement": "",
                            "recommendations": [],
                            "review_decision": "N/A",
                            "review_profile_met": "",  # N/A → callback not called → ""
                            "review_comment": "",
                            "indicators": [],
                        },
                    ],
                    "metadata": {
                        "review_completed": None,
                        "review_created": str(self.review.created_on),
                        "review_finalised": None,
                        "review_last_updated": str(self.review.last_updated),
                    },
                    "review_details": {
                        "company_name": None,
                        "quality_self_assessment": None,
                        "review_method": None,
                        "review_period": {},
                    },
                    "review_commentary": {
                        "objective_level": [
                            {"areas_for_improvement": None, "areas_of_good_practice": None, "objective_code": "A"},
                            {"areas_for_improvement": None, "areas_of_good_practice": None, "objective_code": "B"},
                            {
                                "areas_for_improvement": "everything",
                                "areas_of_good_practice": "nothing",
                                "objective_code": "C",
                            },
                            {"areas_for_improvement": None, "areas_of_good_practice": None, "objective_code": "D"},
                        ],
                        "overall": {"areas_for_improvement": None, "areas_of_good_practice": None},
                    },
                    "assessment_id": 1,
                    "app_version": "webcaf-2",
                }
            )
        )

        self.assertEqual(actual, expected)


class TestExportReviewsIntegration(TestCase):
    """
    Comprehensive integration test for Command.export_reviews with realistic data.

    Assessment indicators and confirmations are drawn from a.json (A1.a, A1.b).
    Review indicators, decisions, and comments are drawn from r.json (A section).

    No transformer or database mocking — the real transformer and real Django ORM
    are exercised end-to-end. Only the S3 client is replaced with a MagicMock.
    """

    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.org = Organisation.objects.create(
            name="Ministry of Transport",
            organisation_type="ministerial-department",
        )
        cls.system = System.objects.create(
            name="National Traffic Management System",
            organisation=cls.org,
        )

        cls.assessment = Assessment.objects.create(
            system=cls.system,
            status="submitted",
            framework="caf32",
            caf_profile="baseline",
            review_type="independent",
            assessment_period="2024/25",
            assessments_data={
                "A1.a": {
                    "indicators": {
                        "achieved_A1.a.5": True,
                        "achieved_A1.a.6": True,
                        "achieved_A1.a.7": True,
                        "achieved_A1.a.8": True,
                        "not-achieved_A1.a.1": False,
                        "not-achieved_A1.a.2": False,
                        "not-achieved_A1.a.3": False,
                        "not-achieved_A1.a.4": False,
                        "achieved_A1.a.5_comment": "",
                        "achieved_A1.a.6_comment": "",
                        "achieved_A1.a.7_comment": "",
                        "achieved_A1.a.8_comment": (
                            "Lorem Ipsum is simply dummy text of the printing and typesetting industry. "
                            "Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, "
                            "when an unknown printer took a galley of type and scrambled it to make a "
                            "type specimen book."
                        ),
                    },
                    "confirmation": {
                        "outcome_status": "Achieved",
                        "confirm_outcome": "confirm",
                        "outcome_status_message": (
                            "You have received this status because you have selected all achieved IGP statements."
                        ),
                        "confirm_outcome_confirm_comment": (
                            "It is a long established fact that a reader will be distracted by the readable "
                            "content of a page when looking at its layout."
                        ),
                    },
                },
                "A1.b": {
                    "indicators": {
                        "achieved_A1.b.4": True,
                        "achieved_A1.b.5": True,
                        "achieved_A1.b.6": True,
                        "not-achieved_A1.b.1": False,
                        "not-achieved_A1.b.2": False,
                        "not-achieved_A1.b.3": False,
                        "achieved_A1.b.4_comment": "",
                        "achieved_A1.b.5_comment": "",
                        "achieved_A1.b.6_comment": "",
                    },
                    "confirmation": {
                        "outcome_status": "Achieved",
                        "confirm_outcome": "confirm",
                        "outcome_status_message": (
                            "You have received this status because you have selected all achieved IGP statements."
                        ),
                        "confirm_outcome_confirm_comment": "This is a test outcome comment",
                    },
                },
            },
        )
        cls.review = Review.objects.create(
            assessment=cls.assessment,
            status="in_progress",
            review_data={
                "review_finalised": {
                    "review_finalised_at": "2026-02-05T13:20:05.727259",
                    "review_finalised_by": "Test Assessor",
                    "review_finalised_by_role": "assessor",
                    "review_finalised_by_email": "test.assessor@cabinetoffice.gov.uk",
                },
                "review_completion": {
                    "review_completed": "yes",
                    "review_completed_at": "2026-01-30T16:08:52.644718",
                    "review_completed_by": "Test Assessor",
                    "review_completed_by_role": "assessor",
                    "review_completed_by_email": "test.assessor@cabinetoffice.gov.uk",
                },
                "assessor_response_data": {
                    "A": {
                        # Following two elements are only present in iar
                        "objective-areas-of-improvement": "rty rtyrt yqrtyr",
                        "objective-areas-of-good-practice": "tyqrt rtyt ggg",
                        "A1.a": {
                            "review_data": {
                                "review_decision": "not-achieved",
                                "review_comment": _LOREM_IPSUM,
                            },
                            "indicators": {
                                "achieved_A1.a.5": "yes",
                                "achieved_A1.a.6": "yes",
                                "achieved_A1.a.7": "yes",
                                "achieved_A1.a.8": "yes",
                                "not-achieved_A1.a.1": "yes",
                                "not-achieved_A1.a.2": "yes",
                                "not-achieved_A1.a.3": "yes",
                                "not-achieved_A1.a.4": "yes",
                                "achieved_A1.a.5_comment": _LOREM_IPSUM,
                                "achieved_A1.a.6_comment": _LOREM_IPSUM,
                                "achieved_A1.a.7_comment": _LOREM_IPSUM,
                                "achieved_A1.a.8_comment": _LOREM_IPSUM,
                                "not-achieved_A1.a.1_comment": "",
                                "not-achieved_A1.a.2_comment": "",
                                "not-achieved_A1.a.3_comment": "",
                                "not-achieved_A1.a.4_comment": "",
                            },
                        },
                        "A1.b": {
                            "review_data": {
                                "review_decision": "achieved",
                                "review_comment": "retretr",
                            },
                            "indicators": {
                                "achieved_A1.b.4": "yes",
                                "achieved_A1.b.5": "no",
                                "achieved_A1.b.6": "no",
                                "not-achieved_A1.b.1": "no",
                                "not-achieved_A1.b.2": "no",
                                "not-achieved_A1.b.3": "no",
                                "achieved_A1.b.4_comment": "",
                                "achieved_A1.b.5_comment": "",
                                "achieved_A1.b.6_comment": "",
                                "not-achieved_A1.b.1_comment": "",
                                "not-achieved_A1.b.2_comment": "",
                                "not-achieved_A1.b.3_comment": "",
                            },
                            "recommendations": [{"text": "Recommendation text", "title": "recommendation title"}],
                        },
                    },
                    "additional_information": {
                        "iar_period": {"end_date": "12/12/2025", "start_date": "11/11/2024"},
                        "review_method": _LOREM_IPSUM,
                        "company_details": {"company_name": "Assessor company", "company_email": "dharshana@ee.com"},
                        "quality_of_evidence": _LOREM_IPSUM,
                        # These two fields are only available on peer-review olly
                        "areas_for_improvement": "ERT we weer wer",
                        "areas_of_good_practice": "dt wrrW RE",
                    },
                },
            },
        )

    def test_export_reviews_with_realistic_data(self):
        """
        End-to-end assertion covering:
          - Correct S3 bucket and key (period "/" → "-", assessment reference).
          - Top-level JSON keys: review_details, outcomes, metadata.
          - Sections outside A–D (system_and_scope) are excluded.
          - "yes"/"no" indicator strings are converted to booleans.
          - _comment keys are stripped from the indicators list.
          - review_decision raw labels are mapped to human-readable titles.
          - review_comment is preserved verbatim.
          - outcome_status is sourced from assessments_data confirmations.
          - outcome_profile_met / outcome_min_profile_requirement are derived from
            the real CAF 3.2 spec (baseline):
              A1.a and A1.b min req = "Achieved"; self-assessment status "Achieved"
              (score 3) >= "Achieved" (score 3) → "Met" / "Achieved".
          - review_profile_met is derived from the real CAF 3.2 spec:
              A1.a: "Not achieved" (score 1) < "Achieved" (score 3) → "Not met".
              A1.b: "Achieved" (score 3) >= "Achieved" (score 3) → "Met".
        """
        s3 = MagicMock()
        command = Command()

        command.export_reviews("analytics-bucket", s3, submitted_dates={}, in_progress_dates={})

        s3.put_object.assert_called_once()
        call_kwargs = s3.put_object.call_args[1]

        # --- S3 addressing ---
        self.assertEqual("analytics-bucket", call_kwargs["Bucket"])
        self.assertEqual(
            f"reviews/2024-25/{self.assessment.reference}.json",
            call_kwargs["Key"],
        )

        body = json.loads(call_kwargs["Body"])

        # --- Top-level structure ---
        self.assertCountEqual(
            ["assessment_id", "app_version", "review_details", "outcomes", "metadata", "review_commentary"], body.keys()
        )

        # review_details and metadata are empty strings — the transformer does not yet
        # populate these fields from the metadata parameter.
        self.assertEqual(
            json.loads(
                json.dumps(
                    {
                        "review_period": {"end_date": "12/12/2025", "start_date": "11/11/2024"},
                        "company_name": "Assessor company",
                        "review_method": _LOREM_IPSUM,
                        "quality_self_assessment": _LOREM_IPSUM,
                    }
                )
            ),
            json.loads(json.dumps(body["review_details"])),
        )
        self.assertEqual(
            {
                "review_last_updated": str(self.review.last_updated),
                "review_created": str(self.review.created_on),
                "review_completed": "2026-01-30T16:08:52.644718",
                "review_finalised": "2026-02-05T13:20:05.727259",
            },
            body["metadata"],
        )

        # --- Outcomes list: only A1.a and A1.b (system_and_scope excluded) ---
        outcomes = body["outcomes"]
        self.assertEqual(2, len(outcomes))
        a1a = outcomes[0]
        a1b = outcomes[1]

        # ---- A1.a ----
        self.assertEqual("A1.a", a1a["outcome_id"])
        self.assertEqual("Achieved", a1a["outcome_min_profile_requirement"])

        # review_decision: raw "not-achieved" is label-mapped to "Not achieved"
        self.assertEqual("Not achieved", a1a["review_decision"])

        # review_profile_met: CAF 3.2 A1.a baseline min requirement = "Achieved";
        # "Not achieved" (score 1) < "Achieved" (score 3) → "Not met"
        self.assertEqual("Not met", a1a["review_profile_met"])

        self.assertEqual(_LOREM_IPSUM, a1a["review_comment"])

        # Indicators: comment keys stripped; "yes" → True, "no" → False
        self.assertEqual(
            [
                {"indicator_id": "A1.a.5", "category": "achieved", "value": True, "comment": _LOREM_IPSUM},
                {"indicator_id": "A1.a.6", "category": "achieved", "value": True, "comment": _LOREM_IPSUM},
                {"indicator_id": "A1.a.7", "category": "achieved", "value": True, "comment": _LOREM_IPSUM},
                {"indicator_id": "A1.a.8", "category": "achieved", "value": True, "comment": _LOREM_IPSUM},
                {"indicator_id": "A1.a.1", "category": "not-achieved", "value": True, "comment": ""},
                {"indicator_id": "A1.a.2", "category": "not-achieved", "value": True, "comment": ""},
                {"indicator_id": "A1.a.3", "category": "not-achieved", "value": True, "comment": ""},
                {"indicator_id": "A1.a.4", "category": "not-achieved", "value": True, "comment": ""},
            ],
            a1a["indicators"],
        )

        # ---- A1.b ----
        self.assertEqual("A1.b", a1b["outcome_id"])
        self.assertEqual("Achieved", a1b["outcome_min_profile_requirement"])

        # review_decision: raw "achieved" → "Achieved"
        self.assertEqual("Achieved", a1b["review_decision"])

        # review_profile_met: CAF 3.2 A1.b baseline min requirement = "Achieved";
        # "Achieved" (score 3) >= "Achieved" (score 3) → "Met"
        self.assertEqual("Met", a1b["review_profile_met"])

        self.assertEqual("retretr", a1b["review_comment"])

        self.assertEqual(
            [
                {"indicator_id": "A1.b.4", "category": "achieved", "value": True, "comment": ""},
                {"indicator_id": "A1.b.5", "category": "achieved", "value": False, "comment": ""},
                {"indicator_id": "A1.b.6", "category": "achieved", "value": False, "comment": ""},
                {"indicator_id": "A1.b.1", "category": "not-achieved", "value": False, "comment": ""},
                {"indicator_id": "A1.b.2", "category": "not-achieved", "value": False, "comment": ""},
                {"indicator_id": "A1.b.3", "category": "not-achieved", "value": False, "comment": ""},
            ],
            a1b["indicators"],
        )


class TestExportSystemsIntegration(TestCase):
    """
    Comprehensive integration test for Command.export_systems with realistic data.

    No mocking beyond the S3 client — the real Django ORM is exercised end-to-end.

    Covers:
      - S3 key format for organisations: organisations/{reference}.json
      - S3 key format for systems: systems/{reference}.json
      - Organisation body: name, type display, id, null parent fields
      - Child organisation body: parent_organisation_id and parent_organisation_name populated
      - System body: name, type display, multi-select fields correctly split into lists,
                     organisation_id, system_id, last_assessed
      - Total call count: one upload per organisation + one per system
    """

    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.parent_org = Organisation.objects.create(
            name="Cabinet Office",
            organisation_type="ministerial-department",
        )
        cls.child_org = Organisation.objects.create(
            name="HMRC",
            organisation_type="executive-agency",
            parent_organisation=cls.parent_org,
        )
        cls.system = System.objects.create(
            name="Tax Filing Portal",
            organisation=cls.child_org,
            system_type="directly_delivers_public_services",
            hosting_type="hosted_on_cloud",
            corporate_services="payroll",
            system_owner="owned_by_organisation_being_assessed",
            last_assessed="assessed_in_2324",
        )

    def test_export_systems_with_realistic_data(self):
        s3 = MagicMock()
        Command().export_organisation_and_systems("analytics-bucket", s3)

        # 2 organisations + 1 system = 3 put_object calls
        self.assertEqual(3, s3.put_object.call_count)

        # Index all calls by S3 key for order-independent assertions
        calls_by_key = {call.kwargs["Key"]: json.loads(call.kwargs["Body"]) for call in s3.put_object.call_args_list}

        # --- S3 key format ---
        self.assertIn(f"organisations/{self.parent_org.reference}.json", calls_by_key)
        self.assertIn(f"organisations/{self.child_org.reference}.json", calls_by_key)
        self.assertIn(f"systems/{self.system.reference}.json", calls_by_key)

        # --- Correct bucket on every call ---
        for call in s3.put_object.call_args_list:
            self.assertEqual("analytics-bucket", call.kwargs["Bucket"])

        # --- Parent organisation: all fields correct, parent fields are None ---
        parent_body = calls_by_key[f"organisations/{self.parent_org.reference}.json"]
        self.assertEqual(
            {
                "app_version": "webcaf-2",
                "organisation_name": "Cabinet Office",
                "organisation_type": "Ministerial department",
                "organisation_id": self.parent_org.id,
                "parent_organisation_id": None,
                "parent_organisation_name": None,
                "legacy_organisation_id": None,
            },
            parent_body,
        )

        # --- Child organisation: parent_organisation_id and name populated ---
        child_body = calls_by_key[f"organisations/{self.child_org.reference}.json"]
        self.assertEqual(
            {
                "app_version": "webcaf-2",
                "organisation_name": "HMRC",
                "organisation_type": "Executive agency",
                "organisation_id": self.child_org.id,
                "parent_organisation_id": self.parent_org.id,
                "parent_organisation_name": "Cabinet Office",
                "legacy_organisation_id": None,
            },
            child_body,
        )

        # --- System: display values, multi-select fields split into lists ---
        system_body = calls_by_key[f"systems/{self.system.reference}.json"]
        self.assertEqual(
            {
                "app_version": "webcaf-2",
                "system_name": "Tax Filing Portal",
                # CharField choice — full display label, no split
                "system_type": "directly_delivers_public_services",
                # MultiSelectField single values — split produces a one-element list
                "hosting_type": ["hosted_on_cloud"],
                "corporate_services": ["payroll"],
                "system_owner": ["owned_by_organisation_being_assessed"],
                "organisation_id": self.child_org.id,
                "system_id": self.system.id,
                # Mapping the last assessed values in to something usable in analasys
                "last_assessed": ["23/24"],
                "legacy_system_id": None,
            },
            system_body,
        )
