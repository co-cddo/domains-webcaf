from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import Assessment, Review


class ReviewVersioningTests(BaseViewTest):
    """
    Tests for Review versioning functionality including:
    - all_versions property
    - current_version property
    - current_version_number property
    - get_version() method
    """

    @classmethod
    def setUpTestData(cls):
        BaseViewTest.setUpTestData()

        cls.assessment = Assessment.objects.create(
            system=cls.test_system,
            assessment_period="2024/25",
            framework="caf32",
            caf_profile="baseline",
            review_type="independent",
        )

    def test_all_versions_empty_for_never_completed_review(self):
        """Test that all_versions returns empty list for review never completed."""
        review = Review.objects.create(assessment=self.assessment, status="in_progress", review_data={"test": "data"})

        self.assertEqual(review.all_versions, [])

    def test_all_versions_includes_completed_version(self):
        """Test that all_versions includes a completed version."""
        review = Review.objects.create(assessment=self.assessment, status="in_progress", review_data={"test": "data"})

        # Complete the review
        review.status = "completed"
        review.save()

        versions = review.all_versions
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0].status, "completed")

    def test_all_versions_filters_non_completed_statuses(self):
        """Test that all_versions only includes completed versions."""
        review = Review.objects.create(assessment=self.assessment, status="to_do", review_data={"test": "data"})

        # Go through various statuses
        review.status = "in_progress"
        review.save()

        review.status = "clarify"
        review.save()

        review.status = "in_progress"
        review.save()

        # Only completed versions should be in all_versions
        self.assertEqual(len(review.all_versions), 0)

        # Now complete it
        review.status = "completed"
        review.save()
        self.assertEqual(len(review.all_versions), 1)

    def test_all_versions_includes_unique_versions_only(self):
        """Test that all_versions only includes versions with different review_data."""
        review = Review.objects.create(
            assessment=self.assessment,
            status="completed",
            review_data={
                "assessor_response_data": {"data": "version 1", "system_and_scope": {}},
                "review_completion": {"review_completed": "yes"},
            },
        )

        # Reopen and complete again with same data (should not add new version)
        review.reopen()
        review.save()
        self.assertEqual(len(review.all_versions), 1)

        review.status = "completed"
        review.save()

        # Should still be only 1 version
        self.assertEqual(len(review.all_versions), 1)

        # Reopen, modify data, and complete (should add a new version)
        review.reopen()
        review.save()

        review.review_data = {
            "assessor_response_data": {"data": "version 2"},
            "review_completion": {"review_completed": "yes"},
        }
        review.status = "completed"
        review.save()

        # Should now be 2 versions
        self.assertEqual(len(review.all_versions), 2)

    def test_all_versions_ordered_reverse_chronologically(self):
        """Test that all_versions are ordered from newest to oldest."""
        review = Review.objects.create(
            assessment=self.assessment,
            status="completed",
            review_data={"assessor_response_data": {"data": 1}, "review_completion": {"review_completed": "yes"}},
        )

        # Create version 2
        review.reopen()
        review.save()

        review.review_data = {"assessor_response_data": {"data": 2}, "review_completion": {"review_completed": "yes"}}
        review.status = "completed"
        review.save()

        # Create version 3
        review.reopen()
        review.save()
        review.review_data = {"assessor_response_data": {"data": 3}, "review_completion": {"review_completed": "yes"}}
        review.status = "completed"
        review.save()

        versions = review.all_versions
        self.assertEqual(len(versions), 3)

        # Most recent should be first
        self.assertEqual(versions[0].review_data["assessor_response_data"]["data"], 3)
        self.assertEqual(versions[1].review_data["assessor_response_data"]["data"], 2)
        self.assertEqual(versions[2].review_data["assessor_response_data"]["data"], 1)

    def test_current_version_returns_none_for_no_versions(self):
        """Test that current_version returns None when no versions exist."""
        review = Review.objects.create(assessment=self.assessment, status="in_progress", review_data={"test": "data"})

        self.assertIsNone(review.current_version)

    def test_current_version_returns_latest_version(self):
        """Test that current_version returns the most recent completed version."""
        review = Review.objects.create(
            assessment=self.assessment, status="completed", review_data={"assessor_response_data": {"data": 1}}
        )

        # Create version 2
        review.reopen()
        review.save()
        review.review_data = {"assessor_response_data": {"data": 2}}
        review.status = "completed"
        review.save()

        current = review.current_version
        self.assertIsNotNone(current)
        self.assertEqual(current.review_data["assessor_response_data"]["data"], 2)

    def test_current_version_number_returns_none_for_no_versions(self):
        """Test that current_version_number returns None when no versions exist."""
        review = Review.objects.create(
            assessment=self.assessment, status="in_progress", review_data={"assessor_response_data": {"data": 1}}
        )

        self.assertIsNone(review.current_version_number)

    def test_current_version_number_returns_correct_count(self):
        """Test that current_version_number returns correct count of versions."""
        review = Review.objects.create(
            assessment=self.assessment, status="completed", review_data={"assessor_response_data": {"data": 1}}
        )

        self.assertEqual(review.current_version_number, 1)

        # Create version 2
        review.reopen()
        review.save()
        review.review_data = {"assessor_response_data": {"data": 2}}
        review.status = "completed"
        review.save()

        self.assertEqual(review.current_version_number, 2)

        # Create version 3
        review.reopen()
        review.save()
        review.review_data = {"assessor_response_data": {"data": 3}}
        review.status = "completed"
        review.save()

        self.assertEqual(review.current_version_number, 3)

    def test_get_version_returns_none_for_no_versions(self):
        """Test that get_version returns None when no versions exist."""
        review = Review.objects.create(assessment=self.assessment, status="in_progress", review_data={"test": "data"})

        self.assertIsNone(review.get_version(1))

    def test_get_version_returns_correct_version_by_number(self):
        """Test that get_version returns correct version using 1-based indexing."""
        review = Review.objects.create(
            assessment=self.assessment, status="completed", review_data={"assessor_response_data": {"data": 1}}
        )

        # Create version 2
        review.reopen()
        review.save()

        review.review_data = {"assessor_response_data": {"data": 2}}
        review.status = "completed"
        review.save()

        # Create version 3
        review.reopen()
        review.save()

        review.review_data = {"assessor_response_data": {"data": 3}}
        review.status = "completed"
        review.save()

        version_1 = review.get_version(1)  # Most recent
        version_2 = review.get_version(2)  # Middle
        version_3 = review.get_version(3)  # Oldest

        self.assertEqual(version_3.review_data["assessor_response_data"]["data"], 3)
        self.assertEqual(version_2.review_data["assessor_response_data"]["data"], 2)
        self.assertEqual(version_1.review_data["assessor_response_data"]["data"], 1)

    def test_get_version_return_non_for_invalid_version_number(self):
        """Test that get_version returns None for invalid version number."""
        review = Review.objects.create(
            assessment=self.assessment, status="completed", review_data={"assessor_response_data": {"data": 1}}
        )

        self.assertIsNone(review.get_version(4))

    def test_get_version_with_zero(self):
        """Test that get_version with 0 return None as 0 is invalid."""
        review = Review.objects.create(
            assessment=self.assessment, status="completed", review_data={"assessor_response_data": {"data": 1}}
        )

        self.assertIsNone(review.get_version(0))

    def test_get_version_with_negative_number(self):
        """Test that get_version returns None for negative version number."""
        review = Review.objects.create(
            assessment=self.assessment, status="completed", review_data={"assessor_response_data": {"data": 1}}
        )

        # Create version 2
        review.reopen()
        review.save()

        review.review_data = {"assessor_response_data": {"data": 2}}
        review.status = "completed"
        review.save()

        self.assertIsNone(review.get_version(-1))

    def test_multiple_completion_reopening_cycles(self):
        """Test versioning through multiple complete/reopen cycles."""
        review = Review.objects.create(
            assessment=self.assessment, status="in_progress", review_data={"assessor_response_data": {"data": 0}}
        )

        # Complete version 1
        review.review_data = {"assessor_response_data": {"data": 1}}
        review.status = "completed"
        review.save()
        self.assertEqual(review.current_version_number, 1)

        # Reopen, modify, complete version 2
        review.reopen()
        review.save()
        review.review_data = {"assessor_response_data": {"data": 2}}
        review.status = "completed"
        review.save()
        self.assertEqual(review.current_version_number, 2)

        # Reopen, modify, complete version 3
        review.reopen()
        review.save()
        review.review_data = {"assessor_response_data": {"data": 3}}
        review.status = "completed"
        review.save()
        self.assertEqual(review.current_version_number, 3)

        # Verify all versions are tracked
        versions = review.all_versions
        self.assertEqual(len(versions), 3)
        self.assertEqual(versions[0].review_data["assessor_response_data"]["data"], 3)
        self.assertEqual(versions[1].review_data["assessor_response_data"]["data"], 2)
        self.assertEqual(versions[2].review_data["assessor_response_data"]["data"], 1)

    def test_versioning_only_tracks_completed_status(self):
        """Test that only 'completed' status creates versions, not other statuses."""
        review = Review.objects.create(assessment=self.assessment, status="to_do", review_data={"test": "data"})

        # Go through all non-completed statuses
        for status in ["in_progress", "clarify", "cancelled"]:
            review.status = status
            review.review_data = {"status": status}
            review.save()

        # No versions should exist
        self.assertEqual(len(review.all_versions), 0)
        self.assertIsNone(review.current_version_number)

        # Complete it
        review.status = "completed"
        review.save()

        # Now should have 1 version
        self.assertEqual(len(review.all_versions), 1)
        self.assertEqual(review.current_version_number, 1)
