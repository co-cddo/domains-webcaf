import unittest
from io import BytesIO

from openpyxl import Workbook

from webcaf.webcaf.utils.excel_exporter import build_assessment_template_workbook
from webcaf.webcaf.utils.excel_importer import (
    JSON_MAP_SHEET_NAME,
    ExcelImportError,
    excel_to_review_json,
)

FRAMEWORK = {
    "objectives": {
        "A": {
            "code": "A",
            "title": "Managing security risk",
            "description": "Objective A description",
            "principles": {
                "A1": {
                    "code": "A1",
                    "title": "Governance",
                    "description": "Principle A1 description",
                    "outcomes": {
                        "A1.a": {
                            "code": "A1.a",
                            "title": "Board Direction",
                            "description": "Outcome A1.a description",
                            "indicators": {
                                "achieved": {
                                    "A1.a.1": {"description": "First achieved indicator"},
                                    "A1.a.2": {"description": "Second achieved indicator"},
                                },
                                "partially-achieved": {
                                    "A1.a.3": {"description": "Partially achieved indicator"},
                                },
                                "not-achieved": {
                                    "A1.a.4": {"description": "Not achieved indicator"},
                                },
                            },
                        },
                        "A1.b": {
                            "code": "A1.b",
                            "title": "Assurance",
                            "description": "Outcome A1.b description",
                            "indicators": {
                                "achieved": {"A1.b.1": {"description": "Only achieved indicator"}},
                                "not-achieved": {"A1.b.2": {"description": "Only not-achieved indicator"}},
                            },
                        },
                    },
                }
            },
        }
    }
}


class TestCAF32ReviewExcelImporter(unittest.TestCase):
    def _workbook_file(self, values: dict) -> BytesIO:
        """
        Build the template for FRAMEWORK and fill in the given cell values.
        """
        wb = build_assessment_template_workbook(FRAMEWORK)
        cell_map = self._cell_map(wb)
        for json_path, value in values.items():
            ws_title, coordinate = cell_map[json_path]
            wb[ws_title][coordinate] = value
        return self._save(wb)

    @staticmethod
    def _cell_map(wb: Workbook) -> dict:
        map_ws = wb[JSON_MAP_SHEET_NAME]
        return {
            json_path: (visible_sheet, visible_cell)
            for visible_sheet, visible_cell, json_path, _value_type, _required in map_ws.iter_rows(
                min_row=2, values_only=True
            )
        }

    @staticmethod
    def _save(wb: Workbook) -> BytesIO:
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    COMPLETE_ANSWERS = {
        "/A1.a/indicators/achieved_A1.a.1": "Yes",
        "/A1.a/indicators/achieved_A1.a.2": "No",
        "/A1.a/indicators/partially-achieved_A1.a.3": "No",
        "/A1.a/indicators/not-achieved_A1.a.4": "Yes",
        "/A1.a/confirmation/outcome_status": "Partially achieved",
        "/A1.a/confirmation/confirm_outcome_confirm_comment": "Evidence for A1.a",
        "/A1.b/indicators/achieved_A1.b.1": "Yes",
        "/A1.b/indicators/not-achieved_A1.b.2": "No",
        "/A1.b/confirmation/outcome_status": "Achieved",
    }

    def test_round_trip_produces_expected_review_json(self):
        data = excel_to_review_json(self._workbook_file(self.COMPLETE_ANSWERS), FRAMEWORK)
        self.assertEqual(
            data,
            {
                "A": {
                    "A1.a": {
                        "achieved_A1.a.1": "yes",
                        "achieved_A1.a.2": "no",
                        "partially-achieved_A1.a.3": "no",
                        "not-achieved_A1.a.4": "yes",
                        "review_decision": "partially-achieved",
                        "review_comment": "Evidence for A1.a",
                    },
                    "A1.b": {
                        "achieved_A1.b.1": "yes",
                        "not-achieved_A1.b.2": "no",
                        "review_decision": "achieved",
                        "review_comment": "",
                    },
                }
            },
        )

    def test_review_json_feeds_set_outcome_review_shape(self):
        """
        The per-outcome dicts split into review_ and indicator keys for Review.set_outcome_review.
        """
        data = excel_to_review_json(self._workbook_file(self.COMPLETE_ANSWERS), FRAMEWORK)
        outcome_answers = data["A"]["A1.a"]
        review_keys = {key for key in outcome_answers if key.startswith("review_")}
        self.assertEqual(review_keys, {"review_decision", "review_comment"})
        indicator_keys = set(outcome_answers) - review_keys
        self.assertEqual(
            indicator_keys,
            {
                "achieved_A1.a.1",
                "achieved_A1.a.2",
                "partially-achieved_A1.a.3",
                "not-achieved_A1.a.4",
            },
        )

    def test_blank_indicator_answers_import_as_no(self):
        answers = {key: value for key, value in self.COMPLETE_ANSWERS.items() if "indicators" not in key}
        data = excel_to_review_json(self._workbook_file(answers), FRAMEWORK)
        self.assertEqual(
            {key: value for key, value in data["A"]["A1.a"].items() if not key.startswith("review_")},
            {
                "achieved_A1.a.1": "no",
                "achieved_A1.a.2": "no",
                "partially-achieved_A1.a.3": "no",
                "not-achieved_A1.a.4": "no",
            },
        )

    def test_blank_required_status_raises(self):
        answers = {
            key: value for key, value in self.COMPLETE_ANSWERS.items() if key != "/A1.b/confirmation/outcome_status"
        }
        with self.assertRaises(ExcelImportError) as ctx:
            excel_to_review_json(self._workbook_file(answers), FRAMEWORK)
        self.assertIn("Required cell", str(ctx.exception))

    def test_invalid_outcome_status_raises(self):
        answers = {**self.COMPLETE_ANSWERS, "/A1.a/confirmation/outcome_status": "Sort of achieved"}
        with self.assertRaises(ExcelImportError) as ctx:
            excel_to_review_json(self._workbook_file(answers), FRAMEWORK)
        self.assertIn("invalid outcome status", str(ctx.exception))

    def test_workbook_from_other_framework_raises(self):
        other_framework = {
            "objectives": {
                "B": {
                    "code": "B",
                    "title": "Other objective",
                    "description": "",
                    "principles": {
                        "B1": {
                            "code": "B1",
                            "title": "Other principle",
                            "description": "",
                            "outcomes": {
                                "B1.a": {
                                    "code": "B1.a",
                                    "title": "Other outcome",
                                    "description": "",
                                    "indicators": {"achieved": {"B1.a.1": {"description": "Indicator"}}},
                                }
                            },
                        }
                    },
                }
            }
        }
        with self.assertRaises(ExcelImportError) as ctx:
            excel_to_review_json(self._workbook_file(self.COMPLETE_ANSWERS), other_framework)
        self.assertIn("not part of the assessment's framework", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
