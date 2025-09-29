import logging
import os
from abc import abstractmethod
from typing import Any, Generator, Optional

import yaml
from django.conf import settings
from django.urls import path, reverse_lazy
from django.utils.text import slugify
from django.views.generic import FormView
from openpyxl import Workbook
from openpyxl.cell import Cell
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.hyperlink import Hyperlink
from openpyxl.worksheet.worksheet import Worksheet

from webcaf import urls
from webcaf.webcaf.abcs import FrameworkRouter
from webcaf.webcaf.caf.views.factory import create_form_view
from webcaf.webcaf.forms.factory import create_form

from .field_providers import (
    FieldProvider,
    OutcomeConfirmationFieldProvider,
    OutcomeIndicatorsFieldProvider,
)

FrameworkValue = str | dict | int | None

FormViewClass = type[FormView]

CAF32Element = dict[str, Any]


class CAFLoader(FrameworkRouter):
    """
    Represents a loader for a specific framework, responsible for loading, reading, and traversing
    a hierarchical framework structure defined in YAML format.

    The class is designed to provide an interface for managing a hierarchical framework structure,
    offering functionality to load the framework from a file, traverse its structure, and retrieve
    specific elements. Subclasses are required to provide specific implementations for framework
    path and ID retrieval. The traversal is operation-specific, allowing for flexibility in
    defining stages like "indicators" or "confirmation".

    :ivar framework: Dictionary containing the entire framework structure as parsed from
        the YAML file.
    :type framework: dict
    :ivar elements: List of all framework elements extracted and traversed from the
        framework structure.
    :type elements: list
    """

    def __init__(self) -> None:
        self.framework: CAF32Element = {}
        self.elements: list[CAF32Element] = []
        self._read()

    @abstractmethod
    def get_framework_path(self) -> str:
        """
        Needs to be implemented by subclasses
        :return:
        """

    @abstractmethod
    def get_framework_id(self) -> str:
        """
        Needs to be implemented by subclasses
        :return:
        """

    def _read(self) -> None:
        with open(self.get_framework_path(), "r") as file:
            self.framework = yaml.safe_load(file)
            self.elements = list(self._traverse_framework())

    def _traverse_framework(self) -> Generator[CAF32Element, None, None]:
        """
        Traverse the framework structure and yield those elements requiring their own
        page in a single sequence.
        """
        for objective_code, objective in self.framework.get("objectives", {}).items():
            objective_ = {
                # Add the dictionary taken from the YAML first so that our code value
                # is set from the dict key and not the value *within* the dict. We
                # can probably remove the code attributes from the YAML
                **objective,
                "type": "objective",
                "code": objective_code,
                "short_name": f"{self.get_framework_id()}_objective_{objective_code}",
                "parent": None,
            }
            yield objective_
            for principle_code, principle in objective.get("principles", {}).items():
                principle_ = {
                    **principle,
                    "type": "principle",
                    "code": principle_code,
                    "short_name": f"{self.get_framework_id()}_principle_{principle_code}",
                    "parent": objective_,
                }
                yield principle_
                for outcome_code, outcome in principle.get("outcomes", {}).items():
                    outcome_ = {
                        **outcome,
                        "type": "outcome",
                        "code": outcome_code,
                        "short_name": f"{self.get_framework_id()}_indicators_{outcome_code}",
                        "parent": principle_,
                        "stage": "indicators",
                    }
                    yield outcome_
                    outcome_ = {
                        **outcome,
                        "type": "outcome",
                        "code": outcome_code,
                        "short_name": f"{self.get_framework_id()}_confirmation_{outcome_code}",
                        "parent": principle_,
                        "stage": "confirmation",
                    }
                    yield outcome_

    def get_sections(self) -> list[dict]:
        return list(filter(lambda x: x["type"] == "objective", self.elements))

    def get_section(self, objective_id: str) -> Optional[dict]:
        return next((x for x in self.get_sections() if x["code"] == objective_id), None)


class CAF32Router(CAFLoader):
    """
    Manages routing and view creation for CAF v3.2 assessments.

    The `CAF32Router` class is responsible for configuring routes, generating URLs, and creating
    corresponding view classes for the CAF (Cyber Assessment Framework) v3.2. It supports integration
    with Django's URL patterns and ensures breadcrumbs and context are created for views. This class
    inherits from `CAFLoader`.

    :ivar exit_url: The URL to redirect to after the assessment sequence completes.
    :type exit_url: str
    """

    logger = logging.getLogger("CAF32Router")

    @staticmethod
    def _build_breadcrumbs(element: CAF32Element) -> list[dict[str, str]]:
        breadcrumbs: list = []
        # We can only build the root breadcrumb here as the rest of it is dependent on the current assessment
        breadcrumbs.insert(0, {"url": reverse_lazy("my-account"), "text": "My account"})
        return breadcrumbs

    def __init__(self, exit_url: str = "index") -> None:
        self.exit_url = exit_url
        super().__init__()

    def get_framework_path(self) -> str:
        return os.path.join(settings.BASE_DIR, "..", "frameworks", "cyber-assessment-framework-v3.2.yaml")

    def get_framework_id(self) -> str:
        return "caf32"

    def _get_success_url(self, element: CAF32Element) -> str:
        """
        Determine the success URL for a form.
        If there's a next URL in the sequence, use that, otherwise use the exit URL.
        """
        current_index = self.elements.index(element)
        if current_index + 1 < len(self.elements):
            return self.elements[current_index + 1]["short_name"]
        else:
            return self.exit_url

    def _create_view_and_url(self, element: CAF32Element, form_class=None) -> None:
        """
        Takes an element from the CAF, the url for the next page in the route and a form class
        to create a view class and add a path for the view to Django's urlpatterns.
        """
        url_path = slugify(f"{element['code']}-{element['title']}")
        extra_context = {
            "title": element.get("title"),
            "description": element.get("description"),
            "breadcrumbs": CAF32Router._build_breadcrumbs(element),
        }
        if element["type"] in ["objective", "principle"]:
            template_name = f"caf/{element['type']}.html"
            class_prefix = f"{self.get_framework_id().capitalize()}{element['type'].capitalize()}View"
            element["view_class"] = create_form_view(
                success_url_name=self._get_success_url(element),
                template_name=template_name,
                class_prefix=class_prefix,
                class_id=element["code"],
                extra_context=extra_context | {"objective_data": element},
            )
            url_to_add = path(
                f"{self.get_framework_id()}/{url_path}/",
                element["view_class"].as_view(),
                name=element["short_name"],
            )
            urls.urlpatterns.append(url_to_add)
        else:
            template_name = f"caf/{element['stage']}.html"
            class_prefix = f"{self.get_framework_id().capitalize()}Outcome{element['stage'].capitalize()}View"
            element["view_class"] = create_form_view(
                success_url_name=self._get_success_url(element),
                template_name=template_name,
                form_class=form_class,
                class_prefix=class_prefix,
                stage=element["stage"],
                class_id=element["code"],
                extra_context=extra_context
                | {
                    "objective_name": f"Objective {element['parent']['parent']['code']} - {element['parent']['parent']['title']}",
                    "objective_code": element["parent"]["parent"]["code"],
                    "outcome": element,
                    "objective_data": element["parent"]["parent"],
                },
            )
            url_to_add = path(
                f"{self.get_framework_id()}/{url_path}/{element['stage']}/",
                element["view_class"].as_view(),
                name=element["short_name"],
            )
            urls.urlpatterns.append(url_to_add)
        self.logger.info(f"Added {url_to_add}")

    def _process_outcome(self, element) -> None:
        if element.get("stage") == "indicators":
            provider: FieldProvider = OutcomeIndicatorsFieldProvider(element)
            indicators_form = create_form(provider)
            self._create_view_and_url(element, form_class=indicators_form)
        elif element.get("stage") == "confirmation":
            provider = OutcomeConfirmationFieldProvider(element)
            outcome_form = create_form(provider)
            self._create_view_and_url(element, form_class=outcome_form)

    def _create_route(self) -> None:
        for element in self.elements:
            if element["type"] == "objective":
                self._create_view_and_url(element, "objective")
            elif element["type"] == "principle":
                self._create_view_and_url(element, "principle")
            elif element["type"] == "outcome":
                self._process_outcome(element)

    # Keeping this interface so we can separate generating the order of the elements
    # from creating the Django urls
    def execute(self) -> None:
        self._create_route()


class CAF40Router(CAFLoader):
    logger = logging.getLogger("CAF40Router")

    def get_framework_path(self) -> str:
        return os.path.join(settings.BASE_DIR, "..", "frameworks", "cyber-assessment-framework-v4.0.yaml")

    def get_framework_id(self) -> str:
        return "caf40"

    def execute(self) -> None:
        """
        Not implemented yet
        :return:
        """
        return None


class CAF32ExcelExporter(CAFLoader):
    """Exports CAF v3.2 framework to a formatted Excel workbook.

    The exporter creates one worksheet per Objective and renders all Principles and
    Outcomes beneath, including indicator rows and data validation lists for answers.
    """

    logger = logging.getLogger("CAF32ExcelExporter")
    OFFICIAL_SENSITIVE = "OFFICIAL SENSITIVE WHEN COMPLETED"

    # ---- FrameworkLoader hooks -------------------------------------------------
    def get_framework_path(self) -> str:
        return os.path.join(settings.BASE_DIR, "..", "frameworks", "cyber-assessment-framework-v3.2.yaml")

    def get_framework_id(self) -> str:
        return "caf32"

    # ---- Helpers ---------------------------------------------------------------

    def _write_guidance_tab(self, wb: Workbook) -> int:
        """Write the required instruction cells at the very top of a worksheet.
        Returns the next row index to continue rendering (1-based).
        """
        # Cache styles used repeatedly
        border = self._thin_border()
        ws = wb.create_sheet(title="Guidance")
        for col, width in (
            ("A", 50),
            ("B", 50),
            ("C", 50),
            ("D", 50),
        ):
            ws.column_dimensions[col].width = width

        # Content constants
        gov_assure_section_title = "GovAssure self-assessment and evidence collation template - CAF version 3.2"
        supporting_resources_title = "Supporting Resources"
        instructions_title = "To use the spreadsheet:"
        faq_title = "For questions or support:"
        template_instructions = ["You can use this spreadsheet to prepare your organisation’s GovAssure self-assessment before completing it in WebCAF.",
                                 "The structure of the spreadsheet matches the format of responses in WebCAF. You should use the GovAssure stage 3 guidance to support you when preparing your self-assessment.",
                                 "This spreadsheet is for use within your organisation. You will not need to share it with GDS. You can choose to use as much or as little as is helpful to you.",
                                 ]
        usage_instructions = ["There is a separate sheet for each CAF objective. You should scroll to the bottom of the sheet to see all contributing outcomes.\n", 
                              "For each contributing outcome, you can:",
                              "- Respond 'Yes' or 'No' to each indicator of good practice (IGP) statement that is true about your system or organisation",
                              "- If you have alternative controls in place, or the IGP is not applicable, tick the statement and explain this alternative control or exemption in the next column",
                              "- Select your overall contributing outcome status from the dropdown menu",
                              "- Write a summary for the contributing outcome (1,500 word limit)",
                              "- List your supporting evidence for the contributing outcome",
                              "\nNote: You will not be asked to list all your supporting evidence in WebCAF. You may choose to do so here for your own reference and to support your stage 4 reviewer.",
                              ]
        links = (
            (
                "Stage 3 self-assessment guidance:",
                "https://www.security.gov.uk/policy-and-guidance/govassure/stage-3-self-assessment/",
            ),
            (
                "NCSC CAF version 3.2:",
                "https://www.ncsc.gov.uk/collection/cyber-assessment-framework/changelog",
            ),
            ("WebCAF:", "https://webcaf.service.security.gov.uk/"),
        )

        faq_links = ("Please contact", "cybergovassure@cabinetoffice.gov.uk"),

        row = 1

        self._write_title(self.OFFICIAL_SENSITIVE, row, ws, h_alignment="center")
        row += 2

        self._write_title(gov_assure_section_title, row, ws)
        row += 1

        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        cell = ws.cell(row=row, column=1, value="\n\n".join(template_instructions))
        cell.alignment = Alignment(
            horizontal="left",
            vertical="top",
            wrap_text=True,
        )
        ws.row_dimensions[row].height = 100

        row += 2
        self._write_title(supporting_resources_title, row, ws)
        row += 1
        for text, target in links:
            left = ws.cell(row=row, column=1, value=text)
            left.border = border
            ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)
            right = ws.cell(row=row, column=2, value=target)
            right.border = border
            right.hyperlink = Hyperlink(ref=right.coordinate, target=target)
            right.style = "Hyperlink"
            row += 1
        row += 1

        self._write_title(instructions_title, row, ws)
        row += 1
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        cell = ws.cell(row=row, column=1, value="\n".join(usage_instructions))
        cell.alignment = Alignment(
            horizontal="left",
            vertical="top",
            wrap_text=True,
        )
        ws.row_dimensions[row].height = 150
        row += 2

        self._write_title(faq_title, row, ws)
        row += 1

        for text, target in faq_links:
            left = ws.cell(row=row, column=1, value=text)
            left.border = border
            ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)
            right = ws.cell(row=row, column=2, value=target)
            right.border = border
            right.hyperlink = Hyperlink(ref=right.coordinate, target=target)
            right.style = "Hyperlink"
            row += 1
        return row

    def _write_title(self, title: str, row: int, ws: Worksheet, h_alignment: str = "left"):
        """
        Write a title row at the given row of the worksheet.
        :param title:
        :param row:
        :param ws:
        :return:
        """
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        cell = ws.cell(row=row, column=1, value=title)
        cell.font = Font(name='Calibri', bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal=h_alignment, vertical="top", wrap_text=True)
        cell.fill = self._fills()["blue"]
        cell.border = self._thin_border()
        

    @staticmethod
    def _thin_border() -> Border:
        side = Side(border_style="thin", color="000000")
        return Border(left=side, right=side, top=side, bottom=side)

    @staticmethod
    def _fills() -> dict[str, PatternFill]:
        return {
            "yellow": PatternFill(start_color="FFFACD", end_color="FFFACD", fill_type="solid"),
            "blue": PatternFill(start_color="4682B4", end_color="4682B4", fill_type="solid"),
            "green": PatternFill(start_color="C6E2B3", end_color="C6E2B3", fill_type="solid"),
            "pink": PatternFill(start_color="FFB6C1", end_color="FFB6C1", fill_type="solid"),
            "grey": PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid"),
        }

    @staticmethod
    def _get_indicator_validator() -> DataValidation:
        return DataValidation(
            type="list",
            formula1='"Yes,No"',
            allow_blank=False,
        )

    @staticmethod
    def _header_specs(fills: dict[str, PatternFill]) -> list[tuple[str, Optional[PatternFill]]]:
        return [
            ("Achieved", fills["green"]),
            ("Answer", fills["green"]),
            ("If applicable, explain alternative controls/exemptions:", fills["green"]),
            ("Partially achieved", fills["yellow"]),
            ("Answer", fills["yellow"]),
            ("If applicable, explain alternative controls/exemptions:", fills["yellow"]),
            ("Not achieved", fills["pink"]),
            ("Answer", fills["pink"]),
            ("If applicable, explain alternative controls/exemptions:", fills["pink"]),
        ]

    @staticmethod
    def _confirmation_status_validators() -> dict[str, DataValidation]:
        return {
            "with-partial": DataValidation(
                type="list", formula1='"Achieved,Partially achieved,Not achieved"', allow_blank=False
            ),
            "without-partial": DataValidation(type="list", formula1='"Achieved,Not achieved"', allow_blank=False),
        }

    # ---- Public API ------------------------------------------------------------
    def execute(self) -> Workbook:
        """Build and return the Excel workbook for the framework."""
        wb = Workbook()
        wb.remove(wb.active)  # remove default sheet

        border = self._thin_border()
        fills = self._fills()
        indicator_validator = self._get_indicator_validator()
        # Outcome status validators no longer needed at this level since we create them per cell
        headers = self._header_specs(fills)

        self._write_guidance_tab(wb)

        # Iterate objectives -> principles -> outcomes
        for obj_code, obj_data in self.framework["objectives"].items():
            ws = wb.create_sheet(title=f"CAF - Objective {obj_code}")
            # Columns C..I are used everywhere else; keep the same for header
            for col, width in (
                ("A", 50),
                ("B", 10),
                ("C", 50),
                ("D", 50),
                ("E", 10),
                ("F", 50),
                ("G", 50),
                ("H", 10),
                ("I", 50),
            ):
                ws.column_dimensions[col].width = width

            # Start on row 1
            row = 1
            self._write_title(self.OFFICIAL_SENSITIVE, row, ws, h_alignment="center")
            row += 2

            # Header
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=9)
            cell = ws.cell(
                row=row,
                column=1,
                value=CellRichText(
                    TextBlock(
                        InlineFont(b=True),
                        "Please refer to the guidance sheet before filling in this sheet. Scroll to the bottom to make sure you have completed all contributing outcomes. 						",
                    )
                ),
            )
            cell.border = border

            row += 1
            cell = ws.cell(
                row=row,
                column=1,
                value=CellRichText(TextBlock(InlineFont(b=True), "Name of the system being assessed: ")),
            )
            cell.border = border
            ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=3)

            row += 3

            # Register indicator validator on the worksheet
            ws.add_data_validation(indicator_validator)

            # Objective heading
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=9)
            cell = ws.cell(row=row, column=1, value=f"Objective {obj_data['code']} - {obj_data['title']}")
            cell.font = Font(name='Calibri', bold=True, size=16)
            row += 1

            # Objective description
            ws.merge_cells(start_row=row, start_column=1, end_row=row + 1, end_column=9)
            cell = ws.cell(row=row, column=1, value=obj_data["description"])
            cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            row += 2

            # Principles
            for _, principle_data in obj_data.get("principles", {}).items():
                ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=9)
                cell = ws.cell(row=row, column=1, value=f"{principle_data['code']} - {principle_data['title']}")
                cell.font = Font(name='Calibri', bold=True, size=14)
                row += 1

                ws.merge_cells(start_row=row, start_column=1, end_row=row + 1, end_column=9)
                cell = ws.cell(row=row, column=1, value=principle_data["description"])
                cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
                row += 3

                # Outcomes
                for _, outcome_data in principle_data.get("outcomes", {}).items():
                    # Outcome header bar
                    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=9)
                    cell = ws.cell(row=row, column=1, value=f"{outcome_data['code']} - {outcome_data['title']}")
                    cell.font = Font(name='Calibri', bold=True, size=14, color="FFFFFF")
                    cell.fill = fills["blue"]
                    cell.border = border
                    row += 1

                    # Outcome description bar
                    ws.merge_cells(start_row=row, start_column=1, end_row=row + 1, end_column=9)
                    cell = ws.cell(row=row, column=1, value=outcome_data["description"])
                    cell.font = Font(name='Calibri', color="FFFFFF")
                    cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
                    cell.fill = fills["blue"]
                    cell.border = border
                    row += 2

                    # Column headers
                    for col_idx, (title, fill) in enumerate(headers, start=1):
                        cell = ws.cell(row=row, column=col_idx, value=title)
                        cell.font = Font(name='Calibri', bold=True, size=12)
                        cell.border = border
                        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                        if fill:
                            cell.fill = fill
                    row += 1

                    # Indicators block
                    indicators = outcome_data.get("indicators", {})
                    max_len = max((len(v) for v in indicators.values() if isinstance(v, dict)), default=0)

                    for idx in range(max_len):
                        col_idx = 1
                        for key in ("achieved", "partially-achieved", "not-achieved"):
                            values = indicators.get(key, {})
                            if idx < len(values):
                                item_data = list(values.values())[idx]
                                desc = f"{idx + 1} - {item_data['description']}"
                                cell = ws.cell(row=row, column=col_idx, value=desc)
                                cell.alignment = Alignment(wrap_text=True)
                                cell.border = border
                                # Fill per column type
                                cell.fill = (
                                    fills["pink"]
                                    if key == "not-achieved"
                                    else fills["yellow"]
                                    if key == "partially-achieved"
                                    else fills["green"]
                                )
                            else:
                                cell = ws.cell(row=row, column=col_idx, value="")
                                cell.fill = fills["grey"]
                                cell.border = border
                            col_idx += 1

                            # Adjacent answer dropdown cell
                            ans_cell = ws.cell(row=row, column=col_idx)
                            ans_cell.border = border

                            if idx < len(values):
                                # Clear any existing validations on this cell first to avoid conflicts
                                self._remove_any_validation_in_cell(ans_cell, ws)

                                # Create a new validator instance for each cell to avoid conflicts
                                cell_validator = self._get_indicator_validator()
                                ws.add_data_validation(cell_validator)
                                cell_validator.add(ans_cell.coordinate)
                            else:
                                # Grey out the answer cell when no indicator
                                ans_cell.fill = fills["grey"]

                            col_idx += 1
                            ans_cell = ws.cell(row=row, column=col_idx)
                            ans_cell.border = border
                            if idx >= len(values):
                                # Grey out the "If applicable..." cell when no indicator
                                ans_cell.fill = fills["grey"]
                            col_idx += 1
                        row += 1

                    # Contributing outcome achievement fields
                    cell = ws.cell(row=row, column=1, value="Contributing outcome status:")
                    cell.font = Font(name='Calibri', bold=True)
                    cell.border = border
                    # status value
                    cell = ws.cell(
                        row=row,
                        column=2,
                    )
                    cell.border = border

                    # Clear any existing validations first to avoid conflicts
                    self._remove_any_validation_in_cell(cell, ws)

                    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=3)

                    # Create a new validator instance for each cell to avoid conflicts
                    if indicators.get("partially-achieved"):
                        # Create fresh instance of validation for each cell
                        outcome_validator = DataValidation(
                            type="list", formula1='"Achieved,Partially achieved,Not achieved"', allow_blank=False
                        )
                    else:
                        # Create fresh instance of validation for each cell
                        outcome_validator = DataValidation(
                            type="list", formula1='"Achieved,Not achieved"', allow_blank=False
                        )

                    # Register and add validation to cell
                    ws.add_data_validation(outcome_validator)
                    outcome_validator.add(cell.coordinate)
                    cell.border = border
                    row += 1

                    cell = ws.cell(row=row, column=1, value="Contributing outcome summary (1,500 word limit):")
                    cell.font = Font(name='Calibri', bold=True)
                    cell.border = border
                    cell = ws.cell(row=row, column=2)
                    cell.border = border
                    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=9)
                    self._remove_any_validation_in_cell(cell, ws)
                    self.add_max_word_validation(cell, ws, 1500)
                    ws.row_dimensions[row].height = 50
                    row += 1

                    cell = ws.cell(row=row, column=1, value="Contributing outcome evidence list: ")
                    cell.font = Font(name='Calibri', bold=True)
                    cell.border = border
                    cell = ws.cell(row=row, column=2)
                    cell.border = border
                    self._remove_any_validation_in_cell(cell, ws)
                    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=9)
                    ws.row_dimensions[row].height = 50
                    row += 5

        return wb

    def add_max_word_validation(self, cell: Cell, ws: Worksheet, max_words: int):
        """Adds a max word validation to the given cell"""
        formula = f'LEN(TRIM({cell.coordinate})) - LEN(SUBSTITUTE(TRIM({cell.coordinate})," ","")) + 1 <= {max_words}'
        dv = DataValidation(type="custom", formula1=formula)
        dv.error = f"Maximum {max_words} words allowed"
        dv.prompt = f"Enter up to {max_words} words only"
        ws.add_data_validation(dv)
        dv.add(cell)

    def _remove_any_validation_in_cell(self, cell: Cell, ws: Worksheet):
        # Iterate through all validation rules
        for dv in ws.data_validations.dataValidation[:]:
            if cell.coordinate in dv.cells:
                dv.ranges.remove(cell.coordinate)  # remove just this cell
                if not dv.cells:  # if rule no longer applies anywhere
                    ws.data_validations.dataValidation.remove(dv)
