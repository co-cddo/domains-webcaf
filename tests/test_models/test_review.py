from unittest.mock import patch

from django.core.exceptions import ValidationError

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import Assessment, Review


class ReviewIsObjectiveCompleteTests(BaseViewTest):
    """
    Tests for the Review.is_objective_complete() method.

    Tests all possible branches:
    1. Missing objective-level keys (recommendations, objective-areas-of-improvement, objective-areas-of-good-practice)
    2. Missing outcome review_decision
    3. Outcome with 'achieved' status
    4. Outcome with non-achieved status but missing recommendations
    5. Outcome with non-achieved status and recommendations present
    6. Complete objective with all required data
    """

    @classmethod
    def setUpTestData(cls):
        BaseViewTest.setUpTestData()

        cls.assessment = Assessment.objects.create(
            system=cls.test_system,
            assessment_period="24/25",
            framework="caf32",
            caf_profile="baseline",
            review_type="independent",
        )

        cls.review = Review.objects.create(
            assessment=cls.assessment,
            status="in_progress",
        )

    def test_objective_incomplete_missing_areas_of_improvement_key(self):
        """Test that objective is incomplete when 'objective-areas-of-improvement' key is missing."""
        mock_caf_objective = {"code": "A", "principles": {"A1": {"outcomes": {"A1.a": {"code": "A1.a"}}}}}

        self.review.review_data = {
            "assessor_response_data": {
                "A": {
                    "recommendations": [],
                    "objective-areas-of-good-practice": "Good practice",
                    # Missing 'objective-areas-of-improvement' key
                    "A1.a": {"review_data": {"review_decision": "achieved"}},
                }
            }
        }
        self.review.save()

        with patch.object(self.review.assessment, "get_caf_objective_by_id", return_value=mock_caf_objective):
            result = self.review.is_objective_complete("A")

        self.assertFalse(result)

    def test_objective_incomplete_missing_areas_of_good_practice_key(self):
        """Test that objective is incomplete when 'objective-areas-of-good-practice' key is missing."""
        mock_caf_objective = {"code": "A", "principles": {"A1": {"outcomes": {"A1.a": {"code": "A1.a"}}}}}

        self.review.review_data = {
            "assessor_response_data": {
                "A": {
                    "recommendations": [],
                    "objective-areas-of-improvement": "Some improvement",
                    # Missing 'objective-areas-of-good-practice' key
                    "A1.a": {"review_data": {"review_decision": "achieved"}},
                }
            }
        }
        self.review.save()

        with patch.object(self.review.assessment, "get_caf_objective_by_id", return_value=mock_caf_objective):
            result = self.review.is_objective_complete("A")

        self.assertFalse(result)

    def test_objective_incomplete_missing_review_decision(self):
        """Test that objective is incomplete when outcome review_decision is missing."""
        mock_caf_objective = {"code": "A", "principles": {"A1": {"outcomes": {"A1.a": {"code": "A1.a"}}}}}

        self.review.review_data = {
            "assessor_response_data": {
                "A": {
                    "recommendations": [],
                    "objective-areas-of-improvement": "Some improvement",
                    "objective-areas-of-good-practice": "Good practice",
                    "A1.a": {
                        "review_data": {
                            # Missing 'review_decision'
                        }
                    },
                }
            }
        }
        self.review.save()

        with patch.object(self.review.assessment, "get_caf_objective_by_id", return_value=mock_caf_objective):
            result = self.review.is_objective_complete("A")

        self.assertFalse(result)

    def test_objective_incomplete_not_achieved_without_recommendations(self):
        """Test that objective is incomplete when outcome is not-achieved but lacks recommendations."""
        mock_caf_objective = {"code": "A", "principles": {"A1": {"outcomes": {"A1.a": {"code": "A1.a"}}}}}

        self.review.review_data = {
            "assessor_response_data": {
                "A": {
                    "recommendations": [],
                    "objective-areas-of-improvement": "Some improvement",
                    "objective-areas-of-good-practice": "Good practice",
                    "A1.a": {
                        "review_data": {"review_decision": "not-achieved"}
                        # Missing 'recommendations' for non-achieved outcome
                    },
                }
            }
        }
        self.review.save()

        with patch.object(self.review.assessment, "get_caf_objective_by_id", return_value=mock_caf_objective):
            result = self.review.is_objective_complete("A")

        self.assertFalse(result)

    def test_objective_incomplete_partially_achieved_without_recommendations(self):
        """Test that objective is incomplete when outcome is partially-achieved but lacks recommendations."""
        mock_caf_objective = {"code": "A", "principles": {"A1": {"outcomes": {"A1.a": {"code": "A1.a"}}}}}

        self.review.review_data = {
            "assessor_response_data": {
                "A": {
                    "recommendations": [],
                    "objective-areas-of-improvement": "Some improvement",
                    "objective-areas-of-good-practice": "Good practice",
                    "A1.a": {
                        "review_data": {"review_decision": "partially-achieved"}
                        # Missing 'recommendations' for partially-achieved outcome
                    },
                }
            }
        }
        self.review.save()

        with patch.object(self.review.assessment, "get_caf_objective_by_id", return_value=mock_caf_objective):
            result = self.review.is_objective_complete("A")

        self.assertFalse(result)

    def test_objective_complete_achieved_outcome(self):
        """Test that objective is complete when outcome is 'achieved'."""
        mock_caf_objective = {"code": "A", "principles": {"A1": {"outcomes": {"A1.a": {"code": "A1.a"}}}}}

        self.review.review_data = {
            "assessor_response_data": {
                "A": {
                    "recommendations": [],
                    "objective-areas-of-improvement": "Some improvement",
                    "objective-areas-of-good-practice": "Good practice",
                    "A1.a": {"review_data": {"review_decision": "achieved"}},
                }
            }
        }
        self.review.save()

        with patch.object(self.review.assessment, "get_caf_objective_by_id", return_value=mock_caf_objective):
            result = self.review.is_objective_complete("A")

        self.assertTrue(result)

    def test_objective_complete_not_achieved_with_recommendations(self):
        """Test that objective is complete when outcome is not-achieved and has recommendations."""
        mock_caf_objective = {"code": "A", "principles": {"A1": {"outcomes": {"A1.a": {"code": "A1.a"}}}}}

        self.review.review_data = {
            "assessor_response_data": {
                "A": {
                    "recommendations": [{"title": "Fix this", "text": "Do better"}],
                    "objective-areas-of-improvement": "Some improvement",
                    "objective-areas-of-good-practice": "Good practice",
                    "A1.a": {
                        "review_data": {"review_decision": "not-achieved"},
                        "recommendations": [{"title": "Fix outcome", "text": "Details"}],
                    },
                }
            }
        }
        self.review.save()

        with patch.object(self.review.assessment, "get_caf_objective_by_id", return_value=mock_caf_objective):
            result = self.review.is_objective_complete("A")

        self.assertTrue(result)

    def test_objective_complete_multiple_outcomes_all_achieved(self):
        """Test that objective is complete when all outcomes are achieved."""
        mock_caf_objective = {
            "code": "A",
            "principles": {
                "A1": {"outcomes": {"A1.a": {"code": "A1.a"}, "A1.b": {"code": "A1.b"}}},
                "A2": {"outcomes": {"A2.a": {"code": "A2.a"}}},
            },
        }

        self.review.review_data = {
            "assessor_response_data": {
                "A": {
                    "recommendations": [],
                    "objective-areas-of-improvement": "Some improvement",
                    "objective-areas-of-good-practice": "Good practice",
                    "A1.a": {"review_data": {"review_decision": "achieved"}},
                    "A1.b": {"review_data": {"review_decision": "achieved"}},
                    "A2.a": {"review_data": {"review_decision": "achieved"}},
                }
            }
        }
        self.review.save()

        with patch.object(self.review.assessment, "get_caf_objective_by_id", return_value=mock_caf_objective):
            result = self.review.is_objective_complete("A")

        self.assertTrue(result)

    def test_objective_complete_mixed_outcomes_with_recommendations(self):
        """Test that objective is complete with mix of achieved and non-achieved outcomes (with recommendations)."""
        mock_caf_objective = {
            "code": "A",
            "principles": {
                "A1": {"outcomes": {"A1.a": {"code": "A1.a"}, "A1.b": {"code": "A1.b"}, "A1.c": {"code": "A1.c"}}}
            },
        }

        self.review.review_data = {
            "assessor_response_data": {
                "A": {
                    "recommendations": [{"title": "Overall rec", "text": "Details"}],
                    "objective-areas-of-improvement": "Some improvement",
                    "objective-areas-of-good-practice": "Good practice",
                    "A1.a": {"review_data": {"review_decision": "achieved"}},
                    "A1.b": {
                        "review_data": {"review_decision": "not-achieved"},
                        "recommendations": [{"title": "Fix A1.b", "text": "Details"}],
                    },
                    "A1.c": {
                        "review_data": {"review_decision": "partially-achieved"},
                        "recommendations": [{"title": "Improve A1.c", "text": "Details"}],
                    },
                }
            }
        }
        self.review.save()

        with patch.object(self.review.assessment, "get_caf_objective_by_id", return_value=mock_caf_objective):
            result = self.review.is_objective_complete("A")

        self.assertTrue(result)

    def test_objective_incomplete_missing_outcome_data(self):
        """Test that objective is incomplete when an outcome is completely missing from review data."""
        mock_caf_objective = {
            "code": "A",
            "principles": {
                "A1": {
                    "outcomes": {
                        "A1.a": {"code": "A1.a"},
                        "A1.b": {"code": "A1.b"},  # This outcome is missing from review_data
                    }
                }
            },
        }

        self.review.review_data = {
            "assessor_response_data": {
                "A": {
                    "recommendations": [],
                    "objective-areas-of-improvement": "Some improvement",
                    "objective-areas-of-good-practice": "Good practice",
                    "A1.a": {"review_data": {"review_decision": "achieved"}}
                    # A1.b is missing
                }
            }
        }
        self.review.save()

        with patch.object(self.review.assessment, "get_caf_objective_by_id", return_value=mock_caf_objective):
            result = self.review.is_objective_complete("A")

        self.assertFalse(result)


class ReviewCompletionStateTests(BaseViewTest):
    @classmethod
    def setUpTestData(cls):
        BaseViewTest.setUpTestData()

        cls.assessment = Assessment.objects.create(
            system=cls.test_system,
            assessment_period="24/25",
            framework="caf32",
            caf_profile="baseline",
            review_type="independent",
        )

    def test_review_data_cannot_change_when_completed(self):
        review = Review.objects.create(
            assessment=self.assessment,
            status="completed",
            review_data={
                "assessor_response_data": {"initial": "value"},
                "review_completion": {"review_completed": "yes"},
            },
        )

        review.review_data = {
            "assessor_response_data": {"initial": "updated"},
            "review_completion": {"review_completed": "yes"},
        }

        with self.assertRaises(ValidationError):
            review.save()

    def test_review_can_be_finalised_when_completed(self):
        review = Review.objects.create(
            assessment=self.assessment,
            status="completed",
            review_data={
                "assessor_response_data": {"initial": "value"},
                "review_completion": {"review_completed": "yes"},
            },
        )

        review.finalise_review(self.user_profile)
        review.save()

        review.refresh_from_db()
        self.assertIn("review_finalised", review.review_data)
        self.assertTrue(review.review_data["review_finalised"].get("review_finalised_at"))

    def test_review_cannot_be_reopened_after_finalised(self):
        review = Review.objects.create(
            assessment=self.assessment,
            status="completed",
            review_data={
                "assessor_response_data": {"initial": "value"},
                "review_completion": {"review_completed": "yes"},
            },
        )

        review.finalise_review(self.user_profile)
        review.save()

        with self.assertRaises(ValidationError):
            review.reopen()


class ReviewSaveMethodTests(BaseViewTest):
    """
    Tests for the Review.save() method.

    Tests all possible branches:
    1. New review (pk is None) - should save successfully
    2. Existing review with no status change - should save successfully
    3. Completed review attempting to modify review_data - should raise ValidationError
    4. Completed review not modifying review_data - should save successfully
    5. Review with can_edit=False - should raise ValidationError
    6. Review with can_edit=True - should save successfully
    7. Review with outdated _original_last_updated - should raise ValidationError
    8. Review with matching _original_last_updated - should save successfully
    """

    @classmethod
    def setUpTestData(cls):
        BaseViewTest.setUpTestData()

        cls.assessment = Assessment.objects.create(
            system=cls.test_system,
            assessment_period="24/25",
            framework="caf32",
            caf_profile="baseline",
            review_type="independent",
        )

    def test_save_new_review_creates_successfully(self):
        """Test that a new review (pk=None) can be saved successfully."""
        new_review = Review()
        new_review.assessment = self.assessment
        new_review.status = "in_progress"
        new_review.review_data = {"test": "data"}
        # Should not raise any exception
        new_review.save()
        self.assertIsNotNone(new_review.pk)
        self.assertEqual(new_review.review_data, {"test": "data"})

    def test_save_existing_review_updates_successfully(self):
        """Test that an existing review with status != 'completed' can be updated."""
        review = Review()
        review.assessment = self.assessment
        review.status = "in_progress"
        review.review_data = {"test": "data"}
        review.save()

        review.review_data = {"test": "updated_data"}
        # Should not raise any exception
        review.save()
        review.refresh_from_db()
        self.assertEqual(review.review_data, {"test": "updated_data"})

    def test_save_completed_review_prevents_review_data_modification(self):
        """Test that modifying review_data on a completed review raises ValidationError."""
        review = Review()
        review.assessment = self.assessment
        review.status = "completed"
        review.review_data = {"assessor_response_data": {"test": "data"}}
        review.save()

        review.review_data = {"assessor_response_data": {"test": "modified_data"}}
        with self.assertRaises(ValidationError) as context:
            review.save()
        self.assertIn("Review data cannot be changed", str(context.exception))

    def test_save_completed_review_allows_other_field_changes(self):
        """Test that a completed review can update fields other than review_data."""
        review = Review()
        review.assessment = self.assessment
        review.status = "completed"
        review.review_data = {"test": "data"}
        review.save()

        # Change a different field (not review_data)
        review.last_updated_by = self.test_user
        # Should not raise any exception
        review.save()
        review.refresh_from_db()
        self.assertEqual(review.last_updated_by, self.test_user)

    def test_save_with_can_edit_false_raises_error(self):
        """Test that saving with can_edit=False raises ValidationError."""
        review = Review()
        review.assessment = self.assessment
        review.status = "in_progress"
        review.review_data = {"test": "data"}
        review.save()

        review.can_edit = False
        review.review_data = {"test": "modified"}
        with self.assertRaises(ValidationError) as context:
            review.save()
        self.assertIn("You do not have permission to edit this report", str(context.exception))

    def test_save_with_can_edit_true_succeeds(self):
        """Test that saving with can_edit=True succeeds."""
        review = Review()
        review.assessment = self.assessment
        review.status = "in_progress"
        review.review_data = {"test": "data"}
        review.save()

        review.can_edit = True
        review.review_data = {"test": "modified"}
        # Should not raise any exception
        review.save()
        review.refresh_from_db()
        self.assertEqual(review.review_data, {"test": "modified"})

    def test_save_with_outdated_original_last_updated_raises_error(self):
        """Test that saving with outdated _original_last_updated raises ValidationError."""
        review = Review()
        review.assessment = self.assessment
        review.status = "in_progress"
        review.review_data = {"test": "data"}
        review.save()

        original_last_updated = review.last_updated

        # Simulate another user updating the review
        review.review_data = {"test": "updated_by_another_user"}
        review.save()

        # Now try to save with the old timestamp
        review.review_data = {"test": "my_update"}
        review._original_last_updated = original_last_updated
        with self.assertRaises(ValidationError) as context:
            review.save()
        self.assertIn("Your copy of data has been updated since you last saved it", str(context.exception))

    def test_save_with_matching_original_last_updated_succeeds(self):
        """Test that saving with matching _original_last_updated succeeds."""
        review = Review()
        review.assessment = self.assessment
        review.status = "in_progress"
        review.review_data = {"test": "data"}
        review.save()

        # Set _original_last_updated to match current last_updated
        review._original_last_updated = review.last_updated
        review.review_data = {"test": "modified"}
        # Should not raise any exception
        review.save()
        review.refresh_from_db()
        self.assertEqual(review.review_data, {"test": "modified"})

    def test_save_without_original_last_updated_succeeds(self):
        """Test that saving without _original_last_updated attribute succeeds."""
        review = Review()
        review.assessment = self.assessment
        review.status = "in_progress"
        review.review_data = {"test": "data"}
        review.save()

        # Don't set _original_last_updated
        review.review_data = {"test": "modified"}
        # Should not raise any exception
        review.save()
        review.refresh_from_db()
        self.assertEqual(review.review_data, {"test": "modified"})

    def test_save_completed_to_in_progress_allows_review_data_change(self):
        """Test that changing status from completed to in_progress allows review_data modification."""
        review = Review()
        review.assessment = self.assessment
        review.status = "completed"
        review.review_data = {"test": "data"}
        review.save()

        review.status = "in_progress"
        review.review_data = {"test": "modified"}
        # Should not raise any exception
        review.save()
        review.refresh_from_db()
        self.assertEqual(review.status, "in_progress")
        self.assertEqual(review.review_data, {"test": "modified"})

    def test_save_multiple_validations_completed_status_checked_before_can_edit(self):
        """Test that completed status validation is checked before can_edit validation."""
        review = Review()
        review.assessment = self.assessment
        review.status = "completed"
        review.review_data = {"assessor_response_data": {"test": "data"}}
        review.save()

        review.can_edit = False
        review.review_data = {"assessor_response_data": {"test": "modified"}}
        # The completed status check comes before can_edit check
        with self.assertRaises(ValidationError) as context:
            review.save()
        # The error should be about completed status, not permissions
        self.assertIn("Review data cannot be changed after it has been marked as completed", str(context.exception))

    def test_save_multiple_validations_completed_status_checked_first(self):
        """Test that completed status validation is checked before last_updated validation."""
        review = Review()
        review.assessment = self.assessment
        review.status = "completed"
        review.review_data = {"assessor_response_data": {"test": "data"}}
        review.save()

        original_last_updated = review.last_updated

        # Update the review to change last_updated
        review.review_data = {"assessor_response_data": {"test": "data"}}  # Keep data same
        review.save()

        # Now try to modify review_data with outdated timestamp
        review.review_data = {"assessor_response_data": {"test": "modified"}}
        review._original_last_updated = original_last_updated
        # Should raise completed status error, not stale data error
        with self.assertRaises(ValidationError) as context:
            review.save()
        self.assertIn("Review data cannot be changed after it has been marked as completed", str(context.exception))


class ReviewRefreshFromDbTests(BaseViewTest):
    """
    Tests for the Review.refresh_from_db() method.

    Tests all possible scenarios:
    1. refresh_from_db updates _original_last_updated to current database value
    2. After refresh_from_db, saving without changes succeeds
    3. After refresh_from_db, if another process modifies the record, optimistic lock still works
    4. refresh_from_db with specific fields parameter works correctly
    5. refresh_from_db properly reloads all field values from database
    """

    @classmethod
    def setUpTestData(cls):
        BaseViewTest.setUpTestData()

        cls.assessment = Assessment.objects.create(
            system=cls.test_system,
            assessment_period="24/25",
            framework="caf32",
            caf_profile="baseline",
            review_type="independent",
        )

    def test_refresh_from_db_updates_original_last_updated(self):
        """Test that refresh_from_db updates _original_last_updated to match database."""
        review = Review()
        review.assessment = self.assessment
        review.status = "in_progress"
        review.review_data = {"test": "data"}
        review.save()

        original_timestamp = review.last_updated
        original_tracked = review._original_last_updated
        self.assertEqual(original_timestamp, original_tracked)

        # Simulate another process updating the review (using another instance)
        other_instance = Review.objects.get(pk=review.pk)
        other_instance.review_data = {"test": "updated_by_another_process"}
        other_instance.save()

        # Refresh from database
        review.refresh_from_db()

        # _original_last_updated should now match the new last_updated from database
        self.assertEqual(review._original_last_updated, review.last_updated)
        # And it should be different from the original
        self.assertNotEqual(review._original_last_updated, original_tracked)

    def test_refresh_from_db_then_save_succeeds(self):
        """Test that after refresh_from_db, saving changes succeeds without optimistic lock error."""
        review = Review()
        review.assessment = self.assessment
        review.status = "in_progress"
        review.review_data = {"test": "data"}
        review.save()

        # Simulate another process updating the review
        Review.objects.filter(pk=review.pk).update(review_data={"test": "updated_by_another_process"})

        # Refresh to get the latest data
        review.refresh_from_db()

        # Now modify and save - should succeed because _original_last_updated was updated
        review.review_data = {"test": "my_change_after_refresh"}
        # Should not raise any exception
        review.save()
        review.refresh_from_db()
        self.assertEqual(review.review_data, {"test": "my_change_after_refresh"})

    def test_refresh_from_db_reloads_field_values(self):
        """Test that refresh_from_db properly reloads all field values from database."""
        review = Review()
        review.assessment = self.assessment
        review.status = "in_progress"
        review.review_data = {"test": "data"}
        review.save()

        # Modify in-memory instance
        review.review_data = {"test": "modified_in_memory"}
        review.status = "clarify"
        self.assertEqual(review.review_data, {"test": "modified_in_memory"})
        self.assertEqual(review.status, "clarify")

        # Refresh from database (without saving)
        review.refresh_from_db()

        # Values should be back to what's in the database
        self.assertEqual(review.review_data, {"test": "data"})
        self.assertEqual(review.status, "in_progress")

    def test_refresh_from_db_with_specific_fields(self):
        """Test that refresh_from_db works correctly with specific fields parameter."""
        review = Review()
        review.assessment = self.assessment
        review.status = "in_progress"
        review.review_data = {"test": "data"}
        review.save()

        # Simulate another process updating multiple fields
        Review.objects.filter(pk=review.pk).update(review_data={"test": "updated_data"}, status="clarify")

        # Modify in-memory instance
        review.review_data = {"test": "in_memory_change"}
        review.status = "cancelled"

        # Refresh only the status field
        review.refresh_from_db(fields=["status"])

        # Status should be refreshed from database
        self.assertEqual(review.status, "clarify")
        # review_data should still have the in-memory change
        self.assertEqual(review.review_data, {"test": "in_memory_change"})
        # _original_last_updated should still be updated
        self.assertIsNotNone(review._original_last_updated)

    def test_refresh_from_db_after_concurrent_modification_prevents_overwrite(self):
        """Test that refresh_from_db helps prevent lost updates in concurrent scenarios."""
        # User 1 loads the review
        review_user1 = Review.objects.get(
            pk=Review.objects.create(
                assessment=self.assessment,
                status="in_progress",
                review_data={"test": "initial"},
            ).pk
        )
        original_timestamp_user1 = review_user1._original_last_updated

        # User 2 loads and modifies the same review
        review_user2 = Review.objects.get(pk=review_user1.pk)
        review_user2.review_data = {"test": "user2_change"}
        review_user2.save()

        # User 1 tries to save with their old timestamp - should fail
        review_user1.review_data = {"test": "user1_change"}
        with self.assertRaises(ValidationError) as context:
            review_user1.save()
        self.assertIn("Your copy of data has been updated since you last saved it", str(context.exception))

        # User 1 refreshes to get latest data
        review_user1.refresh_from_db()
        self.assertEqual(review_user1.review_data, {"test": "user2_change"})
        self.assertNotEqual(review_user1._original_last_updated, original_timestamp_user1)

        # Now User 1 can make their change on top of User 2's change
        review_user1.review_data = {"test": "user1_change_after_refresh"}
        # Should succeed
        review_user1.save()
        review_user1.refresh_from_db()
        self.assertEqual(review_user1.review_data, {"test": "user1_change_after_refresh"})

    def test_refresh_from_db_on_new_unsaved_instance(self):
        """Test that refresh_from_db doesn't break when called on a new instance after save."""
        review = Review()
        review.assessment = self.assessment
        review.status = "in_progress"
        review.review_data = {"test": "data"}
        # At this point, _original_last_updated is None because pk is None
        self.assertIsNone(review._original_last_updated)

        review.save()
        # After save, _original_last_updated should be set
        self.assertIsNotNone(review._original_last_updated)

        # Refresh should work fine
        review.refresh_from_db()
        self.assertEqual(review._original_last_updated, review.last_updated)

    def test_refresh_from_db_maintains_optimistic_locking_protection(self):
        """Test that refresh_from_db properly maintains optimistic locking after multiple refreshes."""
        review = Review()
        review.assessment = self.assessment
        review.status = "in_progress"
        review.review_data = {"test": "data"}
        review.save()

        timestamp_after_create = review._original_last_updated

        # First refresh (no external changes yet)
        review.refresh_from_db()
        timestamp_after_first_refresh = review._original_last_updated
        self.assertEqual(timestamp_after_first_refresh, timestamp_after_create)

        # Simulate external update using another instance
        other_instance = Review.objects.get(pk=review.pk)
        other_instance.review_data = {"test": "external_update_1"}
        other_instance.save()

        # Second refresh
        review.refresh_from_db()
        timestamp_after_second_refresh = review._original_last_updated
        # Timestamp should be updated because last_updated changed in the database
        self.assertNotEqual(timestamp_after_second_refresh, timestamp_after_first_refresh)

        # Save should succeed because we have the latest timestamp
        review.review_data = {"test": "my_update"}
        review.save()  # Should not raise
        review.refresh_from_db()
        self.assertEqual(review.review_data, {"test": "my_update"})


class ReviewReopenTests(BaseViewTest):
    """
    Tests for the Review.reopen() method.

    Tests that reopening a completed review transitions it back to in_progress
    and clears completion data, while preventing reopening from invalid states.
    """

    @classmethod
    def setUpTestData(cls):
        BaseViewTest.setUpTestData()

        cls.assessment = Assessment.objects.create(
            system=cls.test_system,
            assessment_period="24/25",
            framework="caf32",
            caf_profile="baseline",
            review_type="independent",
        )

    def test_reopen_completed_review_changes_status(self):
        """Test that reopening a completed review changes status to in_progress."""
        review = Review.objects.create(
            assessment=self.assessment,
            status="completed",
            review_data={
                "assessor_response_data": {
                    "review_completion": {
                        "review_completed": "yes",
                        "review_completed_at": "2024-12-01T10:00:00.000000",
                    }
                }
            },
        )

        review.reopen()

        self.assertEqual(review.status, "in_progress")

    def test_reopen_clears_completion_data(self):
        """Test that reopening clears review_completion data."""
        review = Review.objects.create(
            assessment=self.assessment,
            status="completed",
            review_data={
                "assessor_response_data": {},
                "review_completion": {
                    "review_completed": "yes",
                    "review_completed_at": "2024-12-01T10:00:00.000000",
                },
            },
        )

        review.reopen()
        assessor_response = review.get_assessor_response()
        review_completion = assessor_response.get("review_completion", {})
        self.assertEqual(review_completion, {})

    def test_reopen_from_to_do_raises_error(self):
        """Test that reopening from to_do status raises ValidationError."""
        review = Review.objects.create(assessment=self.assessment, status="to_do")

        with self.assertRaises(ValidationError) as context:
            review.reopen()
        self.assertIn("Invalid state for report reopening", str(context.exception))

    def test_reopen_from_in_progress_raises_error(self):
        """Test that reopening from in_progress status raises ValidationError."""
        review = Review.objects.create(assessment=self.assessment, status="in_progress")

        with self.assertRaises(ValidationError) as context:
            review.reopen()
        self.assertIn("Invalid state for report reopening", str(context.exception))

    def test_reopen_from_clarify_raises_error(self):
        """Test that reopening from clarify status raises ValidationError."""
        review = Review.objects.create(assessment=self.assessment, status="clarify")

        with self.assertRaises(ValidationError) as context:
            review.reopen()
        self.assertIn("Invalid state for report reopening", str(context.exception))

    def test_reopen_from_cancelled_raises_error(self):
        """Test that reopening from cancelled status raises ValidationError."""
        review = Review.objects.create(assessment=self.assessment, status="cancelled")

        with self.assertRaises(ValidationError) as context:
            review.reopen()
        self.assertIn("Invalid state for report reopening", str(context.exception))

    def test_reopen_allows_further_edits(self):
        """Test that after reopening, the review can be edited."""
        review = Review.objects.create(
            assessment=self.assessment,
            status="completed",
            review_data={
                "assessor_response_data": {"review_completion": {"review_completed": "yes"}, "A": {"some": "data"}}
            },
        )

        review.reopen()

        # Should be able to modify review_data now
        review.review_data["assessor_response_data"]["A"]["new_field"] = "value"
        review.save()  # Should not raise

        review.refresh_from_db()
        self.assertEqual(review.review_data["assessor_response_data"]["A"]["new_field"], "value")


class ReviewCompletionInfoTests(BaseViewTest):
    """
    Tests for the Review.completion_info property.

    Tests that completion_info correctly retrieves and parses completion data.
    """

    @classmethod
    def setUpTestData(cls):
        BaseViewTest.setUpTestData()

        cls.assessment = Assessment.objects.create(
            system=cls.test_system,
            assessment_period="24/25",
            framework="caf32",
            caf_profile="baseline",
            review_type="independent",
        )

    def test_completion_info_returns_none_when_no_data(self):
        """Test that completion_info returns None when no completion data exists."""
        review = Review.objects.create(assessment=self.assessment, status="in_progress", review_data={})

        self.assertIsNone(review.completion_info)

    def test_completion_info_returns_none_when_empty_dict(self):
        """Test that completion_info returns None when review_completion is empty."""
        review = Review.objects.create(
            assessment=self.assessment, status="in_progress", review_data={"assessor_response_data": {}}
        )

        self.assertIsNone(review.completion_info)

    def test_completion_info_returns_dict_when_present(self):
        """Test that completion_info returns dict when completion data exists."""
        review = Review.objects.create(
            assessment=self.assessment,
            status="completed",
            review_data={"assessor_response_data": {}, "review_completion": {"review_completed": "yes"}},
        )

        completion_info = review.completion_info
        self.assertIsNotNone(completion_info)
        self.assertEqual(completion_info["review_completed"], "yes")

    def test_completion_info_parses_datetime_string(self):
        """Test that completion_info parses ISO datetime strings."""
        from datetime import datetime

        review = Review.objects.create(
            assessment=self.assessment,
            status="completed",
            review_data={
                "assessor_response_data": {},
                "review_completion": {
                    "review_completed": "yes",
                    "review_completed_at": "2024-12-01T10:30:45.123456",
                },
            },
        )

        completion_info = review.completion_info
        self.assertIsNotNone(completion_info)
        self.assertIsInstance(completion_info["review_completed_at"], datetime)
        self.assertEqual(completion_info["review_completed_at"].year, 2024)
        self.assertEqual(completion_info["review_completed_at"].month, 12)
        self.assertEqual(completion_info["review_completed_at"].day, 1)

    def test_completion_info_handles_already_parsed_datetime(self):
        """Test that completion_info handles datetime objects that are already parsed."""
        from datetime import datetime

        dt = datetime(2024, 12, 1, 10, 30, 45)
        review = Review.objects.create(
            assessment=self.assessment,
            status="completed",
            review_data={
                "assessor_response_data": {},
                "review_completion": {
                    "review_completed": "yes",
                    "review_completed_at": dt.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                },
            },
        )

        completion_info = review.completion_info
        self.assertIsNotNone(completion_info)
        self.assertIsInstance(completion_info["review_completed_at"], datetime)
        self.assertEqual(completion_info["review_completed_at"], dt)

    def test_completion_info_without_completed_at(self):
        """Test completion_info when review_completed_at is not present."""
        review = Review.objects.create(
            assessment=self.assessment,
            status="completed",
            review_data={
                "assessor_response_data": {},
                "review_completion": {
                    "review_completed": "yes"
                    # No review_completed_at
                },
            },
        )

        completion_info = review.completion_info
        self.assertIsNotNone(completion_info)
        self.assertEqual(completion_info["review_completed"], "yes")
        self.assertNotIn("review_completed_at", completion_info)


class ReviewIsCompanyDetailsCompleteTests(BaseViewTest):
    """
    Tests for the Review.is_company_details_complete() method.

    Tests that the method correctly identifies when company details are complete.
    """

    @classmethod
    def setUpTestData(cls):
        BaseViewTest.setUpTestData()

        cls.assessment = Assessment.objects.create(
            system=cls.test_system,
            assessment_period="24/25",
            framework="caf32",
            caf_profile="baseline",
            review_type="independent",
        )

    def test_returns_true_with_valid_company_details(self):
        """Test that method returns True when company details exist."""
        review = Review.objects.create(
            assessment=self.assessment,
            status="in_progress",
            review_data={
                "assessor_response_data": {
                    "additional_information": {
                        "company_details": {"company_name": "Test Company", "lead_assessor_name": "test@example.com"}
                    }
                }
            },
        )

        self.assertTrue(review.is_company_details_complete())

    def test_returns_false_when_company_details_missing(self):
        """Test that method returns False when company_details key doesn't exist."""
        review = Review.objects.create(
            assessment=self.assessment,
            status="in_progress",
            review_data={"assessor_response_data": {"additional_information": {}}},
        )

        self.assertFalse(review.is_company_details_complete())

    def test_returns_false_when_company_details_none(self):
        """Test that method returns False when company_details is None."""
        review = Review.objects.create(
            assessment=self.assessment,
            status="in_progress",
            review_data={"assessor_response_data": {"additional_information": {"company_details": None}}},
        )

        self.assertFalse(review.is_company_details_complete())

    def test_returns_false_when_additional_information_missing(self):
        """Test that method returns False when additional_information doesn't exist."""
        review = Review.objects.create(
            assessment=self.assessment, status="in_progress", review_data={"assessor_response_data": {}}
        )

        self.assertFalse(review.is_company_details_complete())
