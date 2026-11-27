"""The official ONS GSS codes of English councils and combined authorities.

The list is kept in ``webcaf/webcaf/data/council_gss_codes.csv``; docs/ORGANISATION_TYPES.md
names the ONS datasets it comes from and how to update it.
"""

import csv
from functools import cache
from pathlib import Path

COUNCIL_GSS_CODES_PATH = Path(__file__).resolve().parent.parent / "data" / "council_gss_codes.csv"


@cache
def official_council_gss_codes() -> frozenset[str]:
    with COUNCIL_GSS_CODES_PATH.open(newline="", encoding="utf-8") as csv_file:
        return frozenset(row["gss_code"] for row in csv.DictReader(csv_file))
