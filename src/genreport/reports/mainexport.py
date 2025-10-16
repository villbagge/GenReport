# src/genreport/reports/mainexport.py
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

# --- Helpers to reformat "Name years, id" -> "#id Name years"
_last_id_re = re.compile(r",\s*(\d+)\s*$")
# Accept 1914-1964  |  1914-  |  -1964  at end of string
_years_dashed_re = re.compile(r"\s((?:\d{4}-\d{4})|(?:\d{4}-)|(?:-\d{4}))$")

def _split_name_years_id(line: str) -> tuple[str, str, str]:
    """
    Input example: 'Oskar ... 1914-1964, 10'  or '... 1914-, 10'  or '... -1964, 10'
    Returns: (id, name, years_dashed)
      - id: '10'
      - name: 'Oskar ...'
      - years_dashed: '1914-1964' | '1914-' | '-1964' | ''
    """
    if not line:
        return "", line, ""

    m_id = _last_id_re.search(line)
    if not m_id:
        # No trailing ", id"
        name = line.strip()
        m_y = _years_dashed_re.search(name)
        years = ""
        if m_y:
            years = m_y.group(1)
            name = name[: m_y.start()].rstrip()
        return "", name, years

    id_str = m_id.group(1)
    left = line[: m_id.start()].rstrip()

    m_y = _years_dashed_re.search(left)
    years = ""
    if m_y:
        years = m_y.group(1)
        name = left[: m_y.start()].rstrip()
    else:
        name = left

    return id_str, name, years

def _format_header_from_line(line: str) -> str:
    """Convert 'Name yrs, id' to '## #id Name yrs'."""
    id_str, name, years = _split_name_years_id(line)
    parts = [f"## #{id_str}" if id_str else "##"]
    if name:
        parts.append(name)
    if years:
        parts.append(years)
    return " ".join(parts).rstrip()

def _format_relation_from_line(label: str, line: str, warn_if_no_id: bool = False) -> str:
    """
    Convert relation line 'Name yrs, id' to 'Label: #id Name yrs'
    If no id is found, omit '#id' and optionally warn.
    """
    id_str, name, years = _split_name_years_id(line)
    bits = [label]  # label already includes trailing ':'
    if id_str:
        bits.append(f"#{id_str}")
    else:
        if warn_if_no_id:
            print(f"⚠️  Warning: Missing numeric id in relation line: '{line}'", file=sys.stderr)
    if name:
        bits.append(name)
    if years:
        bits.append(years)
    return " ".join(bits).rstrip()

def _map_relation_label(rid: str, line: str, doc: GedDocument) -> str:
    """Translate GED relation tags to Swedish labels."""
    rid_u = (rid or "").upper()
    if rid_u == "SPOUSE":
        return "Gift:"
    if rid_u == "CHILD":
        return "Barn:"
    if rid_u == "PARENT":
        # Determine gender of the related person via trailing id in 'line'
        m = _last_id_re.search(line)
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
    return rid  # fallback, should not happen for our mapped relations

def generate_mainexport(in_path: Path, out_path: Path) -> int:
    """
    Output format:
      # Persongalleri
      ## #<id> <name> <YYYY-YYYY|YYYY-| -YYYY>
      Född: ...
      Död: ...
      Syssla: <occupation>[ i <place>]
      Far:/Mor:/Förälder: #<id> <name> <YYYY-YYYY|YYYY-| -YYYY>
      Gift: #<id> <name> <YYYY-YYYY|YYYY-| -YYYY>
      Barn: #<id> <name> <YYYY-YYYY|YYYY-| -YYYY>
    """
    doc = GedDocument(in_path)
    count = 0

    with open(out_path, "w", encoding="utf-8") as f:
        # H1 at the very top
        f.write("# Persongalleri\n\n")

        for xref, (s, e) in doc.iter_individuals():
            header, fields, relations = doc.collect_fields_for_individual(s, e)

            # Person header → move ID to front and hash it
            f.write(_format_header_from_line(header) + "\n")

            # --- Collect birth/death and occupation fields first ---
            birth_date = birth_place = birth_note = None
            death_date = death_place = death_note = None
            occu_text = None
            occu_place = None

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
                elif fid_u == "OCCU":
                    occu_text = _flatten(content)
                elif fid_u == "OCCU.PLAC":
                    occu_place = _flatten(content)

            # Merged birth/death lines
            _write_birth_line(f, birth_date, birth_place, birth_note)
            _write_death_line(f, death_date, death_place, death_note)

            # Merged OCCU + OCCU.PLAC → "Syssla: ..."
            if occu_text or occu_place:
                line = "Syssla:"
                if occu_text:
                    line += f" {occu_text}"
                if occu_place:
                    line += f" i {occu_place}"
                f.write(line + "\n")

            # --- Other fields (filtered); suppress OCCU + OCCU.PLAC since we printed them above ---
            for fid, desc, content in fields:
                content = _flatten(content)
                if not content:
                    continue
                fid_u = (fid or "").upper()
                if fid_u in (
                    "BIRT.DATE","BIRT.PLAC","BIRT.NOTE",
                    "DEAT.DATE","DEAT.PLAC","DEAT.NOTE","DEAT._DESCRIPTION",
                    "OCCU","OCCU.PLAC"
                ):
                    continue
                if _is_email_line(fid, desc, content) or _is_media_line(fid, desc):
                    continue

                # Other fields remain in the original flat form
                f.write(f"{fid},{desc},{content}\n")

            # --- Relations (translated + reformat with #id and dashed years) ---
            for rid, rdesc, line in relations:
                line = _flatten(line)
                if not line:
                    continue
                if _is_email_line(rid, rdesc, line) or _is_media_line(rid, rdesc):
                    continue

                label = _map_relation_label(rid, line, doc)
                if label.endswith(":"):
                    f.write(_format_relation_from_line(label, line, warn_if_no_id=True) + "\n")
                else:
                    f.write(f"{label},{rdesc},{line}\n")

            f.write("\n")
            count += 1

    return count
