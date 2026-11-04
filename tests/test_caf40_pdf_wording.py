from pathlib import Path
from unittest import TestCase

import yaml

CAF40_YAML = Path(__file__).resolve().parent.parent / "frameworks" / "cyber-assessment-framework-v4.0.yaml"

# Wording from frameworks/NCSC-Cyber-Assessment-Framework-4.0.pdf for the items that
# differed when the YAML was compared with the PDF (CS-527, corrected in CS-672).
EXPECTED_INDICATORS = {
    ("A2.b", "achieved", "A2.b.12"): (
        "You use appropriate techniques to develop an understanding of network and information "
        "systems supporting your essential function(s) from a threat actor's perspective. You "
        "anticipate probable attack methods and techniques, targets and objectives, and develop "
        "plausible scenarios."
    ),
    ("A2.b", "achieved", "A2.b.15"): (
        "You maintain a detailed understanding of current threats (e.g. by threat intelligence "
        "and proactive research)."
    ),
    ("A4.a", "achieved", "A4.a.12"): (
        "You consider factors such as your supplier's ownership, nationality, partnerships, "
        "competitors, other organisations with which they sub-contract and their approach to "
        "cyber security. These factors inform your risk assessment and are fully considered in "
        "your procurement lifecycle processes and purchasing decisions."
    ),
    ("B2.d", "partially-achieved", "B2.d.9"): (
        "All user, device and system access to the systems supporting the essential function(s) "
        "is logged and monitored, but it is not compared to other log data or access records."
    ),
    ("B2.d", "achieved", "B2.d.12"): (
        "All user, device and systems access to network and information systems supporting your "
        "essential function(s) is logged and monitored."
    ),
    ("C2.a", "partially-achieved", "C2.a.5"): (
        "You deploy an effective threat hunting capability but not frequent enough to match the "
        "risks posed to network and information systems supporting your essential function(s) "
        "(e.g. you perform threat hunts in response to a tip off from a reputable source)."
    ),
    ("D1.c", "achieved", "D1.c.7"): (
        "Exercises are routinely run, with the findings documented and used to refine incident "
        "response plans and protective security, in line with the lessons learned."
    ),
}

EXPECTED_B3_DESCRIPTION = (
    "Data stored or transmitted electronically is protected from actions such as unauthorised "
    "access, modification, or deletion that may cause an adverse impact on essential functions. "
    "Such protection extends to the means by which authorised users, devices and systems access "
    "critical data necessary for the operation of essential functions. It also covers information "
    "that would assist a threat actor, such as design details of network and information systems."
)

EXPECTED_C1F_TITLE = "Understanding User's and System's Behaviour, and Threat Intelligence (within Security Monitoring)"


class Caf40PdfWordingTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with CAF40_YAML.open(encoding="utf-8") as file:
            framework = yaml.safe_load(file)
        cls.principles = {
            code: principle
            for objective in framework["objectives"].values()
            for code, principle in objective["principles"].items()
        }
        cls.outcomes = {
            code: outcome for principle in cls.principles.values() for code, outcome in principle["outcomes"].items()
        }

    def test_indicator_statements_match_pdf(self):
        for (outcome, level, indicator), expected in EXPECTED_INDICATORS.items():
            with self.subTest(indicator=indicator):
                self.assertEqual(self.outcomes[outcome]["indicators"][level][indicator]["description"], expected)

    def test_principle_b3_description_matches_pdf(self):
        self.assertEqual(self.principles["B3"]["description"], EXPECTED_B3_DESCRIPTION)

    def test_outcome_c1f_title_matches_pdf(self):
        self.assertEqual(self.outcomes["C1.f"]["title"], EXPECTED_C1F_TITLE)
