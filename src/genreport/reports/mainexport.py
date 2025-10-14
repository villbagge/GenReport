# === GENREPORT HEADER START ===
# GenReport — v0.3.0
# Commit: Add Swedish role labels and gender-aware parent output
# Date: 2025-10-14
# Files: mainexport.py
# Changes:
#   - OCCU -> Syssla:
#   - SPOUSE -> Gift:
#   - CHILD -> Barn:
#   - PARENT -> Far:/Mor: depending on gender (warning if unknown)
# === GENREPORT HEADER END ===

from __future__ import annotations
import re
from pathlib import Path
import sys

from ..ged import GedDocument

# compact multi-line values to one line
_flatten_re = re.compile(r"\s*\n\s*")

def _flatten(text: str) -> str:
    return _flatten_re.sub(" / ", (text or "").strip())

def _is_email_line(fid: str, desc: str, content: str) -> bool:
    f = (fid or "").upper()
    d = (desc or "").lower()
    c = (content or "")
    return (
        "EMAIL" in f
        or "email" in d
        or c.strip().upper() == "EMAIL"
        or "@" in c
    )

def _is_media_line(fid: str, desc: str) -> bool:
    f = (fid or "").upper()
    d = (desc or "").lower()
    if "OBJE" in f or ".FILE" in f or ".FORM" in f:
        return True
    if any(x in d for x in ("media", "file", "bild")):
        return True
    return False

def _write_birth_line(f, date, place, note):
    if not (date or place or note):
        return
    line = "Född:"
    if date:
        line += f" {date}"
    if place:
        line += f" i {place}"
    if note:
        line += f", Not: {note}"
    f.write(line + "\n")

def _write_death_line(f, date, place, note):
    if not (date or place or note):
        return
    line = "Död:"
    if date:
        line += f" {date}"
    if place:
        line += f" i {place}"
    if note:
        line += f", Not: {note}"
    f.write(line + "\n")

def _map_relation_label(rid: str, line: str, doc: GedDocument) -> str:
    """Translate GED relation tags to Swedish labels."""
    rid_u = (rid or "").upper()
    if rid_u == "SPOUSE":
        return "Gift:"
    if rid_u == "CHILD":
        return "Barn:"
    if rid_u == "PARENT":
        # Try to determine gender of the related person
        # Extract trailing ", <id>" (GEDCOM internal numeric ref)
        match = re.search(r",\s*(\d+)\s*$", line)
        if match:
            rel_id = match.group(1)
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
    return rid  # Default: keep as-is (technical tag)

def generate_mainexport(in_path: Path, out_path: Path) -> int:
    """
    Output format (Markdown-friendly flat text):
      # Persongalleri
      ## <header>
      Född: ...
      Död: ...
      <Syssla: ...>
      <Gift: ...>
      <Barn: ...>
      <Far:/Mor: ...>
    """
    doc = GedDocument(in_path)
    count = 0

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Persongalleri\n\n")

        for xref, (s, e) in doc.iter_individuals():
            header, fields, relations = doc.collect_fields_for_individual(s, e)
            f.write(f"## {header}\n")

            # --- Collect birth/death fields first ---
            birth_date = birth_place = birth_note = None
            death_date = death_place = death_note = None

            for fid, desc, content in fields:
                fid_u = (fid or "").upper()
                if fid_u == "BIRT.DATE":
                    birth_date = _flatten(content)
                elif fid_u == "BIRT.PLAC":
                    birth_place = _flatten(content)
                elif fid_u == "BIRT.NOTE":
                    birth_note = _flatten(content)
                elif fid_u == "DEAT.DATE":
                    death_date = _flatten(content)
                elif fid_u == "DEAT.PLAC":
                    death_place = _flatten(content)
                elif fid_u == "DEAT.NOTE":
                    death_note = _flatten(content)

            _write_birth_line(f, birth_date, birth_place, birth_note)
            _write_death_line(f, death_date, death_place, death_note)

            # --- Other fields (filtered, Swedish mappings) ---
            for fid, desc, content in fields:
                content = _flatten(content)
                if not content:
                    continue
                fid_u = (fid or "").upper()
                if fid_u in ("BIRT.DATE","BIRT.PLAC","BIRT.NOTE","DEAT.DATE","DEAT.PLAC","DEAT.NOTE","DEAT._DESCRIPTION"):
                    continue
                if _is_email_line(fid, desc, content) or _is_media_line(fid, desc):
                    continue

                # Replace OCCU with Syssla
                if fid_u == "OCCU":
                    f.write(f"Syssla: {content}\n")
                else:
                    f.write(f"{fid},{desc},{content}\n")

            # --- Relations (translated labels) ---
            for rid, rdesc, line in relations:
                line = _flatten(line)
                if not line:
                    continue
                if _is_email_line(rid, rdesc, line) or _is_media_line(rid, rdesc):
                    continue

                label = _map_relation_label(rid, line, doc)
                if label.endswith(":"):
                    f.write(f"{label} {line}\n")
                else:
                    f.write(f"{label},{rdesc},{line}\n")

            f.write("\n")
            count += 1

    return count
