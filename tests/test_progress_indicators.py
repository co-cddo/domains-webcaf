from unittest import TestCase
from unittest.mock import patch

from webcaf.webcaf.models import Assessment, System
from webcaf.webcaf.templatetags.form_extras import (
    generate_assessment_progress_indicators,
)

caf_test_data = [
    {
        "code": "A",
        "title": "Managing security risk",
        "description": "Appropriate organisational structures, policies, processes and procedures in place to understand, assess and systematically manage security risks...",
        "principles": {
            "A1": {
                "code": "A1",
                "title": "Governance",
                "description": "The organisation has appropriate management policies, processes and procedures in place to govern its approach...",
                "outcomes": {
                    "A1.a": {
                        "code": "A1.a",
                        "title": "Board Direction",
                        "description": "You have effective organisational security management led at board level...",
                        "assessment_questions": [
                            "Is the organisation's security policy for essential functions formally owned and managed at the board level, and is it communicated effectively to risk managers?",
                            "How regularly is the security of network and information systems that support essential functions discussed and formally reported on at the board level?",
                        ],
                        "indicators": {
                            "partially-achieved": {},
                            "not-achieved": {
                                "A1.a.1": {
                                    "description": "The security of network and information systems... is not discussed or reported on regularly at board- level.",
                                    "ncsc-index": "A1.a.NA.1",
                                }
                            },
                            "achieved": {
                                "A1.a.5": {
                                    "description": "Your organisation's approach and policy... are owned and managed at board-level.",
                                    "ncsc-index": "A1.a.A.1",
                                }
                            },
                        },
                    }
                },
            }
        },
        "type": "objective",
        "short_name": "caf32_objective_A",
        "parent": None,
    },
    {
        "code": "B",
        "title": "Protecting against cyber attack",
        "description": "Proportionate security measures are in place to protect the network and information systems...",
        "principles": {
            "B1": {
                "code": "B1",
                "title": "Service Protection Policies, Processes and Procedures",
                "description": "The organisation defines, implements, communicates and enforces appropriate policies...",
                "outcomes": {
                    "B1.a": {
                        "code": "B1.a",
                        "title": "Policy, Process and Procedure Development",
                        "description": "You have developed and continue to improve a set of cyber security and resilience policies...",
                        "assessment_questions": [
                            "Can you demonstrate that you have a complete and fully documented security governance and risk management approach, including policies and processes?",
                            "What happens if security policies are not followed? Are they often circumvented to achieve business objectives, or are they consistently enforced?",
                        ],
                        "indicators": {
                            "not-achieved": {
                                "B1.a.1": {
                                    "description": "Your policies, processes and procedures are absent or incomplete.",
                                    "ncsc-index": "B1.a.NA.1",
                                }
                            },
                            "partially-achieved": {
                                "B1.a.8": {
                                    "description": "Your policies, processes and procedures document your overarching security governance...",
                                    "ncsc-index": "B1.a.PA.1",
                                }
                            },
                            "achieved": {
                                "B1.a.10": {
                                    "description": "You fully document your overarching security governance and risk management approach...",
                                    "ncsc-index": "B1.a.A.1",
                                }
                            },
                        },
                    }
                },
            }
        },
        "type": "objective",
        "short_name": "caf32_objective_B",
        "parent": None,
    },
    {
        "code": "C",
        "title": "Detecting cyber security events",
        "description": "Capabilities exist to ensure security defences remain effective and to detect cyber security events...",
        "principles": {
            "C1": {
                "code": "C1",
                "title": "Security Monitoring",
                "description": "The organisation monitors the security status of the network and information systems...",
                "outcomes": {
                    "C1.a": {
                        "code": "C1.a",
                        "title": "Monitoring Coverage",
                        "description": "The data sources that you include in your monitoring allow for timely identification of security events...",
                        "assessment_questions": [
                            "Is your security monitoring based on a clear understanding of your network architecture and common cyber-attack methods?",
                            "Do you actively collect security and operational data related to your essential functions, or is this data collection incomplete or absent?",
                        ],
                        "indicators": {
                            "not-achieved": {
                                "C1.a.1": {
                                    "description": "Data relating to the security and operation of your essential function(s) is not collected.",
                                    "ncsc-index": "C1.a.NA.1",
                                }
                            },
                            "partially-achieved": {
                                "C1.a.5": {
                                    "description": "Data relating to the security and operation of some areas of your essential function(s) is collected but coverage is not comprehensive.",
                                    "ncsc-index": "C1.a.PA.1",
                                }
                            },
                            "achieved": {
                                "C1.a.9": {
                                    "description": "Monitoring is based on an understanding of your networks, common cyber attack methods...",
                                    "ncsc-index": "C1.a.A.1",
                                }
                            },
                        },
                    }
                },
            }
        },
        "type": "objective",
        "short_name": "caf32_objective_C",
        "parent": None,
    },
    {
        "code": "D",
        "title": "Minimising the impact of cyber security incidents",
        "description": "Capabilities exist to minimise the adverse impact of a cyber security incident on the operation of essential functions...",
        "principles": {
            "D1": {
                "code": "D1",
                "title": "Response and Recovery Planning",
                "description": "There are well-defined and tested incident management processes in place...",
                "outcomes": {
                    "D1.a": {
                        "code": "D1.a",
                        "title": "Response Plan",
                        "description": "You have an up-to-date incident response plan that is grounded in a thorough risk assessment...",
                        "assessment_questions": [
                            "Is your incident response plan based on a thorough understanding of security risks to the network and systems supporting your essential functions?",
                            "Is the incident response plan fully documented, and has it been shared with all relevant staff and stakeholders?",
                        ],
                        "indicators": {
                            "not-achieved": {
                                "D1.a.1": {
                                    "description": "Your incident response plan is not documented.",
                                    "ncsc-index": "D1.a.NA.1",
                                }
                            },
                            "partially-achieved": {
                                "D1.a.4": {
                                    "description": "Your incident response plan covers your essential function(s).",
                                    "ncsc-index": "D1.a.PA.1",
                                }
                            },
                            "achieved": {
                                "D1.a.8": {
                                    "description": "Your incident response plan is based on a clear understanding of the security risks to the network...",
                                    "ncsc-index": "D1.a.A.1",
                                }
                            },
                        },
                    }
                },
            }
        },
        "type": "objective",
        "short_name": "caf32_objective_D",
        "parent": None,
    },
]


@patch("webcaf.webcaf.caf.routers.CAFLoader.get_sections")
class TestProgressIndicators(TestCase):
    def test_generate_assessment_progress_indicators(self, mock_get_sections):
        expected_progress_indicators = {
            "percentage": 50,
            "question_number": "1",
            "principles_in_section": 1,
            "principle": "C1",
            "principle_name": "Security Monitoring",
        }
        # get the smaller test caf data
        mock_get_sections.return_value = caf_test_data
        test_assessment = Assessment(
            status="draft",
            system=System(name="test_db"),
            assessments_data={
                "A.1.a": {"confirmation": {"outcome_status": "Achieved", "confirm_outcome": "confirm"}},
                "B.1.a": {"confirmation": {"outcome_status": "Achieved", "confirm_outcome": "confirm"}},
                "C.1.a": {"confirmation": {"outcome_status": "Achieved"}},
            },
        )
        test_progress_indicators = generate_assessment_progress_indicators(
            assessment=test_assessment, principle_question="C1.a.1"
        )

        for key, value in test_progress_indicators.items():
            self.assertEqual(expected_progress_indicators[key], value)
