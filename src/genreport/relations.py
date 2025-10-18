# src/genreport/relations.py
from __future__ import annotations

import re
import sys
from .ged import GedDocument

# Match a trailing ", <digits>" at the end of the line to extract GED numeric id
_last_id_re = re.compile(r",\s*(\d+)\s*$")


def map_relation_label(doc: GedDocument, rid: str, line: str) -> str:
    """
    Map internal relation codes to presentation labels, using the related
    person's gender for parents. Emits the same warnings to stderr as before.
    Behavior is intentionally identical to the inlined logic we used to keep
    in mainexport.py.
    """
    rid_u = (rid or "").upper()
    if rid_u == "SPOUSE":
        return "Vigd:"
    if rid_u == "CHILD":
        return "Barn:"
    if rid_u == "PARENT":
        m = _last_id_re.search(line or "")
        if m:
            rel_id = m.group(1)
            gender = doc.get_gender_for_id(rel_id)
            if gender == "M":
                return "Far:"
            elif gender == "F":
                return "Mor:"
            else:
                print(f"⚠️  Warning: Unknown gender for parent ID {rel_id}", file=sys.stderr)
                return "Förälder:"
        else:
            print(f"⚠️  Warning: Could not parse parent ID from line '{line}'", file=sys.stderr)
            return "Förälder:"
    return rid
