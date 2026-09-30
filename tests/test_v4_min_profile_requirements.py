import csv
import unittest
from pathlib import Path

from ruamel.yaml import YAML

yaml = YAML()

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


class TestProfileRequirements(unittest.TestCase):

    def setUp(self):
        reader = csv.reader(V4_MIN_REQUIREMENTS.splitlines(), delimiter="\t")
        self.requirements = []
        for i, row in enumerate(reader):
            # Skip the header row
            if i <= 1:
                continue  # Skip the header row
            self.requirements.append(row)
        with open(Path(__file__).parent.parent / "frameworks/cyber-assessment-framework-v4.0.yaml", "r") as json_file:
            self.json_data = yaml.load(json_file)

    def test_v4_min_profile_requirements(self):
        self.assertEqual(len(self.requirements), 41)  # Expecting 41 requirement rows (excluding header)
        for row in self.requirements:
            with self.subTest(msg=f"Profile value check failed: {row[0]} - {row[1]}"):
                self.assertEqual(len(row), 4)  # Each row should have 4 columns
                self.assertIn(
                    row[2].strip(), ["Not Achieved", "Partially achieved", "Achieved"]
                )  # Basic Profile values
                self.assertIn(
                    row[3].strip(), ["Not Achieved", "Partially achieved", "Achieved"]
                )  # Enhanced Profile values
                min_profile_requirement_ = self.json_data["objectives"][row[0][0]]["principles"][row[0][:2]][
                    "outcomes"
                ][row[0].strip()]["min_profile_requirement"]
                self.assertEqual(min_profile_requirement_["baseline"], row[2].strip(), "Basic Profile value mismatch")
                self.assertEqual(
                    min_profile_requirement_["enhanced"], row[3].strip(), "Enhanced Profile value mismatch"
                )
