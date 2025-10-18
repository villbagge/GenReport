# src/genreport/relations.py
from __future__ import annotations

import re
from .ged import GedDocument
from .log import warn

# Match a trailing ", <digits>" at the end of the line to extract GED numeric id
_last_id_re = re.compile(r",\s*(\d+)\s*$")


def map_relation_label(doc: GedDocument, rid: str, line: str) -> str:
    """
    Map internal relation codes to presentation labels, using the related
    person's gender for parents. Emits the same warnings to stderr as before
    (now via log.warn, identical text).
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
                warn(f"⚠️  Warning: Unknown gender for parent ID {rel_id}")
                return "Förälder:"
        else:
            warn(f"⚠️  Warning: Could not parse parent ID from line '{line}'")
            return "Förälder:"
    return rid
