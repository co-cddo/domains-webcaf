from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.forms import BaseFormSet
from django.forms.boundfield import BoundField
from django.test import TestCase
from parameterized import parameterized

from webcaf.webcaf.caf.routers import CAF32Router
from webcaf.webcaf.models import Assessment, Organisation, Review
from webcaf.webcaf.templatetags.review_tags import (
    PrincipleOutcomeStatus,
    RecommendationGroup,
    ReviewComment,
    ReviewStatusInfo,
    get_indicator_comments,
)
from webcaf.webcaf.templatetags.review_tags import get_objectives as get_objectives_tag
from webcaf.webcaf.templatetags.review_tags import (
    get_outcome_category_names,
    get_outcome_recommendation_count,
    get_outcome_status,
    get_path,
    get_principle,
    get_principle_profile_status,
    get_recommendation_count,
    get_recommendations,
    get_review_completed_percentage,
    get_review_outcome_statuses,
    get_selected_tag,
    get_user_role,
    is_comment_present,
    is_review_all_objectives_complete,
    is_review_objective_complete,
)


class TestGetSelectedTag(TestCase):
    def test_returns_selected_when_indicator_exists(self):
        field = Mock(spec=BoundField)
        field.name = "achieved_A1.a.5"
        answered_statements = {"indicators": {"achieved_A1.a.5": True}}

        result = get_selected_tag(field, answered_statements)

        self.assertEqual(result, "selected")

    def test_returns_did_not_select_when_indicator_missing(self):
        field = Mock(spec=BoundField)
        field.name = "achieved_A1.a.5"
        answered_statements = {"indicators": {}}

        result = get_selected_tag(field, answered_statements)

        self.assertEqual(result, "did not select")

    def test_returns_did_not_select_when_indicator_is_false(self):
        field = Mock(spec=BoundField)
        field.name = "achieved_A1.a.5"
        answered_statements = {"indicators": {"achieved_A1.a.5": False}}

        result = get_selected_tag(field, answered_statements)

        self.assertEqual(result, "did not select")


class TestGetOutcomeCategoryNames(TestCase):
    def test_returns_correct_categories(self):
        result = get_outcome_category_names()
        self.assertEqual(result, ["achieved", "partially-achieved", "not-achieved"])
        self.assertEqual(len(result), 3)


class TestGetOutcomeStatus(TestCase):
    def test_returns_review_decision(self):
        review = Mock(spec=Review)
        review.get_outcome_review.return_value = {"review_decision": "achieved"}

        result = get_outcome_status("obj1", "outcome1", review)

        self.assertEqual(result, "achieved")
        review.get_outcome_review.assert_called_once_with("obj1", "outcome1")

    def test_returns_none_when_review_decision_missing(self):
        review = Mock(spec=Review)
        review.get_outcome_review.return_value = {}

        result = get_outcome_status("obj1", "outcome1", review)

        self.assertIsNone(result)


class TestGetRecommendationCount(TestCase):
    def test_counts_non_deleted_forms(self):
        parent_form = Mock(spec=BaseFormSet)
        form1 = Mock()
        form1.cleaned_data = {"DELETE": False, "text": "recommendation 1"}
        form2 = Mock()
        form2.cleaned_data = {"DELETE": True, "text": "recommendation 2"}
        form3 = Mock()
        form3.cleaned_data = {"DELETE": False, "text": "recommendation 3"}
        parent_form.forms = [form1, form2, form3]

        result = get_recommendation_count(parent_form)

        self.assertEqual(result, 2)

    def test_returns_zero_when_all_deleted(self):
        parent_form = Mock(spec=BaseFormSet)
        form1 = Mock()
        form1.cleaned_data = {"DELETE": True}
        parent_form.forms = [form1]

        result = get_recommendation_count(parent_form)

        self.assertEqual(result, 0)

    def test_returns_zero_when_no_forms(self):
        parent_form = Mock(spec=BaseFormSet)
        parent_form.forms = []

        result = get_recommendation_count(parent_form)

        self.assertEqual(result, 0)


class TestGetOutcomeRecommendationCount(TestCase):
    def test_returns_correct_count(self):
        review = Mock(spec=Review)
        review.get_outcome_recommendations.return_value = [
            {"title": "rec1", "text": "text1"},
            {"title": "rec2", "text": "text2"},
        ]

        result = get_outcome_recommendation_count(review, "obj1", "outcome1")

        self.assertEqual(result, 2)
        review.get_outcome_recommendations.assert_called_once_with("obj1", "outcome1")

    def test_returns_zero_when_no_recommendations(self):
        review = Mock(spec=Review)
        review.get_outcome_recommendations.return_value = []

        result = get_outcome_recommendation_count(review, "obj1", "outcome1")

        self.assertEqual(result, 0)


class TestGetUserRole(TestCase):
    def test_returns_role_display_name_when_profile_exists(self):
        user = Mock(spec=User)
        organisation = Mock(spec=Organisation)

        profile = Mock()
        profile.organisation = organisation
        profile.get_role_display.return_value = "Administrator"

        user.profiles.filter.return_value = [profile]

        result = get_user_role(user, organisation)

        self.assertEqual(result, "Administrator")
        profile.get_role_display.assert_called_once()

    def test_returns_dash_when_no_profile_exists(self):
        user = Mock(spec=User)
        organisation = Mock(spec=Organisation)
        user.profiles.filter.return_value = []

        result = get_user_role(user, organisation)

        self.assertEqual(result, "-")

    def test_returns_dash_when_user_is_none(self):
        organisation = Mock(spec=Organisation)

        result = get_user_role(None, organisation)

        self.assertEqual(result, "-")


class TestIsCommentPresent(TestCase):
    def test_returns_true_when_comment_exists(self):
        review = Mock(spec=Review)
        review.get_objective_comments.return_value = "Some comment"

        result = is_comment_present(review, "obj1", "section1")

        self.assertTrue(result)

    def test_returns_false_when_comment_is_none(self):
        review = Mock(spec=Review)
        review.get_objective_comments.return_value = None

        result = is_comment_present(review, "obj1", "section1")

        self.assertFalse(result)


class TestIsReviewObjectiveComplete(TestCase):
    def test_returns_true_when_objective_complete(self):
        review = Mock(spec=Review)
        review.is_objective_complete.return_value = True

        result = is_review_objective_complete(review, "obj1")

        self.assertTrue(result)
        review.is_objective_complete.assert_called_once_with("obj1")

    def test_returns_false_when_objective_incomplete(self):
        review = Mock(spec=Review)
        review.is_objective_complete.return_value = False

        result = is_review_objective_complete(review, "obj1")

        self.assertFalse(result)


class TestIsReviewAllObjectivesComplete(TestCase):
    def test_returns_true_when_all_objectives_complete(self):
        review = Mock(spec=Review)
        review.is_all_objectives_complete.return_value = True

        result = is_review_all_objectives_complete(review)

        self.assertTrue(result)

    def test_returns_false_when_not_all_objectives_complete(self):
        review = Mock(spec=Review)
        review.is_all_objectives_complete.return_value = False

        result = is_review_all_objectives_complete(review)

        self.assertFalse(result)


class TestGetReviewCompletedPercentage(TestCase):
    @parameterized.expand(
        [
            # (completed_outcomes, total_outcomes, iar_complete, quality_complete, method_complete, scope_complete, company_complete, expected_percentage)
            (0, 10, False, False, False, False, False, 0),
            (5, 10, False, False, False, False, False, 45),  # 90 * 5 / 10
            (10, 10, False, False, False, False, False, 90),  # All outcomes complete
            (10, 10, True, True, True, True, True, 100),  # All complete
            (5, 10, True, False, False, False, False, 47),  # 45 + 2*1
            (5, 10, True, True, True, False, False, 51),  # 45 + 2*3
            (0, 0, True, True, True, True, True, 10),  # No outcomes but all attributes complete
        ]
    )
    def test_calculates_correct_percentage(
        self,
        completed_outcomes,
        total_outcomes,
        iar_complete,
        quality_complete,
        method_complete,
        scope_complete,
        company_complete,
        expected_percentage,
    ):
        review = Mock(spec=Review)
        review.get_completed_outcomes_info.return_value = {
            "completed_outcomes": completed_outcomes,
            "total_outcomes": total_outcomes,
        }
        review.is_iar_period_complete.return_value = iar_complete
        review.is_quality_of_evidence_complete.return_value = quality_complete
        review.is_review_method_complete.return_value = method_complete
        review.is_system_and_scope_complete.return_value = scope_complete
        review.is_company_details_complete.return_value = company_complete

        result = get_review_completed_percentage(review)

        self.assertEqual(result, expected_percentage)


class TestGetPath(TestCase):
    def test_returns_value_at_simple_path(self):
        review = Mock(spec=Review)
        review.review_data = {"key1": "value1"}

        result = get_path(review, "key1")

        self.assertEqual(result, "value1")

    def test_returns_value_at_nested_path(self):
        review = Mock(spec=Review)
        review.review_data = {"level1": {"level2": {"level3": "deep_value"}}}

        result = get_path(review, "level1.level2.level3")

        self.assertEqual(result, "deep_value")

    def test_returns_dict_at_partial_path(self):
        review = Mock(spec=Review)
        review.review_data = {"level1": {"level2": {"level3": "deep_value"}}}

        result = get_path(review, "level1.level2")

        self.assertEqual(result, {"level3": "deep_value"})

    def test_returns_none_when_path_not_found(self):
        review = Mock(spec=Review)
        review.review_data = {"key1": "value1"}

        result = get_path(review, "nonexistent")

        self.assertIsNone(result)

    def test_returns_none_when_partial_path_not_found(self):
        review = Mock(spec=Review)
        review.review_data = {"level1": {"level2": "value"}}

        result = get_path(review, "level1.nonexistent.level3")

        self.assertIsNone(result)


class TestGetObjectives(TestCase):
    def test_returns_all_caf_objectives(self):
        review = Mock(spec=Review)
        assessment = Mock(spec=Assessment)
        review.assessment = assessment
        expected_objectives = [
            {"code": "obj1", "title": "Objective 1"},
            {"code": "obj2", "title": "Objective 2"},
        ]
        assessment.get_all_caf_objectives.return_value = expected_objectives

        result = get_objectives_tag(review)

        self.assertEqual(result, expected_objectives)
        assessment.get_all_caf_objectives.assert_called_once()


class TestGetReviewOutcomeStatuses(TestCase):
    def test_returns_status_info_namedtuple(self):
        review = Mock(spec=Review)
        assessment = Mock(spec=Assessment)
        review.assessment = assessment

        assessment.assessments_data = {"outcome1": {"confirmation": {"outcome_status": "Achieved"}}}
        review.review_data = {
            "assessor_response_data": {"obj1": {"outcome1": {"review_data": {"review_decision": "achieved"}}}}
        }

        result = get_review_outcome_statuses(review, "obj1", "outcome1")

        self.assertIsInstance(result, ReviewStatusInfo)
        self.assertEqual(result.status, "Achieved")
        self.assertEqual(result.review_decision, "achieved")


class TestGetPrincipleProfileStatus(TestCase):
    @patch("webcaf.webcaf.templatetags.review_tags.IndicatorStatusChecker")
    @patch("webcaf.webcaf.templatetags.review_tags.status_to_label")
    def test_returns_all_true_when_requirements_met(self, mock_status_to_label, mock_checker):
        review = Mock(spec=Review)
        assessment = Mock(spec=Assessment)
        review.assessment = assessment

        assessment.assessments_data = {
            "P1.1": {"confirmation": {"outcome_status": "Achieved"}},
            "P1.2": {"confirmation": {"outcome_status": "Achieved"}},
        }
        review.review_data = {
            "assessor_response_data": {
                "obj1": {
                    "P1.1": {"review_data": {"review_decision": "achieved"}},
                    "P1.2": {"review_data": {"review_decision": "achieved"}},
                }
            }
        }

        mock_status_to_label.return_value = "achieved"
        mock_checker.indicator_min_profile_requirement_met.return_value = "Yes"

        result = get_principle_profile_status(review, "obj1", "P1")

        self.assertEqual(result, PrincipleOutcomeStatus(True, True, 2, 2, 2))

    @patch("webcaf.webcaf.templatetags.review_tags.IndicatorStatusChecker")
    @patch("webcaf.webcaf.templatetags.review_tags.status_to_label")
    def test_returns_false_when_requirements_not_met(self, mock_status_to_label, mock_checker):
        review = Mock(spec=Review)
        assessment = Mock(spec=Assessment)
        review.assessment = assessment

        assessment.assessments_data = {
            "P1.1": {"confirmation": {"outcome_status": "Not achieved"}},
        }
        review.review_data = {
            "assessor_response_data": {
                "obj1": {
                    "P1.1": {"review_data": {"review_decision": "not-achieved"}},
                }
            }
        }

        mock_status_to_label.return_value = "not-achieved"
        mock_checker.indicator_min_profile_requirement_met.return_value = "No"

        result = get_principle_profile_status(review, "obj1", "P1")

        self.assertEqual(result, PrincipleOutcomeStatus(False, False, 1, 0, 0))


class TestGetRecommendations(TestCase):
    def setUp(self):
        self.review = Mock(spec=Review)
        self.assessment = Mock(spec=Assessment)
        self.review.assessment = self.assessment
        mock_router = Mock(spec=CAF32Router)
        objectives = {
            "A": {
                "code": "A",
                "title": "Objective A",
                "principles": {
                    "A1": {
                        "code": "A1",
                        "title": "Principle 1",
                        "outcomes": {
                            "A1.a": {
                                "code": "A1.a",
                                "title": "Outcome 1.1",
                                "min_profile_requirement": {"baseline": "Achieved"},
                            },
                            "A1.b": {
                                "code": "A1.b",
                                "title": "Outcome 1.2",
                                "min_profile_requirement": {"baseline": "Achieved"},
                            },
                            "A1.c": {
                                "code": "A1.c",
                                "title": "Outcome 1.2.3",
                                "min_profile_requirement": {"baseline": "Achieved"},
                            },
                        },
                    }
                },
            }
        }
        mock_router.get_sections.return_value = objectives
        mock_router.get_section.side_effect = lambda section_code: objectives.get(section_code, None)
        self.assessment.get_router.return_value = mock_router
        self.assessment.caf_profile = "baseline"
        self.assessment.get_all_caf_objectives.return_value = list(objectives.values())

    def test_returns_all_recommendations_when_mode_is_all(self):
        self.review.get_assessor_response.return_value = {
            "A": {
                "A1.a": {
                    "review_data": {"review_decision": "achieved"},
                    "recommendations": [
                        {"title": "Rec 1", "text": "Text 1"},
                    ],
                },
                "A1.b": {
                    "review_data": {"review_decision": "achieved"},
                    "recommendations": [],
                },
                "A1.c": {
                    "review_data": {"review_decision": "achieved"},
                    "recommendations": [],
                },
            }
        }

        result = get_recommendations(self.review, "all")

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], RecommendationGroup)
        self.assertEqual(result[0].recommendations[0].id, "REC-A1A1")
        self.assertEqual(result[0].group_index, 1)
        self.assertEqual(result[0].recommendations[0].title, "Rec 1")
        self.assertEqual(result[0].recommendations[0].text, "Text 1")
        self.assertEqual(result[0].recommendations[0].objective, "A")
        self.assertEqual(result[0].recommendations[0].outcome, "A1.a")

    def test_returns_only_priority_recommendations_when_mode_is_priority(self):
        self.review.get_assessor_response.return_value = {
            "A": {
                "A1.a": {
                    "review_data": {"review_decision": "not-achieved"},
                    "recommendations": [{"title": "Priority Rec", "text": "Priority Text"}],
                },
                "A1.b": {
                    "review_data": {"review_decision": "achieved"},
                    "recommendations": [{"title": "Normal Rec", "text": "Normal Text"}],
                },
                "A1.c": {
                    "review_data": {"review_decision": "achieved"},
                    "recommendations": [],
                },
            }
        }

        result = get_recommendations(self.review, "priority")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Priority Rec")
        self.assertEqual(result[0].recommendations[0].title, "Priority Rec")
        self.assertEqual(result[0].recommendations[0].text, "Priority Text")

    def test_returns_only_normal_recommendations_when_mode_is_normal(self):
        self.review.get_assessor_response.return_value = {
            "A": {
                "A1.a": {
                    "review_data": {"review_decision": "partially-achieved"},
                    "recommendations": [{"title": "Priority Rec", "text": "Priority Text"}],
                },
                "A1.b": {
                    "review_data": {"review_decision": "achieved"},
                    "recommendations": [{"title": "Normal Rec", "text": "Normal Text"}],
                },
                "A1.c": {
                    "review_data": {"review_decision": "achieved"},
                    "recommendations": [],
                },
            }
        }

        result = get_recommendations(self.review, "normal")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Normal Rec")
        self.assertEqual(result[0].recommendations[0].title, "Normal Rec")
        self.assertEqual(result[0].recommendations[0].text, "Normal Text")

    def test_returns_only_normal_recommendations_with_groups_when_mode_is_normal(self):
        self.review.get_assessor_response.return_value = {
            "A": {
                "A1.a": {
                    "review_data": {"review_decision": "partially-achieved"},
                    "recommendations": [{"title": "Priority Rec", "text": "Priority Text"}],
                },
                "A1.b": {
                    "review_data": {"review_decision": "achieved"},
                    "recommendations": [{"title": "Normal Rec", "text": "Normal Text 1"}],
                },
                "A1.c": {
                    "review_data": {"review_decision": "achieved"},
                    "recommendations": [{"title": "Normal Rec", "text": "Normal Text 2"}],
                },
            }
        }

        result = get_recommendations(self.review, "normal")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Normal Rec")
        self.assertEqual(len(result[0].recommendations), 2)
        self.assertEqual(result[0].recommendations[0].title, "Normal Rec")
        self.assertEqual(result[0].recommendations[1].title, "Normal Rec")

    def test_generates_correct_recommendation_ids(self):
        self.review.get_assessor_response.return_value = {
            "A": {
                "A1.a": {
                    "review_data": {"review_decision": "achieved"},
                    "recommendations": [
                        {"title": "Rec 1", "text": "Text 1"},
                        {"title": "Rec 2", "text": "Text 2"},
                    ],
                },
                "A1.b": {
                    "review_data": {"review_decision": "achieved"},
                    "recommendations": [],
                },
                "A1.c": {
                    "review_data": {"review_decision": "achieved"},
                    "recommendations": [{"title": "Rec 3", "text": "Text 3"}],
                },
            }
        }
        result = get_recommendations(self.review, "all")

        self.assertEqual(len(result), 3)
        # All results are grouped in its own group
        self.assertEqual(result[0].group_index, 1)
        self.assertEqual(result[0].recommendations[0].id, "REC-A1A1")
        self.assertEqual(result[1].group_index, 2)
        self.assertEqual(result[1].recommendations[0].id, "REC-A1A2")
        self.assertEqual(result[2].group_index, 3)
        self.assertEqual(result[2].recommendations[0].id, "REC-A1C1")

    def test_generates_correct_recommendation_ids_with_group_index(self):
        self.review.get_assessor_response.return_value = {
            "A": {
                "A1.a": {
                    "review_data": {"review_decision": "achieved"},
                    "recommendations": [
                        {"title": "Rec 1", "text": "Text 1", "id": "REC-A1A1"},
                        {"title": "Rec 2", "text": "Text 2", "id": "REC-A1A2"},
                    ],
                },
                "A1.b": {
                    "review_data": {"review_decision": "achieved"},
                    "recommendations": [],
                },
                "A1.c": {
                    "review_data": {"review_decision": "achieved"},
                    "recommendations": [{"title": "Rec 1", "text": "Text 3", "id": "REC-A1C1"}],
                },
            }
        }
        result = get_recommendations(self.review, "all")

        self.assertEqual(len(result), 2)
        # All results are grouped under other, so the index should be 1
        self.assertEqual(result[0].group_index, 1)
        self.assertEqual(result[0].title, "Rec 1")
        # A1.a and A1.c has the same title, so they are grouped under the same group
        self.assertEqual(result[0].recommendations[0].id, "REC-A1A1")
        self.assertEqual(result[0].recommendations[1].id, "REC-A1C1")
        # Other group, with only 1 record
        self.assertEqual(result[1].group_index, 2)
        self.assertEqual(result[1].title, "Rec 2")
        self.assertEqual(result[1].recommendations[0].id, "REC-A1A2")


class TestGetIndicatorComments(TestCase):
    def test_returns_comments_for_all_categories(self):
        review = Mock(spec=Review)
        review.review_data = {
            "assessor_response_data": {
                "obj1": {
                    "indicator1": {
                        "indicators": {
                            "achieved_1_comment": "Achieved comment 1",
                            "achieved_2_comment": "Achieved comment 2",
                            "partially-achieved_1_comment": "Partial comment",
                            "not-achieved_1_comment": "",
                        }
                    }
                }
            }
        }

        result = get_indicator_comments(review, "obj1", "indicator1")

        self.assertEqual(len(result), 3)
        self.assertIsInstance(result[0], ReviewComment)
        self.assertEqual(result[0].section, "achieved")
        self.assertEqual(result[0].index, 1)
        self.assertEqual(result[0].comment, "Achieved comment 1")

    def test_excludes_empty_comments(self):
        review = Mock(spec=Review)
        review.review_data = {
            "assessor_response_data": {
                "obj1": {
                    "indicator1": {
                        "indicators": {
                            "achieved_1_comment": "Comment 1",
                            "achieved_2_comment": "",
                            "partially-achieved_1_comment": None,
                        }
                    }
                }
            }
        }

        result = get_indicator_comments(review, "obj1", "indicator1")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].comment, "Comment 1")

    def test_returns_empty_list_when_no_comments(self):
        review = Mock(spec=Review)
        review.review_data = {"assessor_response_data": {"obj1": {"indicator1": {"indicators": {}}}}}

        result = get_indicator_comments(review, "obj1", "indicator1")

        self.assertEqual(len(result), 0)


class TestGetPrinciple(TestCase):
    def test_returns_principle_data(self):
        review = Mock(spec=Review)
        principle_data = {"code": "P1", "title": "Principle 1"}
        review.review_data = {"assessor_response_data": {"obj1": {"P1": principle_data}}}

        result = get_principle(review, "obj1", "P1")

        self.assertEqual(result, principle_data)

    def test_returns_correct_principle_from_multiple(self):
        review = Mock(spec=Review)
        review.review_data = {
            "assessor_response_data": {
                "obj1": {
                    "P1": {"code": "P1", "title": "Principle 1"},
                    "P2": {"code": "P2", "title": "Principle 2"},
                }
            }
        }

        result = get_principle(review, "obj1", "P2")

        self.assertEqual(result["code"], "P2")
