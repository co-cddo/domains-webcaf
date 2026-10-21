import os
import re
import unittest
import zipfile
from io import BytesIO

import yaml
from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.worksheet.cell_range import CellRange

from webcaf.webcaf.utils.excel_exporter import (
    ABOUT_SHEET_NAME,
    INDEX_SHEET_NAME,
    INDEX_TABLE_NAME,
    LISTS_SHEET_NAME,
    assessment_template_filename,
    build_assessment_template_workbook,
)
from webcaf.webcaf.utils.excel_importer import (
    JSON_MAP_HEADERS,
    JSON_MAP_SHEET_NAME,
    META_SHEET_NAME,
    excel_to_assessment_json,
)

OBJECTIVE_HEADERS = [
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
]

TABLE_HEADERS = OBJECTIVE_HEADERS[:7]
HEADER_FILL = "225E6D"
EXCEL_LAST_COLUMN = 16384


class TestCAF32ExcelExporter(unittest.TestCase):
    def setUp(self):
        framework_path = os.path.join(
            os.path.dirname(__file__), "../frameworks", "cyber-assessment-framework-v3.2.yaml"
        )
        with open(framework_path, "r") as file:
            self.framework = yaml.safe_load(file)
        self.wb = build_assessment_template_workbook(self.framework, "caf32")
        # Uncomment to save the workbook for manual inspection
        # current_dir = os.path.dirname(os.path.abspath(__file__))
        # new_file_path = os.path.join(current_dir, "test.xlsx")
        # self.wb.save(new_file_path)

    def _json_map(self) -> dict:
        map_ws = self.wb[JSON_MAP_SHEET_NAME]
        return {row[2]: row for row in map_ws.iter_rows(min_row=2, values_only=True)}

    def _visible_sheet_names(self) -> list:
        return [ABOUT_SHEET_NAME] + [
            name
            for code in self.framework["objectives"]
            for name in (f"Objective {code}", f"Objective {code} evidence")
        ]

    def _hidden_columns(self, ws) -> list:
        return [(dim.min, dim.max) for dim in ws.column_dimensions.values() if dim.hidden]

    def test_sheet_names_and_visibility(self):
        self.assertEqual(
            self.wb.sheetnames,
            [
                INDEX_SHEET_NAME,
                ABOUT_SHEET_NAME,
                "Objective A",
                "Objective A evidence",
                "Objective B",
                "Objective B evidence",
                "Objective C",
                "Objective C evidence",
                "Objective D",
                "Objective D evidence",
                LISTS_SHEET_NAME,
                JSON_MAP_SHEET_NAME,
                META_SHEET_NAME,
            ],
        )
        self.assertEqual(self.wb[JSON_MAP_SHEET_NAME].sheet_state, "veryHidden")
        self.assertEqual(self.wb[META_SHEET_NAME].sheet_state, "veryHidden")
        self.assertEqual(self.wb[META_SHEET_NAME]["B1"].value, "caf32")

    def test_index_sheet_links_to_every_visible_sheet(self):
        ws = self.wb[INDEX_SHEET_NAME]
        self.assertEqual(
            ws["A1"].value,
            "Welcome to the Prepare your GovAssure self-assessment and evidence spreadsheet "
            "(Cyber Assessment Framework (CAF) version 3.2).\n"
            "This worksheet is the index you can use to navigate to individual sheets.\n"
            "Index begins in cell A2.\n"
            "Rows and columns outside of the tables are hidden to prevent accidental navigation.",
        )
        self.assertEqual(ws["A1"].font.size, 12)
        self.assertTrue(ws["A1"].alignment.wrap_text)
        self.assertGreater(ws.row_dimensions[1].height, 60)

        self.assertEqual(ws["A2"].value, "Index")
        self.assertEqual(ws["A2"].font.size, 14)
        self.assertTrue(ws["A2"].font.bold)
        self.assertEqual(ws["A2"].font.color.rgb, "00FFFFFF")
        self.assertEqual(ws["A2"].fill.fgColor.rgb, "00000000")

        entries = self._visible_sheet_names()
        self.assertEqual([ws.cell(row=row, column=1).value for row in range(3, 12)], entries)
        for row, title in enumerate(entries, start=3):
            cell = ws.cell(row=row, column=1)
            self.assertEqual(cell.hyperlink.location, f"'{title}'!A1")
            self.assertIsNone(cell.hyperlink.target)
            self.assertEqual(cell.font.color.rgb, "000000FF")
            self.assertEqual(cell.font.underline, "single")
            self.assertEqual(cell.font.size, 12)
        self.assertNotIn(LISTS_SHEET_NAME, entries)
        self.assertIsNone(ws["A12"].value)

    def test_index_sheet_is_a_table_with_everything_else_hidden(self):
        ws = self.wb[INDEX_SHEET_NAME]
        table = ws.tables[INDEX_TABLE_NAME]
        self.assertEqual(table.ref, "A2:A11")
        self.assertEqual([column.name for column in table.tableColumns], ["Index"])
        self.assertFalse(table.tableStyleInfo.showRowStripes)
        self.assertEqual(self._hidden_columns(ws), [(2, EXCEL_LAST_COLUMN)])
        self.assertTrue(ws.sheet_format.zeroHeight)
        for row in range(1, 12):
            self.assertIsNotNone(ws.row_dimensions[row].height, row)

    def test_about_sheet(self):
        ws = self.wb[ABOUT_SHEET_NAME]
        self.assertEqual(
            [ws.cell(row=row, column=1).value for row in range(1, 8)],
            [
                "Prepare your GovAssure self-assessment and evidence (CAF version 3.2)",
                "System being assessed",
                "Enter the name of the system",
                "Guidance on using this document",
                "Prepare your GovAssure self-assessment and evidence",
                "You must mark this document OFFICIAL-SENSITIVE.",
                None,
            ],
        )
        title = ws["A1"]
        self.assertEqual((title.font.size, title.font.bold, title.font.color.rgb), (16, True, "00FFFFFF"))
        self.assertEqual(title.fill.fgColor.rgb, "001F497D")
        self.assertTrue(title.alignment.wrap_text)
        self.assertGreater(ws.row_dimensions[1].height, 30)
        for coordinate in ("A2", "A4"):
            heading = ws[coordinate]
            self.assertEqual((heading.font.size, heading.font.bold, heading.font.color.rgb), (14, True, "00000000"))
            self.assertEqual(heading.fill.fgColor.rgb, "00C5D9F1")
        for coordinate in ("A3", "A5", "A6"):
            self.assertEqual(ws[coordinate].font.size, 12)
        link = ws["A5"]
        self.assertEqual(
            link.hyperlink.target,
            "https://www.security.gov.uk/policy-and-guidance/govassure/stage-3-self-assessment/"
            "prepare-your-GovAssure-self-assessment-and-evidence",
        )
        self.assertEqual(link.font.color.rgb, "000000FF")
        self.assertEqual(link.font.underline, "single")
        self.assertEqual(self._hidden_columns(ws), [(2, EXCEL_LAST_COLUMN)])
        self.assertTrue(ws.sheet_format.zeroHeight)
        for row in range(1, 7):
            self.assertIsNotNone(ws.row_dimensions[row].height, row)
        self.assertIsNone(ws.row_dimensions[7].height)
        self.assertFalse(ws.sheet_view.showGridLines)

    def test_evidence_sheet(self):
        ws = self.wb["Objective A evidence"]
        self.assertEqual(
            [cell.value for cell in ws[1]],
            [
                "Contributing outcome",
                "Evidence name",
                "Notes",
                "Relevant indicators of good practice (IGPs)",
                "Hyperlink to evidence",
            ],
        )
        for cell in ws[1]:
            self.assertEqual(cell.font.size, 14)
            self.assertEqual(cell.fill.fgColor.rgb, f"00{HEADER_FILL}")
        self.assertGreaterEqual(ws.row_dimensions[1].height, 37)
        validations = [(str(dv.sqref), dv.formula1) for dv in ws.data_validations.dataValidation]
        self.assertEqual(validations, [("A2:A201", "Objective_A_COs")])
        self.assertEqual(ws.freeze_panes, "A2")

        self.assertFalse(ws.sheet_format.zeroHeight)
        self.assertEqual(self._hidden_columns(ws), [])
        self.assertEqual(len(ws.tables), 0)
        self.assertEqual(ws.auto_filter.ref, "A1:D201")

    def test_lists_sheet_feeds_evidence_dropdowns(self):
        ws = self.wb[LISTS_SHEET_NAME]
        self.assertEqual(ws["A3"].value, "Objective A")
        self.assertEqual(ws["A4"].value, "A1.a - Board Direction")
        self.assertEqual(self.wb.defined_names["Objective_A_COs"].attr_text, "Lists!$A$4:$A$10")
        for code in "ABCD":
            self.assertIn(f"Objective_{code}_COs", self.wb.defined_names)

    def test_objective_sheet_headers(self):
        ws = self.wb["Objective A"]
        self.assertEqual([ws.cell(row=1, column=col).value for col in range(1, 10)], OBJECTIVE_HEADERS)

        for col in range(1, 10):
            cell = ws.cell(row=1, column=col)
            self.assertEqual(cell.font.size, 14)
            self.assertTrue(cell.font.bold)
            self.assertEqual(cell.font.color.rgb, "00FFFFFF")
            self.assertEqual(cell.fill.fgColor.rgb, f"00{HEADER_FILL}")
            self.assertTrue(cell.alignment.wrap_text)
            self.assertEqual(cell.border.left.style, "hair")

        self.assertGreaterEqual(ws.row_dimensions[1].height, 55)
        self.assertEqual(ws.freeze_panes, "C2")

    def test_objective_sheet_is_a_table(self):
        for code in self.framework["objectives"]:
            ws = self.wb[f"Objective {code}"]
            table = ws.tables[f"Objective{code}"]
            self.assertEqual(table.ref, f"A1:G{ws.max_row}")
            self.assertEqual([column.name for column in table.tableColumns], TABLE_HEADERS)
            self.assertEqual(table.headerRowCount, 1)
            self.assertFalse(table.tableStyleInfo.showRowStripes)
            self.assertEqual(table.autoFilter.ref, table.ref)
            self.assertIsNone(ws.auto_filter.ref)

            table_range = CellRange(table.ref)
            for merged in ws.merged_cells.ranges:
                self.assertEqual(merged.min_col, merged.max_col, str(merged))
                self.assertIn(merged.min_col, (8, 9), str(merged))
                self.assertTrue(merged.isdisjoint(table_range), str(merged))

    def test_objective_sheet_hides_everything_outside_the_data(self):
        ws = self.wb["Objective A"]

        self.assertEqual(self._hidden_columns(ws), [(10, EXCEL_LAST_COLUMN)])
        self.assertTrue(ws.sheet_format.zeroHeight)
        for row in range(1, ws.max_row + 1):
            self.assertIsNotNone(ws.row_dimensions[row].height, row)

    def test_objective_sheet_body_text_is_12pt(self):
        ws = self.wb["Objective A"]
        for row in ws.iter_rows(min_row=2, max_col=9):
            for cell in row:
                if isinstance(cell, MergedCell):
                    continue
                self.assertEqual(cell.font.size, 12, cell.coordinate)
                self.assertTrue(cell.alignment.wrap_text, cell.coordinate)

    def test_row_heights_grow_with_wrapped_text(self):
        ws = self.wb["Objective A"]
        heights = {row: ws.row_dimensions[row].height for row in range(2, ws.max_row + 1)}

        self.assertGreaterEqual(min(heights.values()), 15.7)

        wording_lengths = {row: len(ws.cell(row=row, column=5).value or "") for row in heights}
        longest = max(wording_lengths, key=wording_lengths.get)
        shortest = min(wording_lengths, key=wording_lengths.get)
        self.assertGreater(heights[longest], heights[shortest])

    def test_one_row_per_igp_ordered_by_level(self):
        ws = self.wb["Objective A"]
        rows = [row[:5] for row in ws.iter_rows(min_row=2, max_row=9, values_only=True)]
        a1a = self.framework["objectives"]["A"]["principles"]["A1"]["outcomes"]["A1.a"]["indicators"]
        self.assertEqual(
            rows[0],
            (
                "A1 Governance",
                "A1.a - Board Direction",
                "Achieved",
                "Achieved statement 1",
                a1a["achieved"]["A1.a.5"]["description"],
            ),
        )
        self.assertEqual(rows[4][2:4], ("Not achieved", "Not achieved statement 1"))
        self.assertEqual(rows[4][4], a1a["not-achieved"]["A1.a.1"]["description"])

        total_igps = sum(
            len(items or {})
            for objective in self.framework["objectives"].values()
            for principle in objective["principles"].values()
            for outcome in principle["outcomes"].values()
            for items in outcome["indicators"].values()
        )
        igp_rows = sum(self.wb[f"Objective {code}"].max_row - 1 for code in self.framework["objectives"])
        self.assertEqual(igp_rows, total_igps)

    def test_status_and_summary_cells_span_the_outcomes_rows(self):
        ws = self.wb["Objective A"]
        merged = [str(merged) for merged in ws.merged_cells.ranges]
        self.assertIn("H2:H9", merged)
        self.assertIn("I2:I9", merged)
        self.assertTrue(ws["H2"].value.startswith("=IF("))
        self.assertEqual(
            ws["I2"].value,
            "You have effective organisational security management led at board level and articulated "
            "clearly in corresponding policies.",
        )
        for coordinate in ("H2", "I2"):
            cell = ws[coordinate]
            self.assertEqual(cell.font.size, 12, coordinate)
            self.assertTrue(cell.fill.fgColor.rgb.endswith("DAEEF3"), coordinate)
            self.assertTrue(cell.alignment.wrap_text, coordinate)
            self.assertEqual(cell.border.left.style, "hair", coordinate)

        self.assertEqual(ws["H5"].border.left.style, "hair")
        self.assertEqual(ws["I9"].border.bottom.style, "hair")
        self.assertTrue(ws["H10"].value.startswith("=IF("))
        self.assertIsNotNone(ws["I10"].value)

    def test_every_outcome_has_one_status_and_one_summary_cell(self):
        for code in self.framework["objectives"]:
            ws = self.wb[f"Objective {code}"]
            outcome_rows = {}
            for row in range(2, ws.max_row + 1):
                outcome_rows.setdefault(ws.cell(row=row, column=2).value, []).append(row)
            expected = {
                f"{column}{rows[0]}:{column}{rows[-1]}"
                for rows in outcome_rows.values()
                if len(rows) > 1
                for column in "HI"
            }
            self.assertEqual({str(merged) for merged in ws.merged_cells.ranges}, expected, ws.title)
            for rows in outcome_rows.values():
                self.assertTrue(str(ws.cell(row=rows[0], column=8).value).startswith("=IF("), ws.title)
                self.assertIsNotNone(ws.cell(row=rows[0], column=9).value, ws.title)

    def test_outcome_rows_are_tall_enough_for_the_summary(self):
        ws = self.wb["Objective A"]
        for merged in ws.merged_cells.ranges:
            if merged.min_col != 9:
                continue
            summary = ws.cell(row=merged.min_row, column=9).value
            outcome_height = sum(ws.row_dimensions[row].height for row in range(merged.min_row, merged.max_row + 1))
            # Roughly 70 characters of 12pt text fit on a line of the summary column
            self.assertGreaterEqual(outcome_height, 15.7 * (len(summary) // 70 + 1), str(merged))

    def test_outcomes_alternate_background(self):
        ws = self.wb["Objective A"]
        self.assertTrue(ws["A2"].fill.fgColor.rgb.endswith("DAEEF3"))
        self.assertTrue(ws["A10"].fill.fgColor.rgb.endswith("FFFFFF"))
        self.assertTrue(ws["A16"].fill.fgColor.rgb.endswith("DAEEF3"))

    def test_answer_validation(self):
        ws = self.wb["Objective A"]
        validations = [(str(dv.sqref), dv.formula1) for dv in ws.data_validations.dataValidation]
        self.assertEqual(validations, [(f"F2:F{ws.max_row}", '"Yes,No"')])

    def test_status_colours(self):
        ws = self.wb["Objective A"]
        rules = {
            (str(cf.sqref), rule.formula[0]): (rule.dxf.font.color.rgb, rule.dxf.fill.bgColor.rgb)
            for cf in ws.conditional_formatting
            for rule in cf.rules
        }
        last_row = ws.max_row
        for column in "CH":
            self.assertEqual(rules[(f"{column}2:{column}{last_row}", '"Achieved"')], ("00225214", "00C6EFCE"))
            self.assertEqual(rules[(f"{column}2:{column}{last_row}", '"Partially achieved"')], ("00694316", "00FFEB9C"))
            self.assertEqual(rules[(f"{column}2:{column}{last_row}", '"Not achieved"')], ("00771813", "00FFC7CE"))

    def test_json_map(self):
        json_map = self._json_map()
        self.assertEqual(
            [cell.value for cell in self.wb[JSON_MAP_SHEET_NAME][1]],
            JSON_MAP_HEADERS,
        )
        self.assertEqual(
            json_map["/A1.a/indicators/achieved_A1.a.5"],
            ("Objective A", "F2", "/A1.a/indicators/achieved_A1.a.5", "indicator_answer", False, None),
        )
        self.assertEqual(
            json_map["/A1.a/indicators/not-achieved_A1.a.1_comment"],
            ("Objective A", "G6", "/A1.a/indicators/not-achieved_A1.a.1_comment", "text", False, None),
        )
        summary = json_map["/A1.a/confirmation/confirm_outcome_confirm_comment"]
        self.assertEqual(summary[:5], ("Objective A", "I2", summary[2], "text", False))
        self.assertEqual(summary[5], self.wb["Objective A"]["I2"].value)
        self.assertFalse(any(path.endswith("/outcome_status") for path in json_map))

    def test_saved_workbook_reloads_with_tables_and_imports(self):
        ws = self.wb["Objective A"]
        for row in range(2, 10):
            ws.cell(row=row, column=6, value="Yes" if ws.cell(row=row, column=3).value == "Achieved" else "No")
        ws["I2"] = "A1.a summary"
        output = BytesIO()
        self.wb.save(output)
        output.seek(0)

        reloaded = load_workbook(output)
        self.assertEqual(
            {name for ws in reloaded.worksheets for name in ws.tables},
            {INDEX_TABLE_NAME, "ObjectiveA", "ObjectiveB", "ObjectiveC", "ObjectiveD"},
        )
        self.assertEqual(
            [column.name for column in reloaded["Objective A"].tables["ObjectiveA"].tableColumns],
            TABLE_HEADERS,
        )
        self.assertIn("I2:I9", [str(merged) for merged in reloaded["Objective A"].merged_cells.ranges])
        self.assertEqual(reloaded[INDEX_SHEET_NAME]["A4"].hyperlink.location, "'Objective A'!A1")

        reloaded_ws = reloaded["Objective A"]
        self.assertTrue(reloaded_ws.protection.sheet)
        self.assertFalse(reloaded_ws.protection.password)
        self.assertTrue(reloaded_ws["H2"].protection.locked)
        self.assertTrue(reloaded_ws["H2"].protection.hidden)
        self.assertFalse(reloaded_ws["F2"].protection.locked)
        self.assertFalse(reloaded_ws["I2"].protection.locked)
        self.assertFalse(reloaded[INDEX_SHEET_NAME].protection.sheet)
        self.assertFalse(reloaded["Objective A evidence"].protection.sheet)

        output.seek(0)
        data = excel_to_assessment_json(output, self.framework)
        self.assertTrue(data["A1.a"]["indicators"]["achieved_A1.a.5"])
        self.assertEqual(data["A1.a"]["confirmation"]["confirm_outcome_confirm_comment"], "A1.a summary")
        self.assertEqual(data["A1.a"]["confirmation"]["outcome_status"], "Achieved")


class TestAssessmentTemplateFilename(unittest.TestCase):
    def test_known_frameworks_are_named_after_their_caf_version(self):
        self.assertEqual(
            assessment_template_filename("caf40"), "Prepare-your-GovAssure-self-assessment-and-evidence-CAF-v4.0.xlsx"
        )
        self.assertEqual(
            assessment_template_filename("caf32"), "Prepare-your-GovAssure-self-assessment-and-evidence-CAF-v3.2.xlsx"
        )

    def test_unknown_frameworks_fall_back_to_their_id(self):
        self.assertEqual(
            assessment_template_filename("caf99"), "Prepare-your-GovAssure-self-assessment-and-evidence-caf99.xlsx"
        )
        self.assertEqual(assessment_template_filename(None), "Prepare-your-GovAssure-self-assessment-and-evidence.xlsx")


if __name__ == "__main__":
    unittest.main()


class TestCAF40ExcelExporterWithoutJsonMap(unittest.TestCase):
    def setUp(self):
        framework_path = os.path.join(
            os.path.dirname(__file__), "../frameworks", "cyber-assessment-framework-v4.0.yaml"
        )
        with open(framework_path, "r") as file:
            self.framework = yaml.safe_load(file)
        self.wb = build_assessment_template_workbook(self.framework, "caf40", include_json_map=False)

    def test_only_lists_sheet_is_hidden(self):
        wb = self.wb
        self.assertEqual(
            wb.sheetnames,
            [INDEX_SHEET_NAME, ABOUT_SHEET_NAME]
            + [
                name
                for code in self.framework["objectives"]
                for name in (f"Objective {code}", f"Objective {code} evidence")
            ]
            + [LISTS_SHEET_NAME],
        )
        self.assertEqual(
            {ws.title: ws.sheet_state for ws in wb.worksheets if ws.sheet_state != "visible"},
            {LISTS_SHEET_NAME: "veryHidden"},
        )
        self.assertEqual(
            wb[ABOUT_SHEET_NAME]["A1"].value,
            "Prepare your GovAssure self-assessment and evidence (CAF version 4.0)",
        )
        self.assertIn("(Cyber Assessment Framework (CAF) version 4.0)", wb[INDEX_SHEET_NAME]["A1"].value)

    def test_unknown_caf_version_is_left_out_of_the_titles(self):
        wb = build_assessment_template_workbook(self.framework, include_json_map=False)
        self.assertEqual(wb[ABOUT_SHEET_NAME]["A1"].value, "Prepare your GovAssure self-assessment and evidence")
        self.assertIn("(Cyber Assessment Framework (CAF)).", wb[INDEX_SHEET_NAME]["A1"].value)

    def test_mirror_statements_copy_the_achieved_answer(self):
        mirrors = []
        for ws in (self.wb[f"Objective {code}"] for code in self.framework["objectives"]):
            achieved = {}
            for row in range(2, ws.max_row + 1):
                key = (ws.cell(row=row, column=2).value, " ".join(str(ws.cell(row=row, column=5).value).split()))
                level = ws.cell(row=row, column=3).value
                answer = ws.cell(row=row, column=6).value
                if level == "Achieved":
                    achieved[key] = f"F{row}"
                    self.assertIsNone(answer)
                elif level == "Partially achieved" and key in achieved:
                    source = achieved[key]
                    self.assertEqual(answer, f'=IF({source}="","Answer the identical \'Achieved\' statement",{source})')
                    mirrors.append((ws.title, row))
                else:
                    self.assertIsNone(answer)
        self.assertEqual(len(mirrors), 20)

    def test_outcome_status_formula_looks_up_assessment_rules(self):
        ws = self.wb["Objective A"]
        # A1.a: achieved F2:F7, no partially achieved, not achieved F8:F11
        self.assertEqual(
            ws["H2"].value,
            '=IF(COUNTIF(F2:F11,"Yes")+COUNTIF(F2:F11,"No")<10,"",'
            'VLOOKUP(IF(COUNTIF(F2:F7,"Yes")=0,"none",IF(COUNTIF(F2:F7,"Yes")=6,"all","some"))'
            '&"_"&"none"&"_"&'
            'IF(COUNTIF(F8:F11,"Yes")=0,"none",IF(COUNTIF(F8:F11,"Yes")=4,"all","some")),'
            "{"
            + ";".join(
                f'"{key}","{rule["outcome_status"]}"' for key, rule in self.framework["assessment-rules"].items()
            )
            + "},2,FALSE))",
        )
        self.assertLess(len(ws["H2"].value), 8192)

    def test_only_computed_cells_are_locked(self):
        ws = self.wb["Objective A"]
        self.assertTrue(ws.protection.sheet)
        self.assertFalse(ws.protection.autoFilter)
        self.assertFalse(ws.protection.formatColumns)
        self.assertFalse(ws.protection.formatRows)
        self.assertTrue(ws["H2"].protection.locked)
        self.assertTrue(ws["H2"].protection.hidden)
        for coordinate in ("A1", "C2", "F2", "G2", "I2"):
            self.assertFalse(ws[coordinate].protection.locked, coordinate)
        for column in "ABCDEFGI":
            self.assertFalse(ws.column_dimensions[column].protection.locked, column)
        mirrors = 0
        for row in range(2, ws.max_row + 1):
            answer = ws.cell(row=row, column=6)
            is_mirror = str(answer.value).startswith("=")
            mirrors += is_mirror
            self.assertEqual(answer.protection.locked, is_mirror, answer.coordinate)
            self.assertFalse(answer.protection.hidden, answer.coordinate)
        self.assertGreater(mirrors, 0)

    def test_sheets_are_protected_without_a_password(self):

        objective_sheets = {f"Objective {code}" for code in self.framework["objectives"]}
        self.assertFalse(self.wb.security.lockStructure)
        self.assertFalse(self.wb.security.workbookPassword)
        for ws in self.wb.worksheets:
            self.assertEqual(ws.protection.sheet, ws.title in objective_sheets, ws.title)
            self.assertFalse(ws.protection.password, ws.title)

        output = BytesIO()
        self.wb.save(output)
        output.seek(0)
        with zipfile.ZipFile(output) as archive:
            sheet_xml = [
                archive.read(name).decode()
                for name in archive.namelist()
                if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
            ]
            workbook_xml = archive.read("xl/workbook.xml").decode()
        
        for protection in re.findall(r"<workbookProtection[^>]*/?>", workbook_xml):
            for attribute in ("lockStructure", "lockWindows", "workbookPassword", "workbookHashValue"):
                self.assertNotIn(attribute, protection, protection)
        protections = [match for xml in sheet_xml for match in re.findall(r"<sheetProtection[^>]*/?>", xml)]
        self.assertEqual(len(protections), len(objective_sheets))
        for protection in protections:
            self.assertIn('sheet="1"', protection)
            for attribute in ("password", "hashValue", "algorithmName", "saltValue", "spinCount"):
                self.assertNotIn(attribute, protection, protection)

    def test_mirror_answers_import_from_the_achieved_statement(self):
        wb = build_assessment_template_workbook(self.framework, "caf40")
        ws = wb["Objective A"]
        answer_cells = [
            cell
            for sheet, cell, path, value_type, *_ in wb[JSON_MAP_SHEET_NAME].iter_rows(min_row=2, values_only=True)
            if sheet == ws.title and value_type == "indicator_answer"
        ]
        mirrors = 0
        for row in range(2, ws.max_row + 1):
            answer = ws.cell(row=row, column=6).value
            if str(answer).startswith("="):
                achieved_cell = answer.removeprefix("=IF(").split("=")[0]
                self.assertNotIn(f"F{row}", answer_cells)
                self.assertEqual(answer_cells.count(achieved_cell), 2)
                mirrors += 1
        self.assertEqual(mirrors, 3)
