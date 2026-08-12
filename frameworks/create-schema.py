#!/usr/bin/env python3

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pypdf import PdfReader

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_NAME = "NCSC-Cyber-Assessment-Framework-4.0.pdf"
PDF_PATH = Path(SCRIPT_DIR, PDF_NAME)

section_heading_pattern = re.compile(r"\b([A-Z]\d\.[a-z]) ([A-Za-z,/() -]+)")
principle_heading_pattern = re.compile(r"\bPrinciple ([A-Z]\d) ([A-Za-z,/ ]+)\b")
objective_heading_pattern = re.compile(r"CAF - Objective ([A-Z]) . ([A-Za-z ]+)\b")


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


def extract_table(text: str, heading_match: re.Match, all_matches: list):
    """
    Extract statements from a CAF table.

    Returns:
    {
        "not_achieved": [...],
        "partially_achieved": [...],
        "achieved": [...]
    }
    """

    start = heading_match.end()

    next_heading_pos = len(text)
    current_pos = heading_match.start()

    for match in all_matches:
        if current_pos < match.start() < next_heading_pos:
            next_heading_pos = match.start()

    for principle_match in principle_heading_pattern.finditer(text):
        if current_pos < principle_match.start() < next_heading_pos:
            next_heading_pos = principle_match.start()

    section_text = text[start:next_heading_pos]

    not_pos = section_text.find("Not Achieved")
    if not_pos == -1:
        return None

    table_text = section_text[not_pos:]

    # Remove table headers
    for phrase_to_delete in (
        "Not Achieved",
        "Partially Achieved",
        "Achieved",
        "At least one of the following.+statements.+is.+true",
        "All the following statements.+are.+true",
        "All the following statements.+are.+true",
    ):
        table_text = re.sub(phrase_to_delete, "", table_text, flags=re.IGNORECASE | re.DOTALL)

    table_text = table_text.strip()

    # --------------------------------------------------------
    # Split into columns.
    #
    # Assumes columns are separated by an empty paragraph
    # (i.e. two consecutive newlines).
    # --------------------------------------------------------
    parts = [
        r"\n\s+\n",
        r"(?=Senior management have.+visibility.+of)",
        r"(?=Your organisational process.+ensures.+that.+security.+risks)",
        r"(?=Your organisational process.+ensures.+that.+security.+risks)",
        r"(?=You perform threat.+analysis)",
        r"(?=You perform detailed.+threat.+analysis)",
        r"(?=You validate that.+the.+security.+measures.+are.+effective)",
        r"(?=All assets relevant.+to.+the.+secure.+operation)",
        r"(?=You understand the.+general.+risks.+suppliers)",
        r"(?=You have a.+deep.+understanding.+of.+your.+supply.+chain)",
        r"(?=Your Your software supplier.+leverages+secure)",
        r"(?=Your software supplier\(s\).+leverages.+an.+established.+secure.+software.+development.+framework)",
        r"(?=Your policies,.+processes.+and.+procedures.+document)",
        r"(?=You fully document.+your.+security.+governance.+risk.+management.+approach)",
        r"(?=Most of your.+policies,.+processes.+and.+procedures)",
        r"(?=All your policies,.+processes.+and.+procedures.+are)",
        r"(?=Your process of.+initial.+identity.+verification.+reasonable.+level.+of.+confidence)",
        r"(?=Your process of.+initial.+identity.+verification.+high.+level.+of.+confidence)",
        r"(?=Only corporately owned.+and.+managed.+devices.+can.+access)",
        r"(?=All privileged operations.+performed.+from.+highly.+trusted.+devices)",
        r"(?=All privileged user.+access.+requires.+strong.+authentication)",
        r"(?=Privileged user access.+dedicated.+separate.+accounts)",
        r"(?=You follow a.+robust.+procedure.+to.+verify.+each.+user.+minimum.+required.+access.+rights)",
        r"(?=You follow a.+robust.+procedure.+to.+verify.+each.+user.+regularly.+audited)",
        r"(?=You have identified.+and.+catalogued.+all.+the.+data.+important)",
        r"(?=You have identified.+and.+catalogued.+all.+the.+data.+important)",
        r"(?=You have identified.+and.+protected.+all.+the.+data.+links)",
        r"(?=You have identified.+and.+protected.+all.+the.+data.+links)",
        r"(?=All copies of.+data.+important.+to.+the.+operation)",
        r"(?=All copies of.+data.+important.+to.+the.+operation)",
        r"(?=You know which.+mobile.+devices.+hold.+data.+important)",
        r"(?=Mobile devices that.+hold.+data.+are.+catalogued)",
        r"(?=Data important to.+the.+operations.+of.+network.+and.+information.+systems.+removed)",
        r"(?=You catalogue and.+track.+all.+devices.+that.+contain.+data.+important)",
        r"(?=You employ appropriate.+expertise.+to.+design.+network.+and.+information.+systems)",
        r"(?=You employ appropriate.+expertise.+to.+design.+network.+and.+information.+systems)",
        r"(?=You have identified.+and.+documented.+the.+assets.+that.+need.+to.+be.+carefully.+configured)",
        r"(?=You have identified,.+documented.+and.+actively.+manage)",
        r"(?=Your systems and.+devices.+supporting.+the.+operation.+only.+administered)",
        r"(?=Your systems and.+devices.+supporting.+the.+operation.+highly.+trusted.+devices)",
        r"(?=You maintain a.+current.+understanding.+of.+the.+exposure)",
        r"(?=You maintain a.+current.+understanding.+of.+the.+exposure)",
        r"(?=You know all.+network.+and.+information.+systems.+necessary.+to.+restore)",
        r"(?=You have business.+continuity.+and.+disaster.+recovery.+plans.+tested)",
        r"(?=Network and information.+systems.+supporting.+the.+operation.+logically.+separated)",
        r"(?=Network and information.+systems.+supporting.+the.+operation.+segregated)",
        r"(?=You have appropriately.+secured.+backups)",
        r"(?=Your comprehensive,.+automatic.+and.+tested.+backups)",
        r"(?=Your executive management.+understand.+and.+widely.+communicate)",
        r"(?=Your executive management.+clearly.+and.+effectively.+communicates)",
        r"(?=You have defined.+appropriate.+cyber.+security.+training)",
        r"(?=All people in.+your.+organisation.+follow.+appropriate.+cyber.+security.+training.+paths)",
        r"(?=Data relating to.+the.+security.+and.+operation.+of.+some.+areas)",
        r"(?=Monitoring is based.+on.+a.+thorough.+understanding)",
        r"(?=Only authorised users.+and.+systems.+can.+access.+log.+data)",
        r"(?=Appropriate access to.+log.+data.+is.+limited)",
        r"(?=You easily detect.+the.+presence.+of.+Indicators.+of.+Compromise)",
        r"(?=You easily detect.+the.+presence.+of.+Indicators.+of.+Compromise.+abnormalities)",
        r"(?=You investigate and.+triage.+alerts.+from.+some.+security.+tools)",
        r"(?=You investigate and.+triage.+alerts.+from.+all.+security.+tools)",
        r"(?=Monitoring and detection.+personnel.+have.+some.+investigative.+skills)",
        r"(?=You have monitoring.+and.+detection.+personnel.+who.+are.+responsible)",
        r"(?=You know how.+effective.+your.+threat.+intelligence.+is)",
        r"(?=You track the.+effectiveness.+of.+your.+threat.+intelligence)",
        r"(?=You have identified.+the.+resources.+required.+to.+perform.+threat.+hunting)",
        r"(?=You understand the.+resources.+required.+to.+perform.+threat.+hunting)",
        r"(?=Your incident response.+plan.+covers.+network.+and.+information.+systems)",
        r"(?=Your incident response.+plan.+is.+based.+on.+a.+clear.+understanding)",
        r"(?=You understand the.+resources.+that.+will.+likely.+be.+needed)",
        r"(?=Exercise scenarios are.+based.+on.+incidents.+experienced)",
        r"(?=Post incident analysis.+is.+conducted.+routinely)",
        r"(?=You have a.+documented.+incident.+review.+process.+policy)",
    ]
    columns = [c.strip() for c in re.split("|".join(parts), table_text, flags=re.DOTALL | re.MULTILINE) if c.strip()]

    def split_statements(column_text):
        return [
            c.strip().replace("\n", "")
            for c in re.split(r"\n(?=[A-Z][a-z]+ )", column_text, re.MULTILINE | re.DOTALL)
            if c.strip()
        ]

    result: dict[str, list[Any]] = {
        "not_achieved": [],
        "partially_achieved": [],
        "achieved": [],
    }

    if len(columns) == 2:
        result["not_achieved"] = split_statements(columns[0])
        result["achieved"] = split_statements(columns[1])

    elif len(columns) == 3:
        result["not_achieved"] = split_statements(columns[0])
        result["partially_achieved"] = split_statements(columns[1])
        result["achieved"] = split_statements(columns[2])

    else:
        # Fallback if the split didn't work
        result["not_achieved"] = split_statements(table_text)

    return result


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
    principle_index: int | None = 1
    for code, title, paragraph in principle_headings:
        principles_dict[principle_index] = {
            "code": code,
            "title": title,
            "description": paragraph,
            "outcomes": {},
        }
        if principle_index:
            principle_index += 1

    section_index = 1
    for section_code, section_title, section_paragraph, table_items in sections:
        indicator_index = 1
        principle_code = section_code[:2]
        principle_index = next(
            (index for index, principle in principles_dict.items() if principle["code"] == principle_code),
            None,
            # type: ignore
        )
        if principle_index is not None:
            not_achieved_dict = {}
            partially_achieved_dict = {}
            achieved_dict = {}
            for indicator_idx, statement in enumerate(table_items.get("not_achieved", []), start=1):
                not_achieved_dict[f"{section_code}.{indicator_index}"] = {
                    "description": statement,
                    "ncsc-index": f"{section_code}.NA.{indicator_idx}",
                }
                indicator_index += 1

            for indicator_idx, statement in enumerate(table_items.get("partially_achieved", []), start=1):
                partially_achieved_dict[f"{section_code}.{indicator_index}"] = {
                    "description": statement,
                    "ncsc-index": f"{section_code}.PA.{indicator_idx}",
                }
                indicator_index += 1

            for indicator_idx, statement in enumerate(table_items.get("achieved", []), start=1):
                achieved_dict[f"{section_code}.{indicator_index}"] = {
                    "description": statement,
                    "ncsc-index": f"{section_code}.A.{indicator_idx}",
                }
                indicator_index += 1

            principles_dict[principle_index]["outcomes"][section_code] = {
                "code": section_code,
                "title": section_title,
                "description": section_paragraph,
                "indicators": {
                    "partially-achieved": partially_achieved_dict,
                    "not-achieved": not_achieved_dict,
                    "achieved": achieved_dict,
                },
                "assessment-rules": "*standard",
            }
            section_index += 1

    objectives_dict = {}
    objective_index = 1
    for code, title, paragraph in objectives:
        objectives_dict[code] = {
            "code": code,
            "title": title,
            "description": paragraph,
            "principles": {},
        }
        objective_index += 1

    for principle_index, principle_data in principles_dict.items():
        objective_code = principle_data["code"][0]
        if objective_index is not None:
            objectives_dict[objective_code]["principles"][principle_data["code"]] = principle_data

    return {"assessment-rules: &standard-rules": assessment_rules, "objectives": objectives_dict}


def save_to_yaml(data: dict, filename: str = "cyber-assessment-framework-v4.0.1.yaml"):
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
