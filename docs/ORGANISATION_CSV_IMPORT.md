# Organisation CSV import

## Purpose

The Django admin import creates organisation records. It does not create or update users, user profiles, organisation memberships, or role assignments.

User onboarding, including invitations and claiming a council, is handled separately.

## Access

Open `/admin/webcaf/organisation/` and select **Import Organisations from CSV**. A blank template is available from
the import page or `/admin/webcaf/organisation/import-org-csv-template/`.

## Current organisation import headers

The CSV must contain exactly these headers. Their order does not matter:

```csv
Organisation,Lead Government Department,Organisation ID,Type
```

- `Organisation` (required): name of the organisation.
- `Lead Government Department` (optional): accepted but ignored. Organisations no longer have a parent organisation.
- `Organisation ID` (optional): the ID of an existing WebCAF organisation, as shown in the Django Admin organisation
  list, used for matching. Leave it blank for a new organisation.
- `Type` (required): organisation type label (see below).

Example:

```csv
Organisation,Lead Government Department,Organisation ID,Type
"Ministry of Housing, Communities and Local Government",,,MHCLG
Example Assurance Ltd,,,Independent assurer
```

## Legacy Reference column

Organisations no longer have a generated reference (CS-680). A file with a `Reference` column is rejected before any
rows are processed, with a message pointing to the `Organisation ID` column. Old references can be all digits, so they
are never read as organisation IDs.

## Legacy email columns

`Email1`, `Email2`, `Email3`, `Email4`, `Email5`, and `Email6` are not part of the current organisation import headers. If any
of these columns is present, the entire import is rejected before any rows are processed. The validation message
identifies each unsupported column and displays the current headers.

Email addresses in legacy columns are not stored. The import does not use them to create or update users,
`UserProfile` records, memberships, or roles.

## Import behaviour

For each valid row, the importer:

1. Looks for an existing organisation by `Organisation ID`, when supplied.
2. Falls back to matching by `Organisation` name.
3. Creates the organisation when no match is found.
4. Sets the organisation type on new records.

Existing users and profiles, including records created by earlier imports, are not changed or removed.

## Organisation type values

The `Type` column accepts these case-sensitive labels:

- MHCLG
- Independent assurer

A row with a blank, removed or unrecognised type is rejected. The whole file is rejected before any records are written,
and the message lists each row to correct.

Council records, including combined authorities, are not supported by this organisation import because they require a
GSS code. If a row specifies the Council type, or matches an existing council, the entire file is rejected before any
records are written. These records must be managed through the dedicated council import or Django Admin.

## Validation

- The header must match the current organisation import headers exactly, although column order may differ.
- Duplicate headers are rejected before any rows are imported.
- Legacy `Email1` to `Email6` columns produce a specific unsupported-column error.
- A `Reference` column produces a specific unsupported-column error.
- Council rows are rejected before any rows are imported.
- Rows with a blank, removed or unrecognised `Type` are rejected, with each row listed.
- An `Organisation ID` that is not the ID of an existing organisation is rejected, with each row listed.
- Validation failures reject the file before organisation processing begins.
- A successful import reports the number of organisation rows processed.
