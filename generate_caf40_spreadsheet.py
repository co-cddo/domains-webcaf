"""Generate the CAF 4.0 GovAssure self-assessment Excel template.

Builds the workbook from ``frameworks/cyber-assessment-framework-v4.0.yaml``
without the hidden JSON mapping sheet and writes it to the project root.

Usage:
    python generate_caf40_spreadsheet.py [output.xlsx]
"""

import sys
from pathlib import Path

import yaml

from webcaf.webcaf.utils.excel_exporter import build_assessment_template_workbook

PROJECT_ROOT = Path(__file__).resolve().parent
FRAMEWORK_PATH = PROJECT_ROOT / "frameworks" / "cyber-assessment-framework-v4.0.yaml"
DEFAULT_OUTPUT = PROJECT_ROOT / "caf40-assessment-template.xlsx"


def main() -> None:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    with open(FRAMEWORK_PATH) as file:
        framework = yaml.safe_load(file)
    workbook = build_assessment_template_workbook(framework, "caf40", include_json_map=False)
    workbook.save(output)
    print(f"Written {output}")


if __name__ == "__main__":
    main()
