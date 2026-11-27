# Organisation types and council subtypes

LG WebCAF has three organisation types, set in Django Admin:

| Type | Stored value | GSS code |
|---|---|---|
| Council | `council` | Required: a unique GSS code from the official ONS list of English councils and combined authorities (see below) |
| MHCLG | `mhclg` | Optional, usually blank |
| Independent assurer | `independent-assurer` | Optional, usually blank |

Combined authorities are stored as councils. Their GSS code identifies them.

## Council subtype

A council's subtype is not stored. It is worked out from the first three characters of its GSS code, using
`Organisation.COUNCIL_SUBTYPES_BY_GSS_PREFIX` in `webcaf/webcaf/models.py`, which is the only place the mapping is kept.

| GSS prefix | Council subtype | Example |
|---|---|---|
| E06 | Unitary authority | E06000014 City of York |
| E07 | Non-metropolitan district | E07000110 Maidstone |
| E08 | Metropolitan district | E08000035 Leeds |
| E09 | London borough | E09000033 Westminster |
| E10 | County council | E10000016 Kent |
| E47 | Combined authority | E47000003 West Yorkshire |

Every code in the official list has one of these prefixes, so every council has a subtype. The subtype is read-only: it
is shown in Django Admin (the organisation list and form) and on My organisation, and changes only when the GSS code
changes.

## Official council GSS codes

A council's GSS code must be in `webcaf/webcaf/data/council_gss_codes.csv`, the official ONS list of English councils
and combined authorities. Any other code, including a code with an unsupported prefix (for example `E99000001`), an
unassigned code with a supported prefix (for example `E08000099`) or a code from outside England, is refused with
"<code> is not the GSS code of an English council or combined authority in the ONS list". The rule is checked whenever an
organisation is saved, so it applies to Django Admin and imports alike. MHCLG and independent assurer organisations are
not checked.

The list has 332 codes, taken from the ONS Open Geography Portal names-and-codes datasets (English codes only):

| ONS dataset | Codes | Count |
|---|---|---|
| `LAD_APR_2025_UK_NC_v2` (Local Authority Districts, April 2025) | E06, E07, E08, E09 | 63 + 164 + 36 + 33 |
| `CTY_DEC_2025_EN_NC` (Counties, December 2025) | E10 | 21 |
| `CAUTH_MAY_2025_EN_NC` (Combined Authorities, May 2025) | E47 | 15 |

The file's `source` column records the dataset for each code.

### Updating the list

When ONS publishes new codes (usually each April, and after any local government reorganisation):

1. Download the new names-and-codes datasets from the ONS Open Geography Portal
   (`https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services`), keeping English (`E`) codes only.
2. Replace the rows in `council_gss_codes.csv`, setting `source` to each dataset's name.
3. Update the counts above and in `tests/test_models/test_organisation.py`.
4. Check existing councils: a council whose code is no longer on the list cannot be saved until its code is updated.

## Organisation identifier

Organisations have no generated reference. The organisation id (the database primary key) identifies an organisation
wherever an identifier is needed: in the Django Admin list, in the `Organisation ID` column of the organisation CSV
import, and in the data export file name.

## Data export changes (CS-680)

`python manage.py export_data` writes one JSON file per organisation, for every organisation type, to
`organisations/<id>.json`, where `<id>` is the organisation id (the same value as `organisation_id` in the file). This is
the LG WebCAF export format; the file names of the inherited central-government WebCAF export do not apply. Compared
with the format before CS-680:

| What | Before | Now |
|---|---|---|
| File name | `organisations/<reference>.json`, using the generated 5-character reference | `organisations/<id>.json`, using the organisation id |
| `organisation_type` | One of the inherited central-government type labels, Council, Combined authority or Other | `Council`, `MHCLG` or `Independent assurer`, or `null` if no type is set |
| `parent_organisation_id`, `parent_organisation_name` | Present | Removed |

The other fields (`organisation_name`, `organisation_id`, `app_version`, `legacy_organisation_id`) are unchanged. The
contact name, email and role were never exported. The analysis data built from the export
(`webcaf/webcaf/utils/data_analysis.py`) no longer has the parent organisation fields.
