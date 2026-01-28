from io import BytesIO

from openpyxl import Workbook

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
    ws = wb.create_sheet("Metadata")

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
    ws = wb.create_sheet("Indicator Level")

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

                for level in ["not-achieved", "partially-achieved", "achieved"]:
                    level_indicators = outcome.get("indicators", {}).get(level, {})
                    for indicator_id, indicator_data in level_indicators.items():
                        indicator_label = (
                            f"{outcome_code} {level.replace('-', ' ').title()} statement {indicator_id.split('.')[-1]}"
                        )
                        indicator_text = indicator_data.get("description", "")

                        prefixed_id = f"{level}_{indicator_id}"

                        self_assessment_value = assessment_indicators.get(prefixed_id, False)
                        self_assessment_comment = assessment_indicators.get(f"{prefixed_id}_comment", "")

                        review_value = review_indicators.get(prefixed_id, "")
                        review_comment = review_indicators.get(f"{prefixed_id}_comment", "")

                        ws.append(
                            [
                                contributing_outcome,
                                indicator_label,
                                indicator_text,
                                str(self_assessment_value).lower(),
                                self_assessment_comment,
                                review_value,
                                review_comment,
                            ]
                        )


def _add_outcome_summary_tab(wb: Workbook, assessment: Assessment, review: Review):
    ws = wb.create_sheet("Outcome Summary")

    ws.append(
        [
            "Contributing outcome",
            "Target CAF profile",
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
                review_status = review_decision.replace("-", " ").title() if review_decision else ""

                ws.append(
                    [
                        contributing_outcome,
                        self_assessment_status,
                        self_assessment_status,
                        review_status,
                        "",
                    ]
                )


def _add_recommendations_tab(wb: Workbook, assessment: Assessment, review: Review):
    ws = wb.create_sheet("Recommendations")

    ws.append(
        [
            "Recommendation number",
            "Contributing outcome",
            "Target CAF profile",
            "Risk",
            "Recommendation",
        ]
    )

    recommendation_counter = 1

    for objective in assessment.get_all_caf_objectives():
        objective_code = objective["code"]

        for principle in objective.get("principles", {}).values():
            for outcome in principle.get("outcomes", {}).values():
                outcome_code = outcome["code"]
                outcome_title = outcome.get("title", "")
                contributing_outcome = f"{outcome_code} {outcome_title}" if outcome_title else outcome_code

                recommendations = review.get_outcome_recommendations(objective_code, outcome_code)

                for recommendation in recommendations:
                    ws.append(
                        [
                            recommendation_counter,
                            contributing_outcome,
                            "",
                            recommendation.get("title", ""),
                            recommendation.get("text", ""),
                        ]
                    )

                    recommendation_counter += 1
