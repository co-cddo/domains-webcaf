# WebCAF Data Migration Tool

Migrate legacy WebCAF assessment data from the old format to the new analytics-compatible format.

## Overview

This migration tool transforms historical WebCAF CAF (Cyber Assessment Framework) assessment data into a structured format optimized for data analytics and reporting. The transformation maintains data integrity while restructuring the hierarchical assessment model.

## Data Structure

The WebCAF assessment framework follows this hierarchy:

```
Objectives (Top-level CAF goals: A, B, C, D)
  └─ Principles (Sub-categories: A1, A2, B1, etc.)
      └─ Contributing Outcomes (Specific outcomes: A1.a, A1.b, etc.)
          └─ Indicators (IGP - Indicators of Good Practice)
              └─ Achievement Levels:
                  • ACH (Achieved)
                  • PAC (Partially Achieved)
                  • NAC (Not Achieved)
```

### Example

```
A: Managing Security Risk (Objective)
  A1: Governance (Principle)
    A1.a: Roles and responsibilities (Contributing Outcome)
      A1.a.1: "The board has approved..." (Indicator - ACH)
      A1.a.2: "Clear lines of accountability..." (Indicator - PAC)
```

## Prerequisites

### Required Files

Copy the following files from the production GovAssure S3 bucket:

| Source File | Destination | Description |
|-------------|-------------|-------------|
| `assessments-combined/cos-igps/all.json.gz` | `data/assessments-combined/cos-igps/` | Combined COS and IGPs assessment data |
| `assessments-combined/overview/all.json.gz` | `data/assessments-combined/overview/` | Assessment metadata (status, dates, versions) |
| `assessment-definitions/*.gz` | `data/assessment-definitions/` | Assessment framework definitions by version |
| `hashed_ids/assessments.json.gz` | `data/hashed_ids/` | Assessment ID mappings |
| `hashed_ids/organisations.json.gz` | `data/hashed_ids/` | Organisation information |
| `hashed_ids/systems.json.gz` | `data/hashed_ids/` | System information |

### Directory Structure

Ensure the following directory structure exists:

```
webcaf/webcaf/utils/data-migration/
├── README.md
├── transform.py
└── data/
    ├── assessment-definitions/      # Assessment framework definitions
    ├── assessments-combined/
    │   ├── cos-igps/               # Raw assessment data
    │   └── overview/               # Assessment metadata
    ├── hashed_ids/                 # ID mappings
    └── assessments-transformed/    # Output directory (auto-created)
```

## Usage

### Running the Transformation

```bash
cd webcaf/webcaf/utils/data-migration
python transform.py
```

### Output

The script generates two files per assessment:

1. **`{assessment_id}.json`**: Transformed assessment data with organization responses
2. **`{assessment_id}-review.json`**: Transformed review data with assessor feedback

Both files are written to `data/assessments-transformed/`

### Progress Monitoring

The script outputs progress information:

```
Loading assessments data...
Assessment data loaded
Loading assessments meta data...
Assessment meta data loaded
Loading assessments data...
Loading organisations data...
Loading systems data...
Following assessments were not found count: X
Assessment not found {assessment_id}
```

## Transformation Process

### 1. Definition Structure Building

Reads compressed assessment definition files and builds a hierarchical structure of the CAF framework.

**Input**: `data/assessment-definitions/*.gz`

**Output**: In-memory definition structure keyed by `assessment_version_id`

### 2. Data Parsing

Extracts and categorizes data from legacy format:

- **Group comments**: Comments grouped by question groups
- **Outcomes**: Outcome-level data (key format: `A1.a`)
- **Indicators**: Indicator-level data (key format: `A1.a.1`)
- **Supplementary questions**: Additional questions marked with `-SQ` suffix

### 3. Assessment Structure Generation

Transforms parsed data into new format:

- Processes indicators by achievement type
- Collects and deduplicates comments from multiple sources
- Maps outcome statuses (Achieved/Partially achieved/Not achieved)
- Generates metadata (organisation, system, version, dates)

**Output structure**:
```json
{
  "A1.a": {
    "indicators": {
      "achieved_A1.a.1": true,
      "achieved_A1.a.1_comment": "...",
      "partially-achieved_A1.a.2": false,
      "partially-achieved_A1.a.2_comment": "..."
    },
    "supplementary_questions": [...],
    "confirmation": {
      "outcome_status": "Achieved",
      "confirm_outcome": "confirm",
      "confirm_outcome_confirm_comment": "..."
    }
  },
  "meta_data": {
    "organisation": {...},
    "system": {...},
    "assessment_version": "...",
    "review_type": "..."
  }
}
```

### 4. Review Structure Generation

Similar to assessment generation but focuses on assessor/reviewer data:

- Includes review decisions and assessor comments
- Captures both organization responses and assessor evaluations
- Generates recommendations structure

## Key Features

- **Complexity Reduction**: Code refactored to reduce cyclomatic complexity (C901 compliance)
- **Error Handling**: Gracefully handles missing indicators with error logging
- **Comment Deduplication**: Automatically removes duplicate comments
- **Multi-version Support**: Handles multiple CAF framework versions
- **Idempotent**: Can be run multiple times safely

## Troubleshooting

### Missing Assessments

If assessments are not found, verify:

1. All required `.gz` files are present in their respective directories
2. File names match exactly (case-sensitive)
3. Files are valid gzip-compressed JSON

### Indicator Not Found Errors

```
Indicator is not found: Indicator entry not found for ID: A1.a.1
```

This is expected for historical data where some indicators may not have been answered. The script continues processing.

## Notes

- The transformation preserves all original data integrity
- Output files use 4-space indentation for readability
- Assessment IDs are hashed for privacy
- Missing assessments are logged at the end of execution
