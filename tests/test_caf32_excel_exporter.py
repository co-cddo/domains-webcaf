import os
import unittest

import yaml

from webcaf.webcaf.utils.excel_exporter import (
    GUIDANCE_SHEET_NAME,
    build_assessment_template_workbook,
)
from webcaf.webcaf.utils.excel_importer import (
    JSON_MAP_HEADERS,
    JSON_MAP_SHEET_NAME,
    META_SHEET_NAME,
)


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

    def test_sheet_names_and_visibility(self):
        self.assertEqual(
            self.wb.sheetnames,
            [
                GUIDANCE_SHEET_NAME,
                "Objective A",
                "Objective B",
                "Objective C",
                "Objective D",
                JSON_MAP_SHEET_NAME,
                META_SHEET_NAME,
            ],
        )
        self.assertEqual(self.wb[JSON_MAP_SHEET_NAME].sheet_state, "veryHidden")
        self.assertEqual(self.wb[META_SHEET_NAME].sheet_state, "veryHidden")
        self.assertEqual(self.wb[META_SHEET_NAME]["B1"].value, "caf32")

    def test_guidance_sheet(self):
        ws = self.wb[GUIDANCE_SHEET_NAME]
        self.assertEqual(ws["A1"].value, "OFFICIAL SENSITIVE WHEN COMPLETED")
        self.assertEqual(ws["A3"].value, "GovAssure self-assessment and evidence collation template - CAF version 3.2")
        self.assertEqual(ws["A8"].value, "NCSC CAF version 3.2:")
        self.assertEqual(ws["B9"].hyperlink.target, "https://webcaf.service.security.gov.uk/")
        self.assertEqual(ws["B15"].hyperlink.target, "mailto:cybergovassure@cabinetoffice.gov.uk")

    def test_objective_sheet_headers(self):
        ws = self.wb["Objective A"]
        self.assertEqual(
            [ws.cell(row=1, column=col).value for col in range(1, 9)],
            [
                "Principle",
                "Contributing outcome",
                "IGP type",
                "IGP",
                "IGP wording",
                "Answer",
                "If applicable, explain alternative controls/exemptions:",
                "Contributing outcome summary (max 1,500 words)\n"
                "The CAF contributing outcome wording is displayed for reference",
            ],
        )
        self.assertEqual(ws.freeze_panes, "C2")

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

    def test_summary_cell_spans_outcome_rows(self):
        ws = self.wb["Objective A"]
        self.assertIn("H2:H9", [str(merged) for merged in ws.merged_cells.ranges])
        self.assertEqual(
            ws["H2"].value,
            "You have effective organisational security management led at board level and articulated "
            "clearly in corresponding policies.",
        )

    def test_outcomes_alternate_background(self):
        ws = self.wb["Objective A"]
        self.assertTrue(ws["A2"].fill.fgColor.rgb.endswith("DAEEF3"))
        self.assertTrue(ws["A10"].fill.fgColor.rgb.endswith("FFFFFF"))
        self.assertTrue(ws["A16"].fill.fgColor.rgb.endswith("DAEEF3"))

    def test_answer_validation(self):
        ws = self.wb["Objective A"]
        validations = [(str(dv.sqref), dv.formula1) for dv in ws.data_validations.dataValidation]
        self.assertEqual(validations, [(f"F2:F{ws.max_row}", '"Yes,No"')])

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
        self.assertEqual(summary[:5], ("Objective A", "H2", summary[2], "text", False))
        self.assertEqual(summary[5], self.wb["Objective A"]["H2"].value)
        self.assertFalse(any(path.endswith("/outcome_status") for path in json_map))


if __name__ == "__main__":
    unittest.main()
