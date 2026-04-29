# Test Data Examples and Expected Output

## Complete Assessment Workflow

### 1. Input: Complete Assessment Data

```json
{
  "assessment_data": [
    {
      "key": "A1.a",
      "group_key": "G_A1.a",
      "org_comment": "Board actively oversees security",
      "achievement": "ACH"
    },
    {
      "key": "A1.a.1",
      "group_key": "G_A1.a",
      "answer": "Yes",
      "org_comment": "Board has documented security oversight"
    },
    {
      "key": "A1.a.2",
      "group_key": "G_A1.a",
      "answer": "Yes",
      "org_comment": "Security policies are board approved"
    },
    {
      "key": "A1.a.3",
      "group_key": "G_A1.a",
      "answer": "No",
      "org_comment": "Some oversight gaps identified"
    },
    {
      "key": "A1.a.4",
      "group_key": "G_A1.a",
      "answer": "No",
      "org_comment": "Not formally implemented"
    },
    {
      "key": "A1.a-SQ",
      "group_key": "G_A1.a",
      "answer": "Quarterly board meetings",
      "org_comment": ""
    },
    {
      "key": "A1.b",
      "group_key": "G_A1.b",
      "org_comment": "Risk management framework in place",
      "achievement": "PAC"
    },
    {
      "key": "B1.a",
      "group_key": "G_B1.a",
      "org_comment": "Classification scheme established",
      "achievement": "ACH"
    },
    {
      "key": "B1.a.1",
      "group_key": "G_B1.a",
      "answer": "Yes",
      "org_comment": "Policy document created"
    }
  ]
}
```

### 2. Definition Structure (Minimal)

```json
{
  "v3.0": {
    "assessment_version_id": "v3.0",
    "display_name": "CAF v3.0",
    "objectives": {
      "A": {
        "code": "A",
        "title": "Governance and risk management",
        "description": "Comprehensive security risk management",
        "principles": {
          "A1": {
            "code": "A1",
            "title": "Security governance",
            "description": "Establish governance framework",
            "outcomes": {
              "A1.a": {
                "code": "A1.a",
                "title": "Governance outcome",
                "description": "Effective governance in place",
                "indicators": {
                  "achieved": {
                    "A1.a.1": {
                      "description": "Board oversees security",
                      "ncsc-index": "A1.a.1"
                    },
                    "A1.a.2": {
                      "description": "Security policies approved",
                      "ncsc-index": "A1.a.2"
                    }
                  },
                  "partially-achieved": {
                    "A1.a.3": {
                      "description": "Partial oversight",
                      "ncsc-index": "A1.a.3"
                    }
                  },
                  "not-achieved": {
                    "A1.a.4": {
                      "description": "No formal governance",
                      "ncsc-index": "A1.a.4"
                    }
                  }
                },
                "external_links": {}
              },
              "A1.b": {
                "code": "A1.b",
                "title": "Risk management outcome",
                "description": "Risk management processes established",
                "indicators": {
                  "achieved": {},
                  "partially-achieved": {},
                  "not-achieved": {}
                },
                "external_links": {}
              }
            },
            "external_links": {}
          }
        }
      },
      "B": {
        "code": "B",
        "title": "Information security",
        "description": "Information security management",
        "principles": {
          "B1": {
            "code": "B1",
            "title": "Information classification",
            "description": "Classify information",
            "outcomes": {
              "B1.a": {
                "code": "B1.a",
                "title": "Classification outcome",
                "description": "Information properly classified",
                "indicators": {
                  "achieved": {
                    "B1.a.1": {
                      "description": "Classification policy exists",
                      "ncsc-index": "B1.a.1"
                    }
                  },
                  "partially-achieved": {},
                  "not-achieved": {}
                },
                "external_links": {}
              }
            },
            "external_links": {}
          }
        }
      }
    }
  }
}
```

### 3. Assessment Metadata

```json
{
  "hashed_assessment_id": "assess_12345",
  "hashed_organisation_id": "org_67890",
  "hashed_system_id": "sys_11111",
  "assessment_version_id": "v3.0",
  "system_profile": "Enhanced",
  "review_type": "Self-Assessment",
  "assessment_status_description": "Submitted",
  "assessment_version": "v3.0",
  "assessment_status_changed_to_submtd": "2026-03-15",
  "assessment_last_updated": "2026-03-15T10:30:00Z",
  "assessment_progress_organisation": "100",
  "assessment_review_type": "None",
  "assessment_progress_assessor": "0",
  "assessment_status_changed_to_aseing": null
}
```

### 4. Expected Output: Assessment Structure (Partial)

```json
{
  "A1.a": {
    "indicators": {
      "achieved_A1.a.1": true,
      "achieved_A1.a.1_comment": "Board has documented security oversight",
      "achieved_A1.a.2": true,
      "achieved_A1.a.2_comment": "Security policies are board approved",
      "partially-achieved_A1.a.3": false,
      "partially-achieved_A1.a.3_comment": "Some oversight gaps identified",
      "not-achieved_A1.a.4": false,
      "not-achieved_A1.a.4_comment": "Not formally implemented"
    },
    "supplementary_questions": [
      {
        "key": "A1.a-SQ",
        "answer": "Quarterly board meetings"
      }
    ],
    "confirmation": {
      "outcome_status": "Achieved",
      "confirm_outcome": "confirm",
      "outcome_status_message": "",
      "confirm_outcome_confirm_comment": "Board actively oversees security"
    }
  },
  "A1.b": {
    "indicators": {},
    "supplementary_questions": [],
    "confirmation": {
      "outcome_status": "Partially achieved",
      "confirm_outcome": "confirm",
      "outcome_status_message": "",
      "confirm_outcome_confirm_comment": "Risk management framework in place"
    }
  },
  "B1.a": {
    "indicators": {
      "achieved_B1.a.1": true,
      "achieved_B1.a.1_comment": "Policy document created"
    },
    "supplementary_questions": [],
    "confirmation": {
      "outcome_status": "Achieved",
      "confirm_outcome": "confirm",
      "outcome_status_message": "",
      "confirm_outcome_confirm_comment": "Classification scheme established"
    }
  },
  "meta_data": {
    "system_profile": "Enhanced",
    "review_type": "Self-Assessment",
    "assessment_status_description": "Submitted",
    "assessment_version": "v3.0",
    "assessment_status_changed_to_submtd": "2026-03-15",
    "assessment_last_updated": "2026-03-15T10:30:00Z",
    "assessment_progress_organisation": "100",
    "assessment_review_type": "None",
    "organisation": {
      "hashed_organisation_id": "org_67890",
      "name": "Test Organization",
      "sector": "Finance",
      "country": "UK"
    },
    "system": {
      "hashed_system_id": "sys_11111",
      "name": "Core Banking System",
      "description": "Main banking application",
      "organisation_id": "org_67890"
    }
  }
}
```

## Partial Assessment Workflow

### 1. Input: Partial Assessment Data

```json
{
  "assessment_data": [
    {
      "key": "A1.a",
      "group_key": "G_A1.a",
      "org_comment": "Partially implemented governance",
      "achievement": "PAC"
    },
    {
      "key": "A1.a.1",
      "group_key": "G_A1.a",
      "answer": "Yes",
      "org_comment": "Board exists but not formal"
    },
    {
      "key": "A1.a.3",
      "group_key": "G_A1.a",
      "answer": "No",
      "org_comment": "Gaps in oversight"
    }
  ]
}
```

**Note:** A1.a.2, A1.a.4, A1.b, and B1.a are NOT included

### 2. Expected Output: Partial Assessment Structure

```json
{
  "A1.a": {
    "indicators": {
      "achieved_A1.a.1": true,
      "achieved_A1.a.1_comment": "Board exists but not formal",
      "partially-achieved_A1.a.3": false,
      "partially-achieved_A1.a.3_comment": "Gaps in oversight"
    },
    "supplementary_questions": [],
    "confirmation": {
      "outcome_status": "Partially achieved",
      "confirm_outcome": "confirm",
      "outcome_status_message": "",
      "confirm_outcome_confirm_comment": "Partially implemented governance"
    }
  },
  "meta_data": {
    "system_profile": "Enhanced",
    "review_type": "Self-Assessment",
    "assessment_status_description": "Submitted",
    "assessment_version": "v3.0",
    "assessment_status_changed_to_submtd": "2026-03-15",
    "assessment_last_updated": "2026-03-15T10:30:00Z",
    "assessment_progress_organisation": "50",
    "assessment_review_type": "None",
    "organisation": {
      "hashed_organisation_id": "org_67890",
      "name": "Test Organization",
      "sector": "Finance",
      "country": "UK"
    },
    "system": {
      "hashed_system_id": "sys_11111",
      "name": "Core Banking System",
      "description": "Main banking application",
      "organisation_id": "org_67890"
    }
  }
}
```

**Key Differences from Complete:**
- Only A1.a present (A1.b and B1.a missing)
- Fewer indicators in A1.a (only 1 and 3, missing 2 and 4)
- No supplementary questions
- A1.a status is "Partially achieved" not "Achieved"

## Review Workflow

### 1. Input: Review/Assessor Data

```json
{
  "review_data": [
    {
      "key": "A1.a",
      "group_key": "G_A1.a",
      "achievement": "ACH",
      "assessor_achievement": "ACH",
      "assessor_comment": "Assessment is accurate. Evidence well documented."
    },
    {
      "key": "A1.a.1",
      "group_key": "G_A1.a",
      "assessor_answer": "Yes",
      "assessor_comment": "Confirmed through board meeting minutes"
    },
    {
      "key": "A1.a.2",
      "group_key": "G_A1.a",
      "assessor_answer": "Yes",
      "assessor_comment": "Policy signatures verified"
    },
    {
      "key": "A1.a.3",
      "group_key": "G_A1.a",
      "assessor_answer": "No",
      "assessor_comment": "Minor gaps noted, acceptable"
    },
    {
      "key": "A1.a.4",
      "group_key": "G_A1.a",
      "assessor_answer": "No",
      "assessor_comment": "Not formally required for this organization"
    },
    {
      "key": "A1.b",
      "group_key": "G_A1.b",
      "achievement": "PAC",
      "assessor_achievement": "PAC",
      "assessor_comment": "Risk processes exist but need refinement"
    }
  ]
}
```

### 2. Expected Output: Review Structure (Partial)

```json
{
  "A": {
    "A1.a": {
      "indicators": {
        "achieved_A1.a.1": "Yes",
        "achieved_A1.a.1_comment": "Confirmed through board meeting minutes",
        "achieved_A1.a.2": "Yes",
        "achieved_A1.a.2_comment": "Policy signatures verified",
        "partially-achieved_A1.a.3": "No",
        "partially-achieved_A1.a.3_comment": "Minor gaps noted, acceptable",
        "not-achieved_A1.a.4": "No",
        "not-achieved_A1.a.4_comment": "Not formally required for this organization"
      },
      "review_data": {
        "outcome_status": "Achieved",
        "review_decision": "Achieved",
        "review_comment": "Assessment is accurate. Evidence well documented."
      },
      "recommendations": []
    },
    "A1.b": {
      "indicators": {},
      "review_data": {
        "outcome_status": "Partially achieved",
        "review_decision": "Partially achieved",
        "review_comment": "Risk processes exist but need refinement"
      },
      "recommendations": []
    }
  },
  "meta_data": {
    "system_profile": "Enhanced",
    "review_type": "Self-Assessment",
    "assessment_status_description": "Submitted",
    "assessment_version": "v3.0",
    "assessment_status_changed_to_aseing": "2026-03-20",
    "assessment_last_updated": "2026-03-20T14:00:00Z",
    "assessment_progress_assessor": "100",
    "assessment_review_type": "Technical Review",
    "organisation": {
      "hashed_organisation_id": "org_67890",
      "name": "Test Organization",
      "sector": "Finance",
      "country": "UK"
    },
    "system": {
      "hashed_system_id": "sys_11111",
      "name": "Core Banking System",
      "description": "Main banking application",
      "organisation_id": "org_67890"
    }
  }
}
```

**Key Differences from Assessment:**
- Indicators contain strings ("Yes"/"No") instead of booleans
- review_data section instead of confirmation
- review_decision field (assessor's verdict)
- review_comment field (assessor's detailed feedback)
- recommendations array (for future implementation)

## Data Flow Comparison

### Complete Assessment Flow
```
Complete Assessment Data (9 items)
    ↓
Build Definition Structure (2 objectives, 3 outcomes, 4 indicators)
    ↓
Parse Assessment Data
    ├─ Group Comments: G_A1.a, G_A1.b, G_B1.a
    ├─ Outcomes: A1.a, A1.b, B1.a
    └─ Indicators: A1.a.1-4, B1.a.1
    ↓
Generate Assessment Structure
    ├─ A1.a: ACH (4 indicators, 1 supplementary question)
    ├─ A1.b: PAC (no indicators)
    └─ B1.a: ACH (1 indicator)
    ↓
Output: 3 complete outcomes + metadata
```

### Partial Assessment Flow
```
Partial Assessment Data (3 items)
    ↓
Build Definition Structure (same)
    ↓
Parse Assessment Data
    ├─ Group Comments: G_A1.a
    ├─ Outcomes: A1.a
    └─ Indicators: A1.a.1, A1.a.3
    ↓
Generate Assessment Structure
    └─ A1.a: PAC (2 indicators only)
    ↓
Output: 1 outcome + metadata
(A1.b and B1.a not generated as no data provided)
```

## Status Code Mapping Reference

```
Assessment Input → Output Status
ACH             → Achieved
P_ACH           → Partially achieved
N_ACH           → Not achieved
PAC             → Partially achieved
NAC             → Not achieved

Review Input → Output Decision
ACH          → achieved
PAC          → partially-achieved
NAC          → not-achieved
```

## Comment Aggregation Example

### Input: Multiple comments from group
```
Group key: "G_A1.a"
Comments:
  - "Board has quarterly meetings"
  - "Security policies approved"
  - "Formal governance established"
  - "Board has quarterly meetings" (duplicate)
```

### Output: Deduplicated and joined
```
"confirm_outcome_confirm_comment":
"Board has quarterly meetings\n\nSecurity policies approved\n\nFormal governance established"
```

All tests in the test suite validate these transformations.
