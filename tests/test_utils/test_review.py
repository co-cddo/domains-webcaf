"""
Tests for webcaf/webcaf/utils/review.py

This module contains tests for the review utility functions including:
- get_review_recommendations
- Recommendation namedtuple
- RecommendationGroup class
- review_status_to_label utility
"""
import json
import types
from pathlib import Path

from django.test import TestCase

from webcaf.webcaf.models import Assessment, Review
from webcaf.webcaf.utils.review import (
    Recommendation,
    RecommendationGroup,
    get_review_recommendations,
    review_status_to_label,
)

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "completed_assessment_base.json"
REVIEW_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "completed_review.json"


class TestReviewStatusToLabel(TestCase):
    """Tests for the review_status_to_label utility function."""

    def test_review_status_to_label_draft(self):
        """Test conversion of 'draft' status to label."""
        self.assertEqual(review_status_to_label("draft"), "Draft")

    def test_review_status_to_label_submitted(self):
        """Test conversion of 'submitted' status to label."""
        self.assertEqual(review_status_to_label("submitted"), "Submitted")

    def test_review_status_to_label_in_review(self):
        """Test conversion of 'review' status to label."""
        self.assertEqual(review_status_to_label("review"), "In review")

    def test_review_status_to_label_published(self):
        """Test conversion of 'published' status to label."""
        self.assertEqual(review_status_to_label("published"), "Published")

    def test_review_status_to_label_cancelled(self):
        """Test conversion of 'cancelled' status to label."""
        self.assertEqual(review_status_to_label("cancelled"), "Cancelled")

    def test_review_status_to_label_achieved(self):
        """Test conversion of 'achieved' status to label."""
        self.assertEqual(review_status_to_label("achieved"), "Achieved")

    def test_review_status_to_label_not_achieved(self):
        """Test conversion of 'not-achieved' status to label."""
        self.assertEqual(review_status_to_label("not-achieved"), "Not achieved")

    def test_review_status_to_label_partially_achieved(self):
        """Test conversion of 'partially-achieved' status to label."""
        self.assertEqual(review_status_to_label("partially-achieved"), "Partially achieved")

    def test_review_status_to_label_unknown(self):
        """Test that unknown status returns the original value."""
        self.assertEqual(review_status_to_label("unknown_status"), "unknown_status")

    def test_review_status_to_label_none(self):
        """Test that None returns None."""
        self.assertIsNone(review_status_to_label(None))

    def test_review_status_to_label_empty_string(self):
        """Test that empty string returns empty string."""
        self.assertEqual(review_status_to_label(""), "")


class TestGetReviewRecommendations(TestCase):
    """Tests for the get_review_recommendations function."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data with assessments and reviews."""
        from django.contrib.auth.models import User

        from webcaf.webcaf.models import Organisation, System, UserProfile

        cls.org = Organisation.objects.create(name="Test Organisation")
        cls.system = System.objects.create(name="Test System", organisation=cls.org)
        cls.system_2 = System.objects.create(name="Test System 2", organisation=cls.org)
        cls.user = User.objects.create_user(username="test@test.gov.uk", email="test@test.gov.uk")
        UserProfile.objects.create(user=cls.user, organisation=cls.org, role="cyber_advisor")

        with open(FIXTURE_PATH, "r") as f:
            base_assessment = json.load(f)

        with open(REVIEW_FIXTURE_PATH, "r") as f:
            base_review = json.load(f)

        cls.assessment = Assessment.objects.create(
            system=cls.system,
            status="submitted",
            assessment_period="25/26",
            review_type="independent",
            framework="caf32",
            caf_profile="baseline",
            assessments_data=base_assessment,
        )

        cls.review = Review.objects.create(
            assessment=cls.assessment,
            status="completed",
            review_data=base_review,
        )

    def test_get_review_recommendations_priority_mode(self):
        """Test getting priority recommendations (not meeting baseline profile)."""
        recommendations = list(get_review_recommendations(self.review, "priority"))

        # Should return RecommendationGroup objects
        for group in recommendations:
            self.assertIsInstance(group, RecommendationGroup)
            # Each group should have recommendations
            self.assertGreater(len(group.recommendations), 0)
            # Each recommendation should have outcome_title
            for rec in group.recommendations:
                self.assertIsInstance(rec, Recommendation)
                self.assertIsNotNone(rec.outcome_title)
                self.assertIsInstance(rec.outcome_title, str)

    def test_get_review_recommendations_normal_mode(self):
        """Test getting normal recommendations (meeting baseline profile)."""
        recommendations = list(get_review_recommendations(self.review, "normal"))

        for group in recommendations:
            self.assertIsInstance(group, RecommendationGroup)
            self.assertGreater(len(group.recommendations), 0)
            for rec in group.recommendations:
                self.assertIsInstance(rec, Recommendation)
                self.assertIsNotNone(rec.outcome_title)

    def test_get_review_recommendations_all_mode(self):
        """Test getting all recommendations regardless of priority."""
        recommendations = list(get_review_recommendations(self.review, "all"))

        self.assertGreater(len(recommendations), 0)
        for group in recommendations:
            self.assertIsInstance(group, RecommendationGroup)
            for rec in group.recommendations:
                self.assertIsNotNone(rec.outcome_title)

    def test_get_review_recommendations_returns_generator(self):
        """Test that get_review_recommendations returns a generator."""
        result = get_review_recommendations(self.review, "all")
        # The function uses yield, so it should return a generator object.
        self.assertIsInstance(result, types.GeneratorType)

    def test_get_review_recommendations_group_index_incrementing(self):
        """Test that group indices are properly incremented."""
        recommendations = list(get_review_recommendations(self.review, "all"))

        indices = [group.group_index for group in recommendations]
        self.assertEqual(indices, list(range(1, len(recommendations) + 1)))

    def test_get_review_recommendations_recommendation_structure(self):
        """Test that recommendations have correct structure with outcome_title."""
        recommendations = list(get_review_recommendations(self.review, "all"))

        for group in recommendations:
            for rec in group.recommendations:
                # Verify all fields are present and correct types
                self.assertIsInstance(rec.id, str)
                self.assertIsInstance(rec.title, str)
                self.assertIsInstance(rec.text, str)
                self.assertIsInstance(rec.objective, str)
                self.assertIsInstance(rec.outcome, str)
                self.assertIsInstance(rec.outcome_title, str)

                # ID should follow the pattern REC-{outcome_code}{index}
                self.assertTrue(rec.id.startswith("REC-"))

    def test_get_review_recommendations_with_peer_review(self):
        """Test recommendations work with peer_review review type."""
        # Create a peer review assessment
        peer_assessment = Assessment.objects.create(
            system=self.system_2,
            status="submitted",
            assessment_period="25/26",
            review_type="peer_review",
            framework="caf32",
            caf_profile="baseline",
            assessments_data=self.assessment.assessments_data,
        )

        peer_review = Review.objects.create(
            assessment=peer_assessment,
            status="completed",
            review_data=self.review.review_data,
        )

        recommendations = list(get_review_recommendations(peer_review, "all"))

        # Should still work the same way
        for group in recommendations:
            for rec in group.recommendations:
                self.assertIsNotNone(rec.outcome_title)

    def test_get_review_recommendations_ordering(self):
        """Test that groups are ordered by recommendation count within each outcome."""
        recommendations = list(get_review_recommendations(self.review, "all"))

        if not recommendations:
            self.skipTest("No recommendations to assert ordering against.")

        # Group sizes should be non-increasing within each outcome block.
        current_outcome = recommendations[0].recommendations[0].outcome
        current_sizes = []
        for group in recommendations:
            outcome = group.recommendations[0].outcome
            if outcome != current_outcome:
                self.assertEqual(current_sizes, sorted(current_sizes, reverse=True))
                current_outcome = outcome
                current_sizes = []
            current_sizes.append(len(group.recommendations))

        if current_sizes:
            self.assertEqual(current_sizes, sorted(current_sizes, reverse=True))

    def test_get_review_recommendations_mode_partitioning(self):
        """Test that priority/normal partition all recommendations without overlap."""
        priority = list(get_review_recommendations(self.review, "priority"))
        normal = list(get_review_recommendations(self.review, "normal"))
        all_recs = list(get_review_recommendations(self.review, "all"))

        def flatten_ids(groups):
            return {rec.id for group in groups for rec in group.recommendations}

        priority_ids = flatten_ids(priority)
        normal_ids = flatten_ids(normal)
        all_ids = flatten_ids(all_recs)

        self.assertTrue(priority_ids.isdisjoint(normal_ids))
        self.assertEqual(priority_ids | normal_ids, all_ids)


class TestGetReviewRecommendationsIntegration(TestCase):
    """Integration tests for get_review_recommendations with real data."""

    @classmethod
    def setUpTestData(cls):
        """Set up multiple assessments with different review types."""
        from django.contrib.auth.models import User

        from webcaf.webcaf.models import Organisation, System, UserProfile

        cls.org = Organisation.objects.create(name="Integration Test Org")
        cls.system = System.objects.create(name="Integration Test System", organisation=cls.org)
        cls.system_2 = System.objects.create(name="Integration Test System 2", organisation=cls.org)
        cls.user = User.objects.create_user(username="integration@test.gov.uk", email="integration@test.gov.uk")
        UserProfile.objects.create(user=cls.user, organisation=cls.org, role="cyber_advisor")

        with open(FIXTURE_PATH, "r") as f:
            base_assessment = json.load(f)

        with open(REVIEW_FIXTURE_PATH, "r") as f:
            base_review = json.load(f)

        # Create assessments with different review types
        cls.independent_assessment = Assessment.objects.create(
            system=cls.system,
            status="submitted",
            assessment_period="25/26",
            review_type="independent",
            framework="caf32",
            caf_profile="baseline",
            assessments_data=base_assessment,
        )

        cls.peer_review_assessment = Assessment.objects.create(
            system=cls.system_2,
            status="submitted",
            assessment_period="25/26",
            review_type="peer_review",
            framework="caf32",
            caf_profile="baseline",
            assessments_data=base_assessment,
        )

        cls.independent_review = Review.objects.create(
            assessment=cls.independent_assessment,
            status="completed",
            review_data=base_review,
        )

        cls.peer_review = Review.objects.create(
            assessment=cls.peer_review_assessment,
            status="completed",
            review_data=base_review,
        )

    def test_recommendations_include_outcome_title_for_both_review_types(self):
        """Test that both independent and peer reviews include outcome_title."""
        independent_recs = list(get_review_recommendations(self.independent_review, "all"))
        peer_recs = list(get_review_recommendations(self.peer_review, "all"))

        # Both should have outcome_title populated
        for group in independent_recs:
            for rec in group.recommendations:
                self.assertIsNotNone(rec.outcome_title)
                self.assertTrue(len(rec.outcome_title) > 0)

        for group in peer_recs:
            for rec in group.recommendations:
                self.assertIsNotNone(rec.outcome_title)
                self.assertTrue(len(rec.outcome_title) > 0)

    def test_recommendation_count_consistent_across_review_types(self):
        """Test that recommendation counts are consistent regardless of review type."""
        independent_recs = list(get_review_recommendations(self.independent_review, "all"))
        peer_recs = list(get_review_recommendations(self.peer_review, "all"))

        # Count total recommendations
        independent_count = sum(len(g.recommendations) for g in independent_recs)
        peer_count = sum(len(g.recommendations) for g in peer_recs)

        # Should be the same since they use the same review data
        self.assertEqual(independent_count, peer_count)
