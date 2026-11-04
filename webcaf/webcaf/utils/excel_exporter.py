"""Builds the downloadable Excel assessment template for a CAF framework.

The workbook follows the "Prepare your GovAssure self-assessment and evidence"
template: an Index sheet linking to every visible sheet, an "About this
document" sheet, then for each Objective a worksheet with one row per
indicator of good practice (IGP), grouped by Principle and Contributing
Outcome, followed by an evidence sheet, and finally a very hidden Lists sheet
feeding the evidence sheets' contributing outcome dropdowns. Unless disabled,
a hidden mapping sheet (``JSON_MAP_SHEET_NAME``) records which visible cell
feeds which JSON path so the importer can convert a completed workbook back
into assessment JSON.

On each Objective sheet the IGP columns (A:G) form an Excel table, while the
contributing outcome status and summary columns (H and I) sit just outside it:
each is merged down the outcome's rows, and Excel tables cannot contain merged
cells. Everything beyond column I and below the last row is hidden.
"""

import logging
import textwrap
from typing import Any

from openpyxl import Workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.dimensions import ColumnDimension
from openpyxl.worksheet.filters import AutoFilter
from openpyxl.worksheet.hyperlink import Hyperlink
from openpyxl.worksheet.table import Table, TableColumn, TableStyleInfo

from webcaf.webcaf.utils.excel_importer import (
    JSON_MAP_HEADERS,
    JSON_MAP_SHEET_NAME,
    META_SHEET_NAME,
)

logger = logging.getLogger(__name__)

INDEX_SHEET_NAME = "Index"
ABOUT_SHEET_NAME = "About this document"
LISTS_SHEET_NAME = "Lists"
INDEX_TABLE_NAME = "SheetIndex"

_CAF_VERSIONS = {"caf32": "3.2", "caf40": "4.0"}
_TEMPLATE_FILENAME_STEM = "Prepare-your-GovAssure-self-assessment-and-evidence"

_INDICATOR_LEVELS = (
    ("achieved", "Achieved"),
    ("partially-achieved", "Partially achieved"),
    ("not-achieved", "Not achieved"),
)

_OBJECTIVE_HEADERS = (
    "Principle",
    "Contributing outcome",
    "Type of indicator of good practice (IGP)",
    "IGP reference",
    "IGP wording",
    "Answer (yes or no)",
    "If applicable, explain alternative controls or exemptions (up to 500 words):",
    "Contributing outcome status",
    "Contributing outcome summary (max 1,500 words)\n"
    "The CAF contributing outcome wording is displayed for reference",
)
_OBJECTIVE_COLUMN_WIDTHS = {
    "A": 13.71,
    "B": 22.14,
    "C": 24.0,
    "D": 23.0,
    "E": 62.43,
    "F": 12.0,
    "G": 48.86,
    "H": 22.14,
    "I": 72.86,
}
_ANSWER_COLUMN = 6
_ALTERNATIVE_CONTROLS_COLUMN = 7
_OUTCOME_COLUMN = 8
_SUMMARY_COLUMN = 9
_OBJECTIVE_TABLE_LAST_COLUMN = _ALTERNATIVE_CONTROLS_COLUMN
_MAX_COLUMN = 16384
# Errs slightly generous so wrapped text is not cut off; checked against the
# GovAssure template's hand-sized rows.
_CHARS_PER_COLUMN_WIDTH_UNIT = 1.05
# Row heights (points) the GovAssure template uses for 1-6 lines of wrapped text
# at the base font size; other font sizes are scaled from these.
_LINE_HEIGHTS = (14.45, 29.1, 43.5, 57.95, 72.6, 87.0)
_LINE_HEIGHT = 14.5
_BASE_FONT_SIZE = 11
_HEADER_FONT_SIZE = 14
_BODY_FONT_SIZE = 12
_OBJECTIVE_DEFAULT_ROW_HEIGHT = 14.45

_HEADER_FILL = PatternFill(start_color="225E6D", end_color="225E6D", fill_type="solid")
_BAND_FILLS = (
    PatternFill(start_color="DAEEF3", end_color="DAEEF3", fill_type="solid"),
    PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid"),
)
_IGP_TYPE_COLOURS = {
    "Achieved": ("225214", "C6EFCE"),
    "Partially achieved": ("694316", "FFEB9C"),
    "Not achieved": ("771813", "FFC7CE"),
}

_TABLE_STYLE = TableStyleInfo(
    name="TableStyleMedium2",
    showFirstColumn=False,
    showLastColumn=False,
    showRowStripes=False,
    showColumnStripes=False,
)

_LINK_COLOUR = "0000FF"
_FRONT_COLUMN_WIDTH = 75.0
_INDEX_HEADER_FILL = PatternFill(start_color="000000", end_color="000000", fill_type="solid")
_INDEX_INTRO = (
    "Welcome to the Prepare your GovAssure self-assessment and evidence spreadsheet "
    "(Cyber Assessment Framework (CAF){version}).\n"
    "This worksheet is the index you can use to navigate to individual sheets.\n"
    "Index begins in cell A2.\n"
    "Rows and columns outside of the tables are hidden to prevent accidental navigation."
)
_ABOUT_TITLE_FILL = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
_ABOUT_HEADING_FILL = PatternFill(start_color="C5D9F1", end_color="C5D9F1", fill_type="solid")
_ABOUT_TITLE = "Prepare your GovAssure self-assessment and evidence{version}"
_ABOUT_GUIDANCE_LINK = (
    "https://www.security.gov.uk/policy-and-guidance/govassure/stage-3-self-assessment/"
    "prepare-your-GovAssure-self-assessment-and-evidence"
)

_MIRROR_ANSWER_PROMPT = "Answer the identical 'Achieved' statement"

_EVIDENCE_HEADERS = (
    "Contributing outcome",
    "Evidence name",
    "Notes",
    "Relevant indicators of good practice (IGPs)",
    "Hyperlink to evidence",
)
_EVIDENCE_COLUMN_WIDTHS = {"A": 30.0, "B": 45.0, "C": 55.0, "D": 45.0, "E": 55.0}
_EVIDENCE_ROWS = 200
_EVIDENCE_BORDER = Border(left=Side(style="hair", color="000000"), top=Side(style="hair", color="000000"))

_LISTS_COLUMN_WIDTHS = (30.0, 53.71, 42.86, 39.86)
_LISTS_FIRST_ROW = 4


def assessment_template_filename(framework_id: str | None) -> str:
    """File name for the downloaded template, e.g.
    ``Prepare-your-GovAssure-self-assessment-and-evidence-CAF-v4.0.xlsx``.

    A framework without a known CAF version is named after its id instead.
    """
    caf_version = _CAF_VERSIONS.get(framework_id or "")
    if caf_version:
        suffix = f"-CAF-v{caf_version}"
    else:
        suffix = f"-{framework_id}" if framework_id else ""
    return f"{_TEMPLATE_FILENAME_STEM}{suffix}.xlsx"


def create_assessment_template_workbook(framework_id: str) -> Workbook:
    """Build the Excel template for the framework with the given id (e.g. ``"caf32"``).

    The framework definition is taken from the already-initialised router
    registry, so the YAML file is not re-read from disk.
    """
    # Imported here rather than at module level: the router registry is only
    # populated once the Django app registry is ready.
    from webcaf.webcaf.frameworks import routers

    return build_assessment_template_workbook(routers[framework_id].framework, framework_id)


def build_assessment_template_workbook(
    framework: dict[str, Any], framework_id: str | None = None, include_json_map: bool = True
) -> Workbook:
    """Build and return the Excel template workbook for the given framework data.

    With ``include_json_map=False`` the hidden mapping and metadata sheets are
    left out, giving a standalone workbook that cannot be imported back.

    The framework's ``assessment-rules`` are written into each Outcome formula,
    so the workbook follows whatever rules the framework defines.
    """
    wb = Workbook()
    wb.remove(wb.active)  # remove default sheet
    json_map_rows: list[list[Any]] = [JSON_MAP_HEADERS]
    caf_version = _CAF_VERSIONS.get(framework_id or "")

    index_ws = wb.create_sheet(title=INDEX_SHEET_NAME)
    _write_about_sheet(wb.create_sheet(title=ABOUT_SHEET_NAME), caf_version)

    assessment_rules = framework.get("assessment-rules") or {}
    for obj_code, obj_data in framework["objectives"].items():
        ws = wb.create_sheet(title=f"Objective {obj_code}")
        _write_objective_sheet(ws, obj_code, obj_data, json_map_rows, assessment_rules)
        _write_evidence_sheet(wb.create_sheet(title=f"Objective {obj_code} evidence"), obj_code)

    # Written last so it links to every visible sheet; it stays the first sheet.
    _write_index_sheet(index_ws, [ws.title for ws in wb.worksheets if ws is not index_ws], caf_version)

    _write_lists_sheet(wb, wb.create_sheet(title=LISTS_SHEET_NAME), framework)

    if not include_json_map:
        return wb

    map_ws = wb.create_sheet(title=JSON_MAP_SHEET_NAME)
    for map_row in json_map_rows:
        map_ws.append(map_row)
    map_ws.sheet_state = "veryHidden"

    if framework_id:
        meta_ws = wb.create_sheet(title=META_SHEET_NAME)
        meta_ws.append(["framework_id", framework_id])
        meta_ws.sheet_state = "veryHidden"

    return wb


def _write_index_sheet(ws, sheet_titles: list[str], caf_version: str | None) -> None:
    """Write the Index sheet: an intro, then a one-column table of links to the given sheets."""
    ws.column_dimensions["A"].width = _FRONT_COLUMN_WIDTH
    ws.sheet_view.showGridLines = False
    widths = {"A": _FRONT_COLUMN_WIDTH}

    intro = _INDEX_INTRO.format(version=f" version {caf_version}" if caf_version else "")
    cell = ws.cell(row=1, column=1, value=intro)
    cell.font = Font(size=_BODY_FONT_SIZE)
    cell.alignment = Alignment(vertical="top", wrap_text=True)
    ws.row_dimensions[1].height = _row_height([intro], _BODY_FONT_SIZE, widths)

    header = ws.cell(row=2, column=1, value="Index")
    header.font = Font(bold=True, size=_HEADER_FONT_SIZE, color="FFFFFF")
    header.fill = _INDEX_HEADER_FILL
    ws.row_dimensions[2].height = _row_height([header.value], _HEADER_FONT_SIZE, widths)

    row = 3
    for title in sheet_titles:
        cell = ws.cell(row=row, column=1, value=title)
        cell.hyperlink = Hyperlink(ref=cell.coordinate, location=f"'{title}'!A1", display=title)
        cell.font = Font(size=_BODY_FONT_SIZE, color=_LINK_COLOUR, underline="single")
        ws.row_dimensions[row].height = _row_height([title], _BODY_FONT_SIZE, widths)
        row += 1
    last_row = row - 1

    _add_table(ws, INDEX_TABLE_NAME, f"A2:A{last_row}", (header.value,))
    _hide_outside_table(ws, last_column=1)


def _write_about_sheet(ws, caf_version: str | None) -> None:
    """Write the "About this document" sheet shown before the objective sheets."""
    ws.column_dimensions["A"].width = _FRONT_COLUMN_WIDTH
    ws.sheet_view.showGridLines = False
    widths = {"A": _FRONT_COLUMN_WIDTH}

    def write(row: int, text: str, font: Font, fill: PatternFill | None = None) -> None:
        cell = ws.cell(row=row, column=1, value=text)
        cell.font = font
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        if fill:
            cell.fill = fill
        ws.row_dimensions[row].height = _row_height([text], font.size, widths)

    heading_font = Font(bold=True, size=_HEADER_FONT_SIZE, color="000000")
    body_font = Font(size=_BODY_FONT_SIZE)

    title = _ABOUT_TITLE.format(version=f" (CAF version {caf_version})" if caf_version else "")
    write(1, title, Font(bold=True, size=16, color="FFFFFF"), _ABOUT_TITLE_FILL)
    write(2, "System being assessed", heading_font, _ABOUT_HEADING_FILL)
    write(3, "Enter the name of the system", body_font)
    write(4, "Guidance on using this document", heading_font, _ABOUT_HEADING_FILL)
    write(
        5,
        "Prepare your GovAssure self-assessment and evidence",
        Font(size=_BODY_FONT_SIZE, color=_LINK_COLOUR, underline="single"),
    )
    ws["A5"].hyperlink = _ABOUT_GUIDANCE_LINK
    write(6, "You must mark this document OFFICIAL-SENSITIVE.", body_font)

    _hide_outside_table(ws, last_column=1)


def _contributing_outcomes_list_name(obj_code: str) -> str:
    return f"Objective_{obj_code}_COs"


def _write_evidence_sheet(ws, obj_code: str) -> None:
    """Write an empty evidence sheet whose contributing outcome column offers a dropdown
    of the objective's contributing outcomes (from the Lists sheet)."""
    for col, width in _EVIDENCE_COLUMN_WIDTHS.items():
        ws.column_dimensions[col].width = width
    ws.sheet_format.defaultRowHeight = _OBJECTIVE_DEFAULT_ROW_HEIGHT

    for col_idx, title in enumerate(_EVIDENCE_HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=title)
        cell.font = Font(bold=True, size=_HEADER_FONT_SIZE, color="FFFFFF")
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        cell.border = _EVIDENCE_BORDER
    ws.row_dimensions[1].height = _row_height(_EVIDENCE_HEADERS, _HEADER_FONT_SIZE, _EVIDENCE_COLUMN_WIDTHS)

    last_row = _EVIDENCE_ROWS + 1
    for row in range(2, last_row + 1):
        for col_idx in range(1, len(_EVIDENCE_HEADERS) + 1):
            cell = ws.cell(row=row, column=col_idx)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = _EVIDENCE_BORDER

    # As in the GovAssure template, the prompt and error messages are defined but switched
    # off, so the dropdown suggests values without rejecting others.
    outcome_validator = DataValidation(
        type="list",
        formula1=_contributing_outcomes_list_name(obj_code),
        allow_blank=True,
        showInputMessage=False,
        showErrorMessage=False,
        prompt="Select the contributing outcome this evidence relates to.",
        error="Select a contributing outcome from the list.",
    )
    ws.add_data_validation(outcome_validator)
    outcome_validator.add(f"A2:A{last_row}")

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:D{last_row}"


def _write_lists_sheet(wb: Workbook, ws, framework: dict[str, Any]) -> None:
    """Write one column of contributing outcomes per objective and name each column's
    range so the evidence sheets' dropdowns can refer to it.

    The sheet is very hidden (it cannot be unhidden from Excel's menus) so the lists
    cannot be changed or deleted by accident; the named ranges still work.
    """
    ws.sheet_state = "veryHidden"
    ws.sheet_format.defaultRowHeight = _OBJECTIVE_DEFAULT_ROW_HEIGHT
    ws.cell(
        row=1,
        column=1,
        value="Contributing outcome lists used for the dropdowns on the evidence sheets. Do not delete this sheet.",
    ).font = Font(bold=True, size=11)

    for col_idx, (obj_code, obj_data) in enumerate(framework["objectives"].items(), start=1):
        column = get_column_letter(col_idx)
        ws.column_dimensions[column].width = (
            _LISTS_COLUMN_WIDTHS[col_idx - 1] if col_idx <= len(_LISTS_COLUMN_WIDTHS) else _LISTS_COLUMN_WIDTHS[0]
        )
        ws.cell(row=_LISTS_FIRST_ROW - 1, column=col_idx, value=f"Objective {obj_code}").font = Font(bold=True, size=11)
        row = _LISTS_FIRST_ROW
        for principle_data in obj_data.get("principles", {}).values():
            for outcome_data in principle_data.get("outcomes", {}).values():
                ws.cell(row=row, column=col_idx, value=f"{outcome_data['code']} - {outcome_data['title']}")
                row += 1
        if row > _LISTS_FIRST_ROW:
            name = _contributing_outcomes_list_name(obj_code)
            wb.defined_names[name] = DefinedName(
                name, attr_text=f"{ws.title}!${column}${_LISTS_FIRST_ROW}:${column}${row - 1}"
            )


def _write_objective_sheet(
    ws, obj_code: str, obj_data: dict[str, Any], json_map_rows: list[list[Any]], assessment_rules: dict[str, Any]
) -> None:
    """Write one row per IGP for every contributing outcome in the objective.

    Columns A:G form an Excel table named after the objective (e.g. ``ObjectiveA``);
    the status and summary columns (H and I) are merged per outcome, so they are
    styled like the table but kept outside it.
    """
    border = _border("hair")
    for col, width in _OBJECTIVE_COLUMN_WIDTHS.items():
        ws.column_dimensions[col].width = width
    ws.sheet_format.defaultRowHeight = _OBJECTIVE_DEFAULT_ROW_HEIGHT
    ws.sheet_format.customHeight = True

    for col_idx, title in enumerate(_OBJECTIVE_HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=title)
        cell.font = Font(bold=True, size=_HEADER_FONT_SIZE, color="FFFFFF")
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        cell.border = border
    ws.row_dimensions[1].height = _row_height(_OBJECTIVE_HEADERS, _HEADER_FONT_SIZE)

    row = 2
    outcome_index = 0
    for principle_data in obj_data.get("principles", {}).values():
        principle_label = f"{principle_data['code']} {principle_data['title']}"
        for outcome_data in principle_data.get("outcomes", {}).values():
            row = _write_outcome_rows(
                ws,
                principle_label,
                outcome_data,
                row,
                _BAND_FILLS[outcome_index % 2],
                border,
                json_map_rows,
                assessment_rules,
            )
            outcome_index += 1
    last_row = row - 1

    answer_validator = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True)
    ws.add_data_validation(answer_validator)
    answer_validator.add(f"F2:F{last_row}")

    for column in ("C", get_column_letter(_OUTCOME_COLUMN)):
        for label, (font_colour, fill_colour) in _IGP_TYPE_COLOURS.items():
            ws.conditional_formatting.add(
                f"{column}2:{column}{last_row}",
                CellIsRule(
                    operator="equal",
                    formula=[f'"{label}"'],
                    font=Font(color=font_colour),
                    fill=PatternFill(bgColor=fill_colour),
                ),
            )

    ws.freeze_panes = "C2"
    # The table brings its own filter, so no sheet-level auto filter is set.
    _add_table(
        ws,
        f"Objective{obj_code}",
        f"A1:{get_column_letter(_OBJECTIVE_TABLE_LAST_COLUMN)}{last_row}",
        _OBJECTIVE_HEADERS[:_OBJECTIVE_TABLE_LAST_COLUMN],
    )
    _hide_outside_table(ws, last_column=_SUMMARY_COLUMN)
    _lock_computed_cells(ws)


def _lock_computed_cells(ws) -> None:
    """Protect the sheet so only computed cells are read-only: the Outcome column and
    the answers of partially achieved statements that mirror an achieved one.

    Protection locks every cell by default, so every other cell is unlocked,
    including the empty rows below the table. The Outcome formulas are also hidden
    from the formula bar, so only the status shows. Filtering and resizing stay allowed.

    No password is set, so users can lift the protection themselves from Excel's
    Review > Unprotect Sheet if they need to.
    """
    unlocked = Protection(locked=False)
    locked_and_hidden = Protection(locked=True, hidden=True)
    outcome_column = get_column_letter(_OUTCOME_COLUMN)
    for col_idx in range(1, _SUMMARY_COLUMN + 1):
        column = get_column_letter(col_idx)
        if column != outcome_column:
            ws.column_dimensions[column].protection = unlocked
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell, MergedCell):
                continue
            if cell.column_letter == outcome_column and cell.data_type == "f":
                cell.protection = locked_and_hidden
            elif cell.column_letter != outcome_column and cell.data_type != "f":
                cell.protection = unlocked

    ws.protection.sheet = True
    ws.protection.autoFilter = False
    ws.protection.formatColumns = False
    ws.protection.formatRows = False


def _add_table(ws, name: str, ref: str, headers: tuple[str, ...]) -> None:
    """Make ``ref`` an Excel table with a header row and no banding.

    The column names are set explicitly from the headers; openpyxl escapes any
    line feed in them as ``_x000a_``, which is how Excel stores it. The range
    must not contain merged cells, or Excel reports the file as corrupt: this is
    why the objective sheets' merged status and summary columns stay outside
    their table.
    """
    table = Table(
        displayName=name,
        ref=ref,
        autoFilter=AutoFilter(ref=ref),
        tableColumns=[TableColumn(id=col_idx, name=header) for col_idx, header in enumerate(headers, start=1)],
        tableStyleInfo=_TABLE_STYLE,
    )
    ws.add_table(table)


def _hide_outside_table(ws, last_column: int) -> None:
    """Hide every column after ``last_column`` (the last column holding data, which
    may lie outside the table) and every row without an explicit height.

    With ``zeroHeight`` set, Excel hides all rows that have no height of their own,
    so every row down to the last data row must have been given one.
    """
    first_hidden = get_column_letter(last_column + 1)
    ws.column_dimensions[first_hidden] = ColumnDimension(
        ws, index=first_hidden, min=last_column + 1, max=_MAX_COLUMN, hidden=True
    )
    ws.sheet_format.zeroHeight = True


def _write_outcome_rows(
    ws,
    principle_label: str,
    outcome_data: dict[str, Any],
    row: int,
    fill: PatternFill,
    border: Border,
    json_map_rows: list[list[Any]],
    assessment_rules: dict[str, Any],
) -> int:
    """Write the IGP rows for one contributing outcome; return the next free row.

    The status formula and the contributing outcome summary each occupy one cell
    merged down all of the outcome's rows, anchored at its first row (the cell the
    JSON map points to).
    """
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

    # Some partially achieved statements repeat an achieved statement word for
    # word. Meeting the achieved statement also meets the partially achieved one,
    # so the mirror copies the achieved statement's answer.
    achieved_rows: dict[str, int] = {}
    level_rows: dict[str, list[int]] = {level_label: [] for _, level_label in _INDICATOR_LEVELS}
    for indicator_key, level_label, statement, wording in igp_rows:
        level_rows[level_label].append(row)
        normalised_wording = " ".join(wording.split())
        if level_label == "Achieved":
            achieved_rows[normalised_wording] = row
        mirrored_row = achieved_rows.get(normalised_wording) if level_label == "Partially achieved" else None
        answer_cell = ws.cell(row=mirrored_row or row, column=_ANSWER_COLUMN).coordinate
        answer = _mirror_answer_formula(answer_cell) if mirrored_row else None

        values = (principle_label, outcome_label, level_label, statement, wording, answer, None)
        for col_idx, value in enumerate(values, start=1):
            _style_body_cell(ws.cell(row=row, column=col_idx, value=value), fill, border)
        # A mirror row must be tall enough to show the prompt in the narrow answer column
        height_values = values[: _ANSWER_COLUMN - 1] + ((_MIRROR_ANSWER_PROMPT,) if mirrored_row else ())
        ws.row_dimensions[row].height = _row_height(height_values, _BODY_FONT_SIZE)

        # A mirror's answer is read from its achieved statement, as the mirror cell
        # shows a prompt rather than an answer until that statement is answered.
        _append_json_map(
            json_map_rows,
            ws,
            answer_cell,
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
        labels = (principle_label, outcome_label)
        for col_idx, value in enumerate(labels, start=1):
            _style_body_cell(ws.cell(row=row, column=col_idx, value=value), fill, border)
        ws.row_dimensions[row].height = _row_height(labels, _BODY_FONT_SIZE)
        row += 1

    last_row = row - 1
    summary = outcome_data.get("description") or ""

    for column in (_OUTCOME_COLUMN, _SUMMARY_COLUMN):
        for outcome_row in range(first_row, row):
            _style_body_cell(ws.cell(row=outcome_row, column=column), fill, border)
        if last_row > first_row:
            ws.merge_cells(start_row=first_row, start_column=column, end_row=last_row, end_column=column)
    if igp_rows and assessment_rules:
        ws.cell(
            row=first_row,
            column=_OUTCOME_COLUMN,
            value=_outcome_status_formula(first_row, last_row, level_rows, assessment_rules),
        )
    cell = ws.cell(row=first_row, column=_SUMMARY_COLUMN, value=summary or None)
    _append_json_map(
        json_map_rows,
        ws,
        cell.coordinate,
        f"/{outcome_code}/confirmation/confirm_outcome_confirm_comment",
        "text",
        placeholder=summary,
    )

    summary_height = _row_height([None] * (_SUMMARY_COLUMN - 1) + [summary], _BODY_FONT_SIZE)
    outcome_height = sum(ws.row_dimensions[r].height or 0 for r in range(first_row, row))
    if summary_height > outcome_height:
        ws.row_dimensions[last_row].height = (ws.row_dimensions[last_row].height or 0) + summary_height - outcome_height

    return row


def _style_body_cell(cell, fill: PatternFill, border: Border) -> None:
    cell.font = Font(size=_BODY_FONT_SIZE)
    cell.fill = fill
    cell.alignment = Alignment(vertical="top", wrap_text=True)
    cell.border = border


def _mirror_answer_formula(achieved_answer_cell: str) -> str:
    """Excel formula giving the same answer as the mirrored achieved statement, or a prompt
    to answer that statement while it is blank."""
    return f'=IF({achieved_answer_cell}="","{_MIRROR_ANSWER_PROMPT}",{achieved_answer_cell})'


def _outcome_status_formula(
    first_row: int, last_row: int, level_rows: dict[str, list[int]], assessment_rules: dict[str, Any]
) -> str:
    """Excel formula looking up the contributing outcome status in the framework's assessment rules.

    The rules are embedded in the formula as an array constant, so the workbook
    needs no extra (hidden) sheet.

    Builds the same rule key as ``IndicatorStatusChecker.get_status_for_indicators``
    (e.g. ``all_none_some``): for each IGP level, ``all`` if every statement is
    answered Yes, ``none`` if none are (or the level has no statements), and
    ``some`` otherwise. The status stays blank until every statement in the
    outcome has been answered Yes or No (mirror statements are answered through
    their achieved statement).
    """
    level_keys = []
    for _, level_label in _INDICATOR_LEVELS:
        rows = level_rows[level_label]
        if not rows:
            level_keys.append('"none"')
            continue
        count_yes = f'COUNTIF(F{rows[0]}:F{rows[-1]},"Yes")'
        level_keys.append(f'IF({count_yes}=0,"none",IF({count_yes}={len(rows)},"all","some"))')
    rule_key = '&"_"&'.join(level_keys)
    rules_table = ";".join(f'"{key}","{rule["outcome_status"]}"' for key, rule in assessment_rules.items())
    status = f"VLOOKUP({rule_key},{{{rules_table}}},2,FALSE)"
    answers = f"F{first_row}:F{last_row}"
    statement_count = last_row - first_row + 1
    return f'=IF(COUNTIF({answers},"Yes")+COUNTIF({answers},"No")<{statement_count},"",{status})'


def _row_height(
    values, font_size: float = _BASE_FONT_SIZE, column_widths: dict[str, float] = _OBJECTIVE_COLUMN_WIDTHS
) -> float:
    """Estimate the height of a wrapped row, as openpyxl cannot auto-fit rows.

    ``values`` are the cell values from column A onwards. The line heights and
    characters per line are known for the base font size; larger fonts fit fewer
    characters per line and need proportionally taller lines.
    """
    scale = font_size / _BASE_FONT_SIZE
    lines = 1
    for col_idx, value in enumerate(values, start=1):
        if not value:
            continue
        chars_per_line = max(1, int(column_widths[get_column_letter(col_idx)] * _CHARS_PER_COLUMN_WIDTH_UNIT / scale))
        lines = max(lines, sum(max(1, len(textwrap.wrap(part, chars_per_line))) for part in str(value).split("\n")))
    if lines <= len(_LINE_HEIGHTS):
        height = _LINE_HEIGHTS[lines - 1]
    else:
        height = _LINE_HEIGHTS[-1] + (lines - len(_LINE_HEIGHTS)) * _LINE_HEIGHT
    return round(height * scale, 2)


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
