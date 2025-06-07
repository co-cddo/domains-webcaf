#!/usr/bin/env python3

import os
import re
from pathlib import Path

import yaml
from pypdf import PdfReader

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_NAME = "cyber-assessment-framework-v3.2.pdf"
PDF_PATH = Path(SCRIPT_DIR, PDF_NAME)

section_heading_pattern = re.compile(r"\b([A-Z]\d\.[a-z]) ([A-Za-z,/() -]+)")
principle_heading_pattern = re.compile(r"\bPrinciple ([A-Z]\d) ([A-Za-z,/ ]+)\b")
objective_heading_pattern = re.compile(r"CAF - Objective ([A-Z]) - ([A-Za-z ]+)\b")


def extract_section_paragraph(text: str, heading_match: re.Match, all_matches: list) -> str:
    """
    Each section (e.g. "A1.1") has a paragraph immediately after the heading. This extracts
    and returns it.
    """
    start = heading_match.end()

    next_heading_pos = len(text)
    current_pos = heading_match.start()

    for match in all_matches:
        if match.start() > current_pos and match.start() < next_heading_pos:
            next_heading_pos = match.start()

    for principle_match in principle_heading_pattern.finditer(text):
        if principle_match.start() > current_pos and principle_match.start() < next_heading_pos:
            next_heading_pos = principle_match.start()

    following_text = text[start:next_heading_pos].lstrip()

    if following_text.startswith("Not Achieved"):
        return ""

    not_achieved_pos = following_text.find("Not Achieved")
    if not_achieved_pos == -1:
        paragraph = following_text.split("\n\n", 1)[0].strip()
    else:
        paragraph = following_text[:not_achieved_pos].strip()

    return re.sub(r"\s+", " ", paragraph).strip()


def extract_principle_paragraph(text: str, heading_match: re.Match) -> str:
    """
    Each principle (e.g. "A1") has a paragraph immediately after the heading. This exracts and returns it
    """
    start = heading_match.end()

    next_heading_pos = len(text)
    current_pos = heading_match.start()

    for section_match in section_heading_pattern.finditer(text):
        if section_match.start() > current_pos and section_match.start() < next_heading_pos:
            next_heading_pos = section_match.start()

    following_text = text[start:next_heading_pos].lstrip()

    return re.sub(r"\s+", " ", following_text).strip()


def extract_objective_paragraph(text: str, heading_match: re.Match) -> str:
    """
    Each objective (e.g. "A") has a paragraph immediately after the heading. This extracts
    and returns it.
    """
    start = heading_match.end()

    next_heading_pos = len(text)
    current_pos = heading_match.start()

    for principle_match in principle_heading_pattern.finditer(text):
        if principle_match.start() > current_pos and principle_match.start() < next_heading_pos:
            next_heading_pos = principle_match.start()

    following_text = text[start:next_heading_pos].lstrip()

    return re.sub(r"\s+", " ", following_text).strip()


def extract_table(text: str, heading_match: re.Match, all_matches: list) -> list[str]:
    """
    This does the best it can to extract the statements from an IGP table. The text
    returned by the PDF parser is not in table format and the ordering of the statements
    is not consistent, so it just adds them to a single list for subsequent manual
    sorting.

    It does not handle statements containing certain combinations of parentheses
    and commas well, losing some text. This also has to be fixed manually.
    """
    start = heading_match.end()

    next_heading_pos = len(text)
    current_pos = heading_match.start()

    for match in all_matches:
        if match.start() > current_pos and match.start() < next_heading_pos:
            next_heading_pos = match.start()

    for principle_match in principle_heading_pattern.finditer(text):
        if principle_match.start() > current_pos and principle_match.start() < next_heading_pos:
            next_heading_pos = principle_match.start()

    section_text = text[start:next_heading_pos]

    not_achieved_pos = section_text.find("Not Achieved")
    if not_achieved_pos == -1:
        return []

    table_text = section_text[not_achieved_pos:]
    cell_pattern = re.compile(
        r"[A-Z][^.]*?(?:\([^)]*?\))*?(?:e\.g\.,[^)]*?\))*?\.\s*(?=\n|$)", re.MULTILINE | re.DOTALL
    )
    cells = cell_pattern.findall(table_text)

    table_items = []
    unwanted_substrings = [
        "Not Achieved",
        "Partially Achieved",
        "Achieved",
        "At least one of the following statements is true",
        "All the following statements are true",
        "Any of the following statements are true",
    ]

    for cell in cells:
        cell = cell.replace("\n", " ")
        cell = re.sub(r"\s+", " ", cell)
        for substring in unwanted_substrings:
            cell = cell.replace(substring, "")
        cell = cell.strip()
        # cell = cell.rstrip(".")
        if cell:
            table_items.append(cell)

    return table_items


def extract_text(reader: PdfReader):
    """
    Loop through the PDF pages starting from the 6th page and pull out the names and descriptions
    for objectives, principles, and sections. Extract the content from each IGP table and add it
    to the section entry.
    """
    objectives = []
    principle_headings = []
    sections = []
    for page in reader.pages[5:]:
        text = page.extract_text()
        if text:
            for match in objective_heading_pattern.finditer(text):
                paragraph = extract_objective_paragraph(text, match)
                objectives.append((match.group(1), match.group(2).strip(), paragraph))

            for match in principle_heading_pattern.finditer(text):
                paragraph = extract_principle_paragraph(text, match)
                principle_headings.append((match.group(1), match.group(2).strip(), paragraph))

            section_matches = list(section_heading_pattern.finditer(text))

            for match in section_matches:
                paragraph = extract_section_paragraph(text, match, section_matches)
                table = extract_table(text, match, section_matches)
                sections.append((match.group(1), match.group(2).strip(), paragraph, table))
    return objectives, sections, principle_headings


def create_yaml_structure(objectives: list, sections: list, principle_headings: list) -> dict:
    """
    Take the data extracted from the PDF and re-structure it for writing to YAML. Index
    objectives, principles, and sections. Add a representation of the assessment rules.
    Add a placeholder reflecting where indicators are exclusive of one another.
    """
    assessment_rules = {1: ["achieved", "all"], 2: ["partially-achieved", "all"], 3: ["not-achieved", "any"]}

    principles_dict = {}
    principle_index = 1
    for code, title, paragraph in principle_headings:
        principles_dict[principle_index] = {
            "code": code,
            "title": title,
            "principle_description": paragraph,
            "sections": {},
        }
        principle_index += 1

    section_index = 1
    # Create a global indicator counter to maintain continuous indexing
    indicator_index = 1
    for section_code, section_title, section_paragraph, table_items in sections:
        principle_code = section_code[:2]
        principle_index = next(
            (index for index, principle in principles_dict.items() if principle["code"] == principle_code), None  # type: ignore
        )
        if principle_index is not None:
            not_achieved_dict = {}
            # Use the global indicator counter instead of resetting for each section
            for statement in table_items:
                not_achieved_dict[indicator_index] = statement
                indicator_index += 1

            principles_dict[principle_index]["sections"][section_index] = {
                "code": section_code,
                "title": section_title,
                "description": section_paragraph,
                "indicators": {"not-achieved": not_achieved_dict, "partially-achieved": {}, "achieved": {}},
                "assessment-rules": "*standard",
            }
            section_index += 1

    objectives_dict = {}
    objective_index = 1
    for code, title, paragraph in objectives:
        objectives_dict[objective_index] = {
            "code": code,
            "title": title,
            "objective_description": paragraph,
            "principles": {},
        }
        objective_index += 1

    for principle_index, principle_data in principles_dict.items():
        objective_code = principle_data["code"][0]
        objective_index = next(
            (index for index, objective in objectives_dict.items() if objective["code"] == objective_code), None  # type: ignore
        )
        if objective_index is not None:
            objectives_dict[objective_index]["principles"][principle_index] = principle_data

    return {"assessment-rules: &standard-rules": assessment_rules, "objectives": objectives_dict}


def save_to_yaml(data: dict, filename: str = "cyber-assessment-framework-v3.2.yaml"):
    with open(filename, "w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )


if __name__ == "__main__":
    reader = PdfReader(PDF_PATH)
    objectives, sections, principle_headings = extract_text(reader)

    yaml_data = create_yaml_structure(objectives, sections, principle_headings)

    save_to_yaml(yaml_data)
