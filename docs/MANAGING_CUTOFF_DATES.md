# Managing Assessment Period Cutoff Dates

## Overview

The system automatically handles assessment period rollover using `Configuration` objects stored in the database. When a new assessment is created, the system selects the appropriate configuration based on the current date and time.

## How It Works

### Automatic Period Selection

1. The system compares the current date and time with the `assessment_period_end` attribute in each `Configuration` object
2. If the current date and time is **after** the `assessment_period_end`, the system automatically selects the next `Configuration` object closest to the current date and time
3. This ensures seamless transitions between assessment periods without manual intervention

### Default Configuration

As part of data seeding, the system automatically creates `Configuration` objects for the following periods:

| Period | Assessment Period End  | Default Framework |
|--------|------------------------|-------------------|
| 25/26  | 31 March 2026 11:59pm | caf32            |
| 26/27  | 31 March 2027 11:59pm | caf32            |

## Administrator Responsibilities

### Updating Configuration

System administrators must:

1. **Access the admin interface** at `/admin/`
2. Navigate to the Configuration section
3. Update the `assessment_period_end` and other relevant attributes as required
4. **Create new configuration entries** for upcoming assessment periods before the current period ends

### Important Notes

⚠️ **Critical:** Ensure new configuration entries are created well before the current period ends to avoid service disruption.

💡 **Tip:** Review and update configurations at the beginning of each assessment year to maintain smooth operations.
