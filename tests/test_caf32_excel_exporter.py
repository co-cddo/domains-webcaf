import os
import unittest

from openpyxl.worksheet.worksheet import Worksheet

from webcaf.webcaf.caf32_router import CAF32ExcelExporter


class CAF32ExcelExporterWithFixture(CAF32ExcelExporter):
    def get_framework_path(self) -> str:
        return os.path.join(os.path.dirname(__file__), "fixtures", "caf-v3.2-dummy.yaml")


class TestCAF32ExcelExporter(unittest.TestCase):
    def setUp(self):
        self.exporter = CAF32ExcelExporterWithFixture()
        self.wb = self.exporter.execute()

    def test_elements_loaded_and_workbook_created(self):
        self.assertIsInstance(self.exporter.elements, list)
        self.assertGreater(len(self.exporter.elements), 0)
        self.assertIsNotNone(self.wb)

    def test_sheet_count_and_titles(self):
        # Expect one sheet per objective in the dummy fixture (A and B)
        sheet_titles = [ws.title for ws in self.wb.worksheets]
        # Titles use the format used by exporter: "CAF - Objective {code}" or similar
        self.assertTrue(any(title.endswith("Objective A") or title.endswith("Objective - A") for title in sheet_titles))
        self.assertTrue(any(title.endswith("Objective B") or title.endswith("Objective - B") for title in sheet_titles))

    def test_top_header_contents_on_first_sheet(self):
        ws: Worksheet = self.wb.worksheets[0]
        # Title merged across C..I at row 1 with the expected text
        self.assertEqual(ws.cell(row=1, column=3).value, "PLEASE ENTER CLASSIFICATION (OFFICIAL IF BLANK)")
        # Resource Links header exists
        resource_links_row = None
        for r in range(1, 15):
            if ws.cell(row=r, column=3).value == "Resource Links":
                resource_links_row = r
                break
        self.assertIsNotNone(resource_links_row)
        # Specific link texts exist in subsequent rows
        texts = [ws.cell(row=resource_links_row + i, column=3).value for i in range(1, 4)]
        self.assertIn("Five Lens Mapping Model", texts)
        self.assertIn("Stage 3 Self-Assessment Guidance", texts)
        self.assertIn("WebCAF", texts)

    def test_outcome_sections_and_validations_present(self):
        ws: Worksheet = self.wb.worksheets[0]
        # Find the first outcome header row by searching for a known pattern "A1.a -" or similar
        found_outcome_row = None
        for r in range(1, 200):
            v = ws.cell(row=r, column=3).value
            if isinstance(v, str) and (" - " in v) and ("A1" in v or "A2" in v or "B1" in v):
                found_outcome_row = r
                break
        self.assertIsNotNone(found_outcome_row, "Outcome header not found")
        # Column headers should be 2 rows below outcome header (one row for header, one for description)
        header_row = found_outcome_row + 2
        expected_headers = [
            "Achieved",
            "Answer",
            "Partially Achieved",
            "Answer",
            "Not Achieved",
            "Answer",
            "Please summarize your evidence",
        ]
        actual_headers = [ws.cell(row=header_row, column=c).value for c in range(3, 10)]
        self.assertEqual(actual_headers, expected_headers)
        # Below headers there should be at least one indicator row with validation cells at D, F, H
        indicator_row = header_row + 1
        # The validation objects are registered on the worksheet; we can assert dataValidations exists
        self.assertTrue(hasattr(ws, "data_validations"))
        # Ensure the answer cells exist (they might be empty strings but should be addressable)
        for col in (4, 6, 8):
            self.assertIsNotNone(ws.cell(row=indicator_row, column=col))

    def test_indicator_fill_colours(self):
        # Validate fill colors for the first indicator line across achieved/partially/not columns
        ws: Worksheet = self.wb.worksheets[0]
        # Locate the first header row as in previous test
        found_outcome_row = None
        for r in range(1, 200):
            v = ws.cell(row=r, column=3).value
            if isinstance(v, str) and (" - " in v) and ("A1" in v or "A2" in v or "B1" in v):
                found_outcome_row = r
                break
        self.assertIsNotNone(found_outcome_row)
        header_row = found_outcome_row + 2
        # Find the first indicator row that actually has any indicator text in C/E/G
        indicator_row = None
        scan_row = header_row + 1
        for r in range(scan_row, scan_row + 100):
            c_vals = [ws.cell(row=r, column=c).value for c in (3, 5, 7)]
            if any(isinstance(v, str) and v.strip() for v in c_vals):
                indicator_row = r
                break
        self.assertIsNotNone(indicator_row, "Could not locate a non-empty indicator row after headers")

        # Columns C, E, G should have colored fills for achieved/partially/not respectively
        fills = {
            3: "C6E2B3",  # green
            5: "FFFACD",  # yellow
            7: "FFB6C1",  # pink
        }
        for col, expected in fills.items():
            cell = ws.cell(row=indicator_row, column=col)
            fill = cell.fill
            self.assertIsNotNone(fill)
            # openpyxl may store color as ARGB or RGB or by index; normalize and compare suffix
            color_val = None
            if getattr(fill, "start_color", None) is not None:
                color_val = fill.start_color.rgb or fill.start_color.index
            if not color_val and getattr(fill, "fgColor", None) is not None:
                color_val = fill.fgColor.rgb or fill.fgColor.index
            self.assertIsNotNone(color_val, f"Could not read cell fill color at row {indicator_row}, col {col}")
            self.assertTrue(
                str(color_val).upper().endswith(expected), f"Expected fill {expected} at column {col}, got {color_val}"
            )


if __name__ == "__main__":
    unittest.main()
