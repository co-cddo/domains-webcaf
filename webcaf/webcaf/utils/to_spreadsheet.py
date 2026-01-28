from io import BytesIO

from openpyxl import Workbook

from webcaf.webcaf.caf.util import IndicatorStatusChecker
from webcaf.webcaf.models import Assessment, Review


def export_assessment_to_excel(assessment: Assessment) -> bytes | None:
    if not assessment.is_complete():
        return None

    try:
        review = assessment.reviews.get(status="completed")
    except Review.DoesNotExist:
        return None

    if not review.is_review_complete():
        return None

    wb = Workbook()
    wb.remove(wb.active)

    _add_metadata_tab(wb, assessment)
    _add_indicator_tab(wb, assessment, review)
    _add_outcome_summary_tab(wb, assessment, review)
    _add_recommendations_tab(wb, assessment, review)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def _add_metadata_tab(wb: Workbook, assessment: Assessment):
    ws = wb.create_sheet("Review details")

    review_type_label = dict(Assessment.REVIEW_TYPE_CHOICES).get(assessment.review_type, assessment.review_type)
    framework_label = dict(Assessment.FRAMEWORK_CHOICES).get(assessment.framework, assessment.framework)
    profile_label = dict(Assessment.PROFILE_CHOICES).get(assessment.caf_profile, assessment.caf_profile)

    ws.append(["Organisation:", assessment.system.organisation.name])
    ws.append(["System name:", assessment.system.name])
    ws.append(["Review year:", assessment.assessment_period])
    ws.append(["Review type:", review_type_label])
    ws.append(["CAF version:", framework_label])
    ws.append(["Assigned target CAF profile:", profile_label])


def _add_indicator_tab(wb: Workbook, assessment: Assessment, review: Review):
    ws = wb.create_sheet("IGPs")

    ws.append(
        [
            "Contributing outcome",
            "IGP",
            "IGP wording",
            "Self-assessment",
            "Self-assessment comments",
            "Review",
            "Review comments",
        ]
    )

    review_data = review.get_assessor_response()

    for objective in assessment.get_all_caf_objectives():
        objective_code = objective["code"]

        for principle in objective.get("principles", {}).values():
            for outcome in principle.get("outcomes", {}).values():
                outcome_code = outcome["code"]
                outcome_title = outcome.get("title", "")
                contributing_outcome = f"{outcome_code} {outcome_title}" if outcome_title else outcome_code

                assessment_section = assessment.get_section_by_outcome_id(outcome_code)
                if not assessment_section:
                    continue

                assessment_indicators = assessment_section.get("indicators", {})

                review_outcome = review_data.get(objective_code, {}).get(outcome_code, {})
                review_indicators = review_outcome.get("indicators", {})

                for level in ["achieved", "partially-achieved", "not-achieved"]:
                    level_indicators = outcome.get("indicators", {}).get(level, {})
                    statement_number = 1

                    if level == "achieved":
                        level_display = "Achieved"
                    elif level == "partially-achieved":
                        level_display = "Partially achieved"
                    else:
                        level_display = "Not achieved"

                    for indicator_id, indicator_data in level_indicators.items():
                        indicator_label = f"{outcome_code} {level_display} statement {statement_number}"
                        indicator_text = indicator_data.get("description", "")

                        prefixed_id = f"{level}_{indicator_id}"
                        statement_number += 1

                        self_assessment_value = assessment_indicators.get(prefixed_id, False)
                        self_assessment_comment = assessment_indicators.get(f"{prefixed_id}_comment", "")

                        review_value = review_indicators.get(prefixed_id, "")
                        review_comment = review_indicators.get(f"{prefixed_id}_comment", "")

                        self_assessment_display = "Y" if self_assessment_value else "N"
                        review_display = "Y" if review_value == "yes" else "N"

                        ws.append(
                            [
                                contributing_outcome,
                                indicator_label,
                                indicator_text,
                                self_assessment_display,
                                self_assessment_comment,
                                review_display,
                                review_comment,
                            ]
                        )


def _add_outcome_summary_tab(wb: Workbook, assessment: Assessment, review: Review):
    ws = wb.create_sheet("Contributing outcomes")

    ws.append(
        [
            "Contributing outcome",
            "Target CAF profile requirement",
            "Self-assessment status",
            "Review status",
            "Target CAF profile",
        ]
    )

    review_data = review.get_assessor_response()

    for objective in assessment.get_all_caf_objectives():
        objective_code = objective["code"]

        for principle in objective.get("principles", {}).values():
            for outcome in principle.get("outcomes", {}).values():
                outcome_code = outcome["code"]
                outcome_title = outcome.get("title", "")
                contributing_outcome = f"{outcome_code} {outcome_title}" if outcome_title else outcome_code

                assessment_section = assessment.get_section_by_outcome_id(outcome_code)
                self_assessment_status = ""
                if assessment_section:
                    confirmation = assessment_section.get("confirmation", {})
                    self_assessment_status = confirmation.get("outcome_status", "")

                review_outcome = review_data.get(objective_code, {}).get(outcome_code, {})
                review_decision = review_outcome.get("review_data", {}).get("review_decision", "")

                if review_decision == "achieved":
                    review_status = "Achieved"
                elif review_decision == "partially-achieved":
                    review_status = "Partially achieved"
                elif review_decision == "not-achieved":
                    review_status = "Not achieved"
                else:
                    review_status = ""

                min_profile_requirement = outcome.get("min_profile_requirement", {})
                target_requirement = min_profile_requirement.get(assessment.caf_profile, "")

                principle_id = outcome_code.rsplit(".", 1)[0]
                status_to_check = review_status if review_status else self_assessment_status
                met_status = IndicatorStatusChecker.indicator_min_profile_requirement_met(
                    assessment, principle_id, outcome_code, status_to_check
                )

                ws.append(
                    [
                        contributing_outcome,
                        target_requirement,
                        self_assessment_status,
                        review_status,
                        "Met" if met_status and met_status == "Yes" else met_status,
                    ]
                )


def _add_recommendations_tab(wb: Workbook, assessment: Assessment, review: Review):
    ws = wb.create_sheet("Risks and recommendations")

    ws.append(
        [
            "Recommendation number",
            "Contributing outcome",
            "Target CAF profile",
            "Risk",
            "Recommendation",
        ]
    )

    review_data = review.get_assessor_response()

    for objective in assessment.get_all_caf_objectives():
        objective_code = objective["code"]

        for principle in objective.get("principles", {}).values():
            for outcome in principle.get("outcomes", {}).values():
                recommendation_counter = 1
                outcome_code = outcome["code"]
                outcome_title = outcome.get("title", "")
                contributing_outcome = f"{outcome_code} {outcome_title}" if outcome_title else outcome_code

                assessment_section = assessment.get_section_by_outcome_id(outcome_code)
                self_assessment_status = ""
                if assessment_section:
                    confirmation = assessment_section.get("confirmation", {})
                    self_assessment_status = confirmation.get("outcome_status", "")

                review_outcome = review_data.get(objective_code, {}).get(outcome_code, {})
                review_decision = review_outcome.get("review_data", {}).get("review_decision", "")

                if review_decision == "achieved":
                    review_status = "Achieved"
                elif review_decision == "partially-achieved":
                    review_status = "Partially achieved"
                elif review_decision == "not-achieved":
                    review_status = "Not achieved"
                else:
                    review_status = ""

                principle_id = outcome_code.rsplit(".", 1)[0]
                status_to_check = review_status if review_status else self_assessment_status
                met_status = IndicatorStatusChecker.indicator_min_profile_requirement_met(
                    assessment, principle_id, outcome_code, status_to_check
                )

                recommendations = review.get_outcome_recommendations(objective_code, outcome_code)

                for recommendation in recommendations:
                    ws.append(
                        [
                            f"REC-{outcome_code.replace('.', '').upper()}{recommendation_counter}",
                            contributing_outcome,
                            "Met" if met_status and met_status == "Yes" else met_status,
                            recommendation.get("title", ""),
                            recommendation.get("text", ""),
                        ]
                    )

                    recommendation_counter += 1
