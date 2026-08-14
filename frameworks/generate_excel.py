"""
This module processes YAML-based cybersecurity assessment frameworks and generates
corresponding Excel reports using the openpyxl library.

The purpose of this module is to generate Excel spreadsheets for specific versions of
the Cyber Assessment Framework (CAF) by converting structured YAML data into formatted
sheets, including color-coded elements, formatted headers, and structured tables.

Functions:
    - safe_sheet_name: Ensures Excel worksheet names comply with naming restrictions.
    - wrap_text: Applies text wrapping to the last row of a given Excel worksheet.
    - make_bold: Formats the last row of a worksheet with bold text and optional fills.
"""

import re
from itertools import zip_longest

import yaml
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from typing_extensions import Literal


def safe_sheet_name(name: str) -> str:
    """
    Ensures that the provided name is a valid Excel worksheet name by removing
    invalid characters and truncating the name to a maximum of 31 characters.

    :param name: The name to be sanitized.
    :return: A sanitized version of the input name that is suitable for use as an
             Excel worksheet name.
    """
    name = re.sub(r"[:\\/?*\[\]]", "", name)[:30]
    return name[:31]


def wrap_text(ws):
    """
    Wraps text in cells of the last row of a worksheet to prevent text overflow.

    :param ws: The worksheet object where the text wrapping will be applied.
               Expected to be a valid instance of an openpyxl worksheet.
    :return: None
    """
    row_num = ws.max_row
    for cell in ws[row_num]:
        cell.alignment = Alignment(wrap_text=True, vertical="top")


"""
Colour names used for the background of cells.
"""
ColourName = Literal["red", "amber", "green", "blue", "grey"]


def make_bold(ws, fill: ColourName | None):
    """
    Applies bold formatting to the last row of a worksheet and optionally adds a fill
    color to the cells in the row.

    :param ws: The worksheet object where the formatting will be applied.
               Expected to be a valid instance of an openpyxl worksheet.
    :param fill: Optional fill color for the cells on the last row. Should be one of
                 the predefined color names: 'red', 'amber', 'green', 'blue', 'grey'.
                 If None, no fill will be applied.
    :return: None
    """
    row_num = ws.max_row
    fill_colours = {
        "red": PatternFill(fill_type="solid", start_color="FFC7CE", end_color="FFC7CE"),
        "amber": PatternFill(fill_type="solid", start_color="FFEB9C", end_color="FFEB9C"),
        "green": PatternFill(fill_type="solid", start_color="C6EFCE", end_color="C6EFCE"),
        "blue": PatternFill(fill_type="solid", start_color="D9EAF7", end_color="D9EAF7"),
        "grey": PatternFill(fill_type="solid", start_color="D9D9D9", end_color="D9D9D9"),
    }
    for cell in ws[row_num]:
        cell.font = Font(
            bold=True,
            size=12,
        )
        if fill:
            cell.fill = fill_colours[fill]


"""
Iterate through the Cyber Assessment Framework (CAF) versions and generate Excel sheets for each version.
"""
for caf_version in ["3.2", "4.0"]:
    wb = Workbook()
    wb.remove(wb.active)
    with open(f"cyber-assessment-framework-v{caf_version}.yaml", "r") as file:
        data = yaml.safe_load(file)
        for k, objective in data["objectives"].items():
            ws = wb.create_sheet(safe_sheet_name(f"Objective {k}-{objective['title']}"))
            for col_letter in "ABCDEFGHI":
                width = {"A": 20, "B": 40, "C": 80, "D": 20, "E": 40, "F": 80, "G": 20, "H": 40, "I": 80}.get(
                    col_letter
                )
                ws.column_dimensions[col_letter].width = width

            for p_key, principle in objective["principles"].items():
                ws.append(["", f"Principle {p_key}-{principle['title']}"])
                make_bold(ws, "green")
                ws.append(["", ""])

                for o_key, outcome in principle["outcomes"].items():
                    ws.append(["", ""])
                    ws.append(["", f"Outcome {o_key}-{outcome['title']}"])
                    make_bold(ws, "blue")
                    ws.append(["", ""])

                    ws.append(
                        [
                            "",
                            "Not achieved Code",
                            "Not achieved Description",
                            "",
                            "Partially Achieved Code",
                            "Partially Achieved Description",
                            "",
                            "Achieved Code",
                            "Achieved Description",
                        ]
                    )
                    wrap_text(ws)
                    make_bold(ws, fill="grey")
                    indicators = outcome["indicators"]

                    not_achieved = [[k, v["description"]] for k, v in indicators["not-achieved"].items()]
                    partially_achieved = [
                        [k, v["description"]] for k, v in indicators.get("partially-achieved", {}).items()
                    ]
                    achieved = [[k, v["description"]] for k, v in indicators["achieved"].items()]

                    # Generate rows filled up to the maximum number of rows
                    columns = zip_longest(not_achieved, partially_achieved, achieved, fillvalue=["", ""])

                    for indicator in columns:
                        flattened = [""] + indicator[0] + [""] + indicator[1] + [""] + indicator[2]
                        ws.append(flattened)
                        wrap_text(ws)

    wb.save(f"cyber-assessment-framework-v{caf_version}.xlsx")
    load_workbook(f"cyber-assessment-framework-v{caf_version}.xlsx")
    print("Workbook OK")
