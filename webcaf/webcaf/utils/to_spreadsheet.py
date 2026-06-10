from io import BytesIO
from typing import Any, Literal, cast

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from webcaf.webcaf.caf.util import IndicatorStatusChecker
from webcaf.webcaf.models import Assessment, Review, Tip
from webcaf.webcaf.utils.review import get_review_recommendations

MIN_WIDTH = 20
PADDING = 2


def _add_actioned_tab(wb: Workbook, tip: Tip, context: dict[str, Any]) -> None:
    ws = wb.create_sheet("Actioned recommendations")
    ws.append(
        [
            "Type",
            "Contributing outcome",
            "Associated risk",
            "Reviewer recommendation",
            "Recommendation and risk reviewed",
            "Status",
            "Action",
            "Action owner",
            "Resource available",
            "Budget available",
            "Estimated completion date",
            "Reason for no completion date",
        ]
    )
    _set_header_properties(ws, [10, 20, 50, 50, 10, 30, 50, 20, 20, 20, 20, 50])
    for recommendation_type in ["priority_recommendations", "other_recommendations"]:
        for recommendation, group, action in context.get(recommendation_type, []):
            if action.action_type == "action_planned":
                action_details = action.action_details
                ws.append(
                    [
                        action.recommendation_category.capitalize(),
                        f"{recommendation.outcome} {recommendation.outcome_title}",
                        f"{'RP' if action.recommendation_category == 'priority' else 'RO'}{group.group_index} — {group.title}",
                        recommendation.id + " - " + recommendation.text,
                        action.recommendation_reviewed.capitalize(),
                        "Action planned",
                        action_details.get("action_taken_description", ""),
                        action_details.get("action_owner", ""),
                        action_details.get("resources_available", ""),
                        action_details.get("budget_available", ""),
                        f"{action_details.get('target_day_day', '')}/{action_details.get('target_day_month', '')}/{action_details.get('target_day_year', '')}"
                        if action_details.get("target_date_provided", "no") == "yes"
                        else "No target date",
                        action_details.get("target_date_unavailable_reason", "N/A")
                        if action_details.get("target_date_provided", "yes") == "no"
                        else "N/A",
                    ]
                )
                _wrap_row_text(ws)


def _add_not_actioned_tab(wb: Workbook, tip: Tip, context: dict[str, Any]) -> None:
    ws = wb.create_sheet("Not actioned recommendations")
    ws.append(
        [
            "Type",
            "Contributing outcome",
            "Associated risk",
            "Reviewer recommendation",
            "Recommendation and risk reviewed",
            "Status",
            "Reason for not actioned",
        ]
    )
    _set_header_properties(ws, [10, 20, 50, 50, 10, 30, 50])
    for recommendation_type in ["priority_recommendations", "other_recommendations"]:
        for recommendation, group, action in context.get(recommendation_type, []):
            if action.action_type == "action_not_planned":
                action_details = action.action_details
                ws.append(
                    [
                        action.recommendation_category.capitalize(),
                        f"{recommendation.outcome} {recommendation.outcome_title}",
                        f"{'RP' if action.recommendation_category == 'priority' else 'RO'}{group.group_index} — {group.title}",
                        recommendation.id + " - " + recommendation.text,
                        action.recommendation_reviewed.capitalize(),
                        "No action planned",
                        action_details.get("action_not_planned_reason", "-"),
                    ]
                )
                _wrap_row_text(ws)


def tip_to_excel(tip: Tip, context: dict[str, Any]) -> bytes | None:
    wb = Workbook()
    wb.remove(wb.active)

    ws = _add_metadata_tab(wb, tip.review.assessment)
    ws.append(["Status", "Submitted" if tip.is_submitted else "Draft"])
    _add_actioned_tab(wb, tip, context)
    _add_not_actioned_tab(wb, tip, context)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def review_to_excel(review: Review) -> bytes | None:
    """
    Converts a review object into an Excel workbook represented as a binary stream
    of bytes. The workbook will only be generated if the review is marked as
    complete. The resulting Excel file includes multiple tabs reflecting different
    aspects of the review, such as metadata, indicators, outcome summary, and
    recommendations.

    :param review: The review instance containing the data to be exported into an
        Excel workbook.
    :type review: Review
    :return: A binary stream of the Excel workbook if the review is complete;
        otherwise, None.
    :rtype: bytes | None
    """
    if not review.is_review_complete():
        return None

    wb = Workbook()
    wb.remove(wb.active)

    _add_metadata_tab(wb, review.assessment)
    _add_indicator_tab(wb, review)
    _add_outcome_summary_tab(wb, review)
    _add_recommendations_tab(wb, review)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def _add_metadata_tab(wb: Workbook, assessment: Assessment) -> Worksheet:
    """
    Adds a metadata tab to the given Excel workbook. This function creates a new sheet titled
    "Review details" and appends various metadata about the assessment, such as organization
    details, assessment period, review type, framework, CAF version, and assigned target profile. It
    formats the sheet by setting appropriate column widths.

    :param wb:
        The Excel workbook object where the metadata tab will be added.
    :type wb: Workbook
    :param assessment:
        An object containing assessment information, including organizational data,
        review type, framework, and CAF profile details.
    :type assessment: Assessment
    :return:
        Worksheet
    """
    ws = wb.create_sheet("Review details")

    review_type_label = dict(Assessment.REVIEW_TYPE_CHOICES).get(assessment.review_type, assessment.review_type)
    framework_label = dict(Assessment.FRAMEWORK_CHOICES).get(assessment.framework, assessment.framework)
    profile_label = dict(Assessment.PROFILE_CHOICES).get(assessment.caf_profile, assessment.caf_profile)

    ws.append(["Organisation:", assessment.system.organisation.name])
    ws.append(["System name:", assessment.system.name])
    ws.append(["Review year:", assessment.assessment_period])
    ws.append(["Review type:", review_type_label.title()])
    ws.append(["CAF version:", framework_label])
    ws.append(["Assigned target CAF profile:", profile_label])
    _set_header_properties(ws, [30, 40], fix=False, bold=False)
    return ws


def _add_indicator_tab(wb: Workbook, review: Review):
    """
    Adds a new worksheet named "IGPs" to the provided workbook and populates it
    with indicator data. The data is drawn from the assessment and review objects,
    structuring it to include contributing outcomes, indicator details,
    self-assessment values, and review results.

    This function organizes and writes information about objectives, principles,
    outcomes, and indicators based on their hierarchical structure. It reflects
    the self-assessment values and corresponding reviewer evaluations into a
    tabular format.

    :param wb: An instance of `Workbook` where the "IGPs" worksheet will be added.
    :param review: An instance of `Review` that encapsulates review data used
                   for generating the indicator tab.
    :return: None
    """
    ws = wb.create_sheet("IGPs")
    assessment: Assessment = review.assessment
    ws.append(
        [
            "Contributing outcome",
            "IGP",
            "IGP wording",
            "Self-assessment",
            "Self-assessment comments",
            "Review",
        ]
        + (
            [
                "Review comments",
            ]
            if assessment.review_type != "peer_review"
            else []
        )
    )
    _set_header_properties(ws, [50, 30, 50, 20, 50, 10, 50])

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
                            ]
                            + ([review_comment] if assessment.review_type != "peer_review" else [])
                        )
                        _wrap_row_text(ws)


def _add_outcome_summary_tab(wb: Workbook, review: Review):
    """
    Adds a new sheet titled "Contributing outcomes" to the given workbook and populates
    it with extracted and processed data from the provided review instance. This function
    is used to summarize contributing outcome data based on assessment and review details.

    :param wb: The workbook object where the new sheet will be added.
    :type wb: Workbook
    :param review: The review object containing assessment data, assessor responses, and
        related information required to generate the contributing outcomes data.
    :type review: Review
    :return: None
    """
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
    _set_header_properties(ws, [50, 30, 30, 30, 30])

    assessment: Assessment = review.assessment
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
                _wrap_row_text(ws)


def _add_recommendations_tab(wb: Workbook, review: Review):
    """
    Adds a "Risks and recommendations" tab to the given workbook based on the provided review information.

    A new sheet is created in the workbook, designed to present recommendations associated
    with outcomes, target profiles, risks, and their contributing factors. The method processes
    assessment and review data to populate the sheet with valuable insights.

    :param wb: The workbook to which the "Risks and recommendations" tab will be added.
    :type wb: Workbook
    :param review: An object containing assessment review data, including assessor responses,
        recommendations, and their associated statuses.
    :type review: Review

    :return: None
    """
    ws = wb.create_sheet(
        "Risks and recommendations" if review.assessment.review_type != "peer_review" else "Recommendations"
    )
    ws.append(
        [
            "Contributing outcome",
            "Target CAF profile",
        ]
        + (
            [
                "Risk number",
                "Risk",
            ]
            if review.assessment.review_type != "peer_review"
            else []
        )
        + [
            "Recommendation number",
            "Recommendation",
        ]
    )
    _set_header_properties(ws, [40, 20, 20, 70, 20, 70])

    contributing_outcome_titles = {}
    for objective in review.assessment.get_all_caf_objectives():
        for principle in objective.get("principles", {}).values():
            for outcome in principle.get("outcomes", {}).values():
                outcome_code = outcome["code"]
                outcome_title = outcome.get("title", "")
                contributing_outcome_titles[outcome_code] = (
                    f"{outcome_code} {outcome_title}" if outcome_title else outcome_code
                )

    for recommendation_type, prefix, profile_met in [("priority", "RP", "Not met"), ("normal", "RO", "Met")]:
        recommendation_groups = get_review_recommendations(
            review, cast(Literal["priority", "normal", "all"], recommendation_type)
        )
        for recommendation_group in recommendation_groups:
            for idx, recommendation in enumerate(recommendation_group.recommendations):
                ws.append(
                    [
                        contributing_outcome_titles[recommendation.outcome],
                        profile_met,
                    ]
                    + (
                        [
                            f"{prefix}{recommendation_group.group_index}",
                            recommendation.title,
                        ]
                        if review.assessment.review_type != "peer_review"
                        else []
                    )
                    + [
                        recommendation.id,
                        recommendation.text,
                    ]
                )
                _wrap_row_text(ws)


def _set_header_properties(ws, widths, fix=True, bold=True):
    """
    Sets header properties for the given worksheet. This includes setting column
    widths, applying font styles, text wrapping, and freezing panes above a specified row.

    :param ws: The worksheet object where header properties are to be applied.
    :type ws: openpyxl.worksheet.worksheet.Worksheet
    :param widths: A list of integers representing the column widths to apply to the header cells.
    :type widths: list[int]
    :param fix: Whether to enable text wrapping and freeze panes. Defaults to True.
    :type fix: bool, optional
    :param bold: Whether to apply bold font to the header cells. Defaults to True.
    :type bold: bool, optional
    :return: None
    """
    for cell, width in zip(ws[1], widths):  # row 1
        if bold:
            cell.font = Font(bold=True)
        if fix:
            cell.alignment = Alignment(wrap_text=True)
            #     Freeze everything above A2 - it is always A2 if you want to fix the 1st row
            ws.freeze_panes = "A2"
        col_letter = get_column_letter(cell.column)
        ws.column_dimensions[col_letter].width = max(width, MIN_WIDTH) + PADDING


def _wrap_row_text(ws):
    """
    Adjusts the alignment of cells in the last row of a worksheet to enable text wrapping.
    This is supposed to be used after data is populated into the worksheet for each row.

    This function modifies the alignment of each cell in the last row of the provided worksheet,
    allowing the text within those cells to wrap and fit within the cell boundaries. It determines
    the last row dynamically based on the worksheet's current state.

    :param ws: Worksheet object that needs cell alignment adjustment in its last row.
    :type ws: openpyxl.worksheet.worksheet.Worksheet
    :return: None
    """
    row_num = ws.max_row
    for col in ws.columns:
        ws.cell(row=row_num, column=col[0].column).alignment = Alignment(wrap_text=True)
