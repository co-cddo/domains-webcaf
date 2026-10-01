"""
Module for processing and updating a YAML-based cyber assessment framework file.

This module reads a YAML file, modifies its content based on predefined minimum
requirements, and writes the updated content back to the file. The module parses
a hard-coded list of minimum requirements defined in a tab-delimited string and
maps them to the appropriate sections of the YAML data structure. It also performs
status mapping and validation to ensure the consistency of the data.

Attributes:
    yaml (ruamel.yaml.YAML): Configured instance of the YAML parser with specific
        indentation, flow style, and width settings.
    V4_MIN_REQUIREMENTS (str): Tab-delimited string representing the predefined
        minimum requirements for the cyber assessment framework.

Raises:
    ValueError: If an unexpected value is encountered for status mapping during
        processing.
"""

import csv
from pathlib import Path

from ruamel.yaml import YAML

yaml = YAML()
yaml.preserve_quotes = True
yaml.default_flow_style = False
yaml.indent(
    mapping=2,
    sequence=2,
    offset=2,
)

yaml.width = 90

# taken from the CAF v4.0 spreadsheet, tab-delimited for easier parsing
# https://www.security.gov.uk/policy-and-guidance/govassure/govassure-government-caf-profiles/
V4_MIN_REQUIREMENTS = """
Contributing outcome number 	Contributing outcome name 	Basic Profile 	Enhanced Profile
A1.a 	Board direction 	Achieved 	Achieved
A1.b 	Roles and responsibilities 	Achieved 	Achieved
A1.c 	Decision-making 	Achieved 	Achieved
A2.a 	Risk management process 	Partially achieved 	Achieved
A2.b 	Understanding threat 	Achieved 	Achieved
A2.c 	Assurance 	Achieved 	Achieved
A3.a 	Asset management 	Achieved 	Achieved
A4.a 	Supply chain 	Achieved 	Achieved
A4.b 	Secure software development and support 	Partially achieved 	Partially achieved
B1.a 	Policy, process and procedure development 	Partially achieved 	Achieved
B1.b 	Policy, process and procedure implementation 	Partially achieved 	Achieved
B2.a 	Identity verification, authentication and authorisation 	Achieved 	Achieved
B2.b 	Device management 	Partially achieved 	Achieved
B2.c 	Privileged user management 	Achieved 	Achieved
B2.d 	Identity and access management (IdAM) 	Achieved 	Achieved
B3.a 	Understanding data 	Partially achieved 	Partially achieved
B3.b 	Data in transit 	Partially achieved 	Achieved
B3.c 	Stored data 	Partially achieved 	Partially achieved
B3.d 	Mobile data 	Partially achieved 	Partially achieved
B3.e 	Media / equipment sanitisation 	Achieved 	Achieved
B4.a 	Secure by design 	Achieved 	Achieved
B4.b 	Secure configuration 	Partially achieved 	Achieved
B4.c 	Secure management 	Achieved 	Achieved
B4.d 	Vulnerability management 	Partially achieved 	Achieved
B5.a 	Resilience preparation 	Partially achieved 	Achieved
B5.b 	Design for resilience 	Partially achieved 	Partially achieved
B5.c 	Backups 	Partially achieved 	Achieved
B6.a 	Cyber security culture 	Partially achieved 	Partially achieved
B6.b 	Cyber security training 	Achieved 	Achieved
C1.a 	Sources and tools for logging and monitoring 	Achieved 	Achieved
C1.b 	Securing logs 	Partially achieved 	Achieved
C1.c 	Generating alerts 	Achieved 	Achieved
C1.d 	Triage of security alerts 	Partially achieved 	Achieved
C1.e 	Personnel skills for monitoring and detection 	Partially achieved 	Achieved
C1.f 	Understanding user’s and system’s behaviour, and threat intelligence (within security monitoring) 	Partially achieved 	Achieved
C2.a 	Threat hunting 	Achieved 	Achieved
D1.a 	Response plan 	Achieved 	Achieved
D1.b 	Response and recovery capability 	Achieved 	Achieved
D1.c 	Testing and exercising 	Achieved 	Achieved
D2.a 	Post incident analysis 	Achieved 	Achieved
D2.b 	Using incidents to drive improvements 	Achieved 	Achieved
"""
with open(Path(__file__).parent / "cyber-assessment-framework-v4.0.yaml", "r") as json_file:
    json_data = yaml.load(json_file)

reader = csv.reader(V4_MIN_REQUIREMENTS.splitlines(), delimiter="\t")
for row in reader:
    outcome = json_data["objectives"][row[0][0]]["principles"][row[0][:2]]["outcomes"][row[0].strip()]
    min_profile_requirement = outcome["min_profile_requirement"]

    def mapping(value):
        statuses_ = json_data["indicator_statuses"]
        if value == "Not Achieved":
            return statuses_[2]
        elif value == "Partially achieved":
            return statuses_[1]
        elif value == "Achieved":
            return statuses_[0]
        else:
            raise ValueError(f"Unexpected value: {value}")

    min_profile_requirement["baseline"] = mapping(row[2].strip())
    min_profile_requirement["enhanced"] = mapping(row[3].strip())

with open(Path(__file__).parent / "cyber-assessment-framework-v4.0.yaml", "w") as json_file:
    yaml.dump(json_data, json_file)
