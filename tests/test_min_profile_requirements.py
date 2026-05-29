from unittest import TestCase

import yaml

ALLOWED_PROFILE_VALUES = {"Achieved", "Partially Achieved", "Not Achieved"}


def parse_caf_spec(spec: str) -> dict[str, dict[str, str]]:
    """
    Parse a Common Assessment Framework (CAF) min profile specification string into a dictionary.

    :param spec: The CAF specification string.
    :return: A dictionary mapping contributing outcome numbers to their details.
    """
    lines = [line for line in spec.strip().splitlines() if line.strip()]
    headers = [h.strip() for h in lines[0].split("\t")]
    result: dict[str, dict[str, str]] = {}
    for line in lines[1:]:
        cells = [c.strip() for c in line.split("\t")]
        row = dict(zip(headers, cells))
        for col in ("Baseline Profile", "Enhanced Profile"):
            if row[col] not in ALLOWED_PROFILE_VALUES:
                raise ValueError(f"Invalid {col} value {row[col]!r} for {row[headers[0]]}")
        result[row[headers[0]]] = {
            "Contributing Outcome name": row["Contributing Outcome name"],
            "Baseline Profile": row["Baseline Profile"],
            "Enhanced Profile": row["Enhanced Profile"],
        }
    return result


NCSC_CAF32_SPEC = """
Contributing Outcome number	Contributing Outcome name	Baseline Profile	Enhanced Profile
A1.a	Board Direction	Achieved	Achieved
A1.b	Roles & Responsibilities	Achieved	Achieved
A1.c	Decision-making	Achieved	Achieved
A2.a	Risk Management Process	Partially Achieved	Achieved
A2.b	Assurance	Achieved	Achieved
A3.a	Asset Management	Achieved	Achieved
A4.a	Supply Chain	Partially Achieved	Achieved
B1.a	Policy & Process Development	Partially Achieved	Partially Achieved
B1.b	Policy & Process Implementation	Partially Achieved	Partially Achieved
B2.a	Identity Verification, Authentication and Authorisation	Partially Achieved	Achieved
B2.b	Device Management	Partially Achieved	Achieved
B2.c	Privileged User Management	Partially Achieved	Achieved
B2.d	Identity & Access Management (IdAM)	Partially Achieved	Achieved
B3.a	Understanding Data	Partially Achieved	Partially Achieved
B3.b	Data in Transit	Partially Achieved	Partially Achieved
B3.c	Stored Data	Partially Achieved	Partially Achieved
B3.d	Mobile Data	Partially Achieved	Partially Achieved
B3.e	Media/Equipment Sanitisation	Partially Achieved	Achieved
B4.a	Secure By Design	Partially Achieved	Partially Achieved
B4.b	Secure Configuration	Partially Achieved	Achieved
B4.c	Secure Management	Partially Achieved	Partially Achieved
B4.d	Vulnerability Management	Partially Achieved	Partially Achieved
B5.a	Resilience Preparation	Partially Achieved	Partially Achieved
B5.b	Design for Resilience	Partially Achieved	Partially Achieved
B5.c	Backups	Partially Achieved	Achieved
B6.a	Cyber Security Culture	Partially Achieved	Partially Achieved
B6.b	Cyber Security Training	Partially Achieved	Partially Achieved
C1.a	Monitoring Coverage	Partially Achieved	Achieved
C1.b	Securing Logs	Partially Achieved	Achieved
C1.c	Generating Alerts	Partially Achieved	Achieved
C1.d	Identifying Security Incidents	Partially Achieved	Achieved
C1.e	Monitoring Tools & Skills	Partially Achieved	Achieved
C2.a	System Abnormalities for Attack Detection	Not Achieved	Not Achieved
C2.b	Proactive Attack Discovery	Not Achieved	Not Achieved
D1.a	Response Plan	Achieved	Achieved
D1.b	Response & Recovery Capability	Achieved	Achieved
D1.c	Testing & Exercising	Achieved	Achieved
D2.a	Incident Root Cause Analysis	Achieved	Achieved
D2.b	Using Incidents to Drive Improvements	Achieved	Achieved
"""


class TestMinProfileRequirements(TestCase):
    """Test suite for minimum profile requirements validation."""

    def test_caf_32_requirements(self):
        """
        Validate that the ``min_profile_requirement`` for every outcome in
        ``frameworks/cyber-assessment-framework-v3.2.yaml`` matches the NCSC
        CAF v3.2 specification declared in ``NCSC_CAF32_SPEC``.

        For each outcome, three independent checks run as separate subTests so
        that a single mismatch does not short-circuit the rest of the suite:

        * the outcome code appears in the NCSC specification,
        * the baseline profile requirement matches, and
        * the enhanced profile requirement matches.
        """
        ncsc_spec = parse_caf_spec(NCSC_CAF32_SPEC)
        with open("frameworks/cyber-assessment-framework-v3.2.yaml", "r") as file:
            framework_data = yaml.safe_load(file)

        for objective in framework_data["objectives"].values():
            for principle in objective["principles"].values():
                for outcome_code, outcome in principle["outcomes"].items():
                    ncsc_requirement = ncsc_spec.get(outcome_code)
                    min_profile_requirement = outcome["min_profile_requirement"]

                    with self.subTest(outcome=outcome_code, check="present in NCSC spec"):
                        self.assertIsNotNone(
                            ncsc_requirement,
                            f"{outcome_code} is missing from NCSC_CAF32_SPEC",
                        )
                    if ncsc_requirement is None:
                        continue

                    with self.subTest(outcome=outcome_code, check="baseline"):
                        self.assertEqual(
                            ncsc_requirement["Baseline Profile"].lower(),
                            min_profile_requirement["baseline"].lower(),
                        )

                    with self.subTest(outcome=outcome_code, check="enhanced"):
                        self.assertEqual(
                            ncsc_requirement["Enhanced Profile"].lower(),
                            min_profile_requirement["enhanced"].lower(),
                        )
