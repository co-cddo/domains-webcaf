"""Builds the downloadable Excel assessment template for a CAF framework.

The workbook follows the GovAssure self-assessment and evidence collation
template: a Guidance sheet, then one worksheet per Objective with one row per
indicator of good practice (IGP), grouped by Principle and Contributing
Outcome. A hidden mapping sheet (``JSON_MAP_SHEET_NAME``) records which visible
cell feeds which JSON path so the importer can convert a completed workbook
back into assessment JSON.
"""

import logging
import math
from datetime import datetime
from typing import Any

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

from webcaf.webcaf.utils.excel_importer import (
    JSON_MAP_HEADERS,
    JSON_MAP_SHEET_NAME,
    META_SHEET_NAME,
)

logger = logging.getLogger(__name__)

GUIDANCE_SHEET_NAME = "Guidance"
GUIDANCE_LAST_UPDATED = datetime(2025, 10, 16)

_CAF_VERSIONS = {"caf32": "3.2", "caf40": "4.0"}

_INDICATOR_LEVELS = (
    ("achieved", "Achieved"),
    ("partially-achieved", "Partially achieved"),
    ("not-achieved", "Not achieved"),
)

_OBJECTIVE_HEADERS = (
    "Principle",
    "Contributing outcome",
    "IGP type",
    "IGP",
    "IGP wording",
    "Answer",
    "If applicable, explain alternative controls/exemptions:",
    "Contributing outcome summary (max 1,500 words)\n"
    "The CAF contributing outcome wording is displayed for reference",
)
_OBJECTIVE_COLUMN_WIDTHS = {
    "A": 13.71,
    "B": 22.14,
    "C": 16.14,
    "D": 23.0,
    "E": 62.43,
    "F": 9.57,
    "G": 48.86,
    "H": 72.86,
}
_ANSWER_COLUMN = 6
_ALTERNATIVE_CONTROLS_COLUMN = 7
_SUMMARY_COLUMN = 8
_CHARS_PER_COLUMN_WIDTH_UNIT = 1.1

_HEADER_FILL = PatternFill(start_color="4BACC6", end_color="4BACC6", fill_type="solid")
_BAND_FILLS = (
    PatternFill(start_color="DAEEF3", end_color="DAEEF3", fill_type="solid"),
    PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid"),
)
_IGP_TYPE_COLOURS = {
    "Achieved": ("006100", "C6EFCE"),
    "Partially achieved": ("9C5700", "FFEB9C"),
    "Not achieved": ("9C0006", "FFC7CE"),
}

_GUIDANCE_BLUE_FILL = PatternFill(start_color="4682B4", end_color="4682B4", fill_type="solid")
_GUIDANCE_INTRO = (
    "You can use this spreadsheet to prepare your organisation’s GovAssure self-assessment before "
    "completing it in WebCAF.\n\n"
    "The structure of the spreadsheet matches the format of responses in WebCAF. You should use the "
    "GovAssure stage 3 guidance to support you when preparing your self-assessment.\n\n"
    "This spreadsheet is for use within your organisation. You will not need to share it with GDS. "
    "You can choose to use as much or as little as is helpful to you."
)
_GUIDANCE_INSTRUCTIONS = (
    "There is a separate sheet for each CAF objective. You should scroll to the bottom of the sheet to "
    "see all contributing outcomes.\n\n"
    "For each contributing outcome, you can:\n"
    "- Respond 'Yes' or 'No' to each indicator of good practice (IGP) statement that is true about your "
    "system or organisation\n"
    "- If you have alternative controls in place, or the IGP is not applicable, tick the statement and "
    "explain this alternative control or exemption in the next column\n"
    "- Write a summary for the contributing outcome (1,500 word limit)\n"
    "- List your supporting evidence for the contributing outcome\n\n"
    "Your contributing outcome status is worked out from your IGP responses, in the same way as in WebCAF.\n\n"
    "Note: You will not be asked to list all your supporting evidence in WebCAF. You may choose to do so "
    "here for your own reference and to support your stage 4 reviewer."
)
_GUIDANCE_CONTACT_EMAIL = "cybergovassure@cabinetoffice.gov.uk"


def create_assessment_template_workbook(framework_id: str) -> Workbook:
    """Build the Excel template for the framework with the given id (e.g. ``"caf32"``).

    The framework definition is taken from the already-initialised router
    registry, so the YAML file is not re-read from disk.
    """
    # Imported here rather than at module level: the router registry is only
    # populated once the Django app registry is ready.
    from webcaf.webcaf.frameworks import routers

    return build_assessment_template_workbook(routers[framework_id].framework, framework_id)


def build_assessment_template_workbook(framework: dict[str, Any], framework_id: str | None = None) -> Workbook:
    """Build and return the Excel template workbook for the given framework data."""
    wb = Workbook()
    wb.remove(wb.active)  # remove default sheet
    json_map_rows: list[list[Any]] = [JSON_MAP_HEADERS]

    _write_guidance_sheet(wb.create_sheet(title=GUIDANCE_SHEET_NAME), _CAF_VERSIONS.get(framework_id or ""))

    for obj_code, obj_data in framework["objectives"].items():
        ws = wb.create_sheet(title=f"Objective {obj_code}")
        _write_objective_sheet(ws, obj_data, json_map_rows)

    map_ws = wb.create_sheet(title=JSON_MAP_SHEET_NAME)
    for map_row in json_map_rows:
        map_ws.append(map_row)
    map_ws.sheet_state = "veryHidden"

    if framework_id:
        meta_ws = wb.create_sheet(title=META_SHEET_NAME)
        meta_ws.append(["framework_id", framework_id])
        meta_ws.sheet_state = "veryHidden"

    return wb


def _write_guidance_sheet(ws, caf_version: str | None) -> None:
    """Write the introductory Guidance sheet shown before the objective sheets."""
    ws.column_dimensions["A"].width = 50
    version_suffix = f" - CAF version {caf_version}" if caf_version else ""
    ncsc_label = f"NCSC CAF version {caf_version}:" if caf_version else "NCSC CAF:"

    def heading(row: int, text: str, horizontal: str = "left") -> None:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        cell = ws.cell(row=row, column=1, value=text)
        cell.font = Font(bold=True, size=12, color="FFFFFF")
        cell.fill = _GUIDANCE_BLUE_FILL
        cell.alignment = Alignment(horizontal=horizontal, vertical="top", wrap_text=True)
        cell.border = _border("thin")

    def paragraph(row: int, text: str, height: float) -> None:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        cell = ws.cell(row=row, column=1, value=text)
        cell.font = Font(size=12)
        cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        ws.row_dimensions[row].height = height

    def link(row: int, label: str, target: str) -> None:
        cell = ws.cell(row=row, column=1, value=label)
        cell.font = Font(size=12)
        cell.border = Border(left=Side(style="thin"))
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)
        cell = ws.cell(row=row, column=2, value=target.removeprefix("mailto:"))
        cell.hyperlink = target
        cell.font = Font(size=12, color="0563C1", underline="single")

    heading(1, "OFFICIAL SENSITIVE WHEN COMPLETED", horizontal="center")
    heading(3, f"GovAssure self-assessment and evidence collation template{version_suffix}")
    paragraph(4, _GUIDANCE_INTRO, 99.95)

    heading(6, "Supporting resources")
    link(
        7,
        "Stage 3 self-assessment guidance:",
        "https://www.security.gov.uk/policy-and-guidance/govassure/stage-3-self-assessment/",
    )
    link(8, ncsc_label, "https://www.ncsc.gov.uk/collection/cyber-assessment-framework/changelog")
    link(9, "WebCAF:", "https://webcaf.service.security.gov.uk/")

    heading(11, "To use the spreadsheet:")
    paragraph(12, _GUIDANCE_INSTRUCTIONS, 198.75)

    heading(14, "For questions or support:")
    link(15, "Please contact", f"mailto:{_GUIDANCE_CONTACT_EMAIL}")

    heading(17, "Last updated:")
    cell = ws.cell(row=18, column=1, value=GUIDANCE_LAST_UPDATED)
    cell.font = Font(size=12)
    cell.number_format = "dd/mm/yyyy"
    cell.alignment = Alignment(horizontal="left")


def _write_objective_sheet(ws, obj_data: dict[str, Any], json_map_rows: list[list[Any]]) -> None:
    """Write one row per IGP for every contributing outcome in the objective."""
    border = _border("hair")
    for col, width in _OBJECTIVE_COLUMN_WIDTHS.items():
        ws.column_dimensions[col].width = width

    for col_idx, title in enumerate(_OBJECTIVE_HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=title)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        cell.border = border
    ws.row_dimensions[1].height = _row_height(_OBJECTIVE_HEADERS)

    row = 2
    outcome_index = 0
    for principle_data in obj_data.get("principles", {}).values():
        principle_label = f"{principle_data['code']} {principle_data['title']}"
        for outcome_data in principle_data.get("outcomes", {}).values():
            row = _write_outcome_rows(
                ws, principle_label, outcome_data, row, _BAND_FILLS[outcome_index % 2], border, json_map_rows
            )
            outcome_index += 1
    last_row = row - 1

    answer_validator = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True)
    ws.add_data_validation(answer_validator)
    answer_validator.add(f"F2:F{last_row}")

    for label, (font_colour, fill_colour) in _IGP_TYPE_COLOURS.items():
        ws.conditional_formatting.add(
            f"C2:C{last_row}",
            CellIsRule(
                operator="equal",
                formula=[f'"{label}"'],
                font=Font(color=font_colour),
                fill=PatternFill(bgColor=fill_colour),
            ),
        )

    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:H{last_row}"


def _write_outcome_rows(
    ws,
    principle_label: str,
    outcome_data: dict[str, Any],
    row: int,
    fill: PatternFill,
    border: Border,
    json_map_rows: list[list[Any]],
) -> int:
    """Write the IGP rows for one contributing outcome; return the next free row."""
    outcome_code = outcome_data["code"]
    outcome_label = f"{outcome_code} - {outcome_data['title']}"
    first_row = row

    igp_rows: list[tuple[str, str, str, str]] = []
    for level, level_label in _INDICATOR_LEVELS:
        items = outcome_data.get("indicators", {}).get(level) or {}
        for number, (item_code, item_data) in enumerate(items.items(), start=1):
            igp_rows.append(
                (f"{level}_{item_code}", level_label, f"{level_label} statement {number}", item_data["description"])
            )

    for indicator_key, level_label, statement, wording in igp_rows:
        values = (principle_label, outcome_label, level_label, statement, wording, None, None)
        for col_idx, value in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col_idx, value=value)
            cell.fill = fill
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = border
        ws.row_dimensions[row].height = _row_height(values)

        _append_json_map(
            json_map_rows,
            ws,
            ws.cell(row=row, column=_ANSWER_COLUMN).coordinate,
            f"/{outcome_code}/indicators/{indicator_key}",
            "indicator_answer",
        )
        _append_json_map(
            json_map_rows,
            ws,
            ws.cell(row=row, column=_ALTERNATIVE_CONTROLS_COLUMN).coordinate,
            f"/{outcome_code}/indicators/{indicator_key}_comment",
            "text",
        )
        row += 1

    if not igp_rows:
        for col_idx, value in enumerate((principle_label, outcome_label), start=1):
            cell = ws.cell(row=row, column=col_idx, value=value)
            cell.fill = fill
            cell.border = border
        row += 1

    last_row = row - 1
    summary = outcome_data.get("description") or ""
    for merged_row in range(first_row, row):
        cell = ws.cell(row=merged_row, column=_SUMMARY_COLUMN)
        cell.fill = fill
        cell.border = border
    if last_row > first_row:
        ws.merge_cells(start_row=first_row, start_column=_SUMMARY_COLUMN, end_row=last_row, end_column=_SUMMARY_COLUMN)
    cell = ws.cell(row=first_row, column=_SUMMARY_COLUMN, value=summary or None)
    cell.alignment = Alignment(vertical="top", wrap_text=True)
    _append_json_map(
        json_map_rows,
        ws,
        cell.coordinate,
        f"/{outcome_code}/confirmation/confirm_outcome_confirm_comment",
        "text",
        placeholder=summary,
    )

    summary_height = _row_height([None] * (_SUMMARY_COLUMN - 1) + [summary])
    outcome_height = sum(ws.row_dimensions[r].height or 0 for r in range(first_row, row))
    if summary_height > outcome_height:
        ws.row_dimensions[last_row].height = (ws.row_dimensions[last_row].height or 0) + summary_height - outcome_height

    return row


def _row_height(values) -> float:
    """Estimate the height of a wrapped row, as openpyxl cannot auto-fit rows."""
    lines = 1
    for col_idx, value in enumerate(values, start=1):
        if not value:
            continue
        chars_per_line = max(
            1, int(_OBJECTIVE_COLUMN_WIDTHS[chr(ord("A") + col_idx - 1)] * _CHARS_PER_COLUMN_WIDTH_UNIT)
        )
        lines = max(lines, sum(math.ceil(max(len(part), 1) / chars_per_line) for part in str(value).split("\n")))
    return round(lines * 14.5 + 0.1, 2)


def _border(style: str) -> Border:
    side = Side(border_style=style, color="000000")
    return Border(left=side, right=side, top=side, bottom=side)


def _append_json_map(
    json_map_rows: list[list[Any]],
    ws,
    cell_coordinate: str,
    json_path: str,
    value_type: str,
    required: bool = False,
    placeholder: str = "",
) -> None:
    json_map_rows.append([ws.title, cell_coordinate, json_path, value_type, required, placeholder or None])
