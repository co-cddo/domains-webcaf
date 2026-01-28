import json
from pathlib import Path

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import Assessment, Review

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "completed_assessment_base.json"
REVIEW_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "completed_review.json"


class TestCSVExport(BaseViewTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        all_systems = []

        for org in cls.org_map.values():
            for system in org["systems"].values():
                all_systems.append(system)

        with open(FIXTURE_PATH, "r") as f:
            base_assessment = json.load(f)

        with open(REVIEW_FIXTURE_PATH, "r") as f:
            base_review = json.load(f)

        # Make one assessment incomplete
        assessments_data = [base_assessment.copy() for _ in range(len(all_systems))]
        # We might want to edit reviews so create in the same way
        reviews_data = [base_review.copy() for _ in range(len(all_systems))]
        del assessments_data[-1]["D2.b"]

        cls.assessments = []
        cls.reviews = []
        for org in cls.org_map.values():
            for system in org["systems"].values():
                assessment = Assessment.objects.create(
                    system=system,
                    status="submitted",
                    assessment_period="25/26",
                    review_type="peer_review",
                    framework="caf32",
                    caf_profile="baseline",
                    assessments_data=assessments_data.pop(0),
                )
                cls.assessments.append(assessment)

                review = Review.objects.create(
                    assessment=assessment,
                    status="completed",
                    review_data=reviews_data.pop(0),
                )
                cls.reviews.append(review)

    def test_we_have_some_assessments(self):
        assert len(self.assessments) > 0
