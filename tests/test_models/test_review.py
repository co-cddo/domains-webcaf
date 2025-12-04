from unittest.mock import patch

from tests.test_views.base_view_test import BaseViewTest
from webcaf.webcaf.models import Assessment, Assessor, Review


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
            assessment_period="2024/25",
            framework="caf32",
            caf_profile="baseline",
            review_type="independent",
        )
        cls.assessor = Assessor.objects.create(
            name="Acme Assurance Ltd",
            contact_name="Jane Doe",
            email="assessor@example.com",
            address="1 High St, London",
            phone_number="0123456789",
            assessor_type="independent",
            organisation=cls.test_organisation,
        )
        cls.review = Review.objects.create(
            assessment=cls.assessment,
            assessed_by=cls.assessor,
            status="in_progress",
        )

    def test_objective_incomplete_missing_recommendations_key(self):
        """Test that objective is incomplete when 'recommendations' key is missing at objective level."""
        # Mock the CAF objective structure
        mock_caf_objective = {"code": "A", "principles": {"A1": {"outcomes": {"A1.a": {"code": "A1.a"}}}}}

        # Set review data with missing 'recommendations' key
        self.review.review_data = {
            "assessor_response_data": {
                "A": {
                    "objective-areas-of-improvement": "Some improvement",
                    "objective-areas-of-good-practice": "Good practice",
                    # Missing 'recommendations' key
                    "A1.a": {"review_data": {"review_decision": "achieved"}},
                }
            }
        }
        self.review.save()

        with patch.object(self.review.assessment, "get_caf_objective_by_id", return_value=mock_caf_objective):
            result = self.review.is_objective_complete("A")

        self.assertFalse(result)

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
