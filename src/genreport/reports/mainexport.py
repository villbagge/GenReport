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
    return ("EMAIL" in f) or ("email" in d) or (c.strip().upper() == "EMAIL") or ("@" in c)

def _is_media_line(fid: str, desc: str) -> bool:
    f = (fid or "").upper()
    d = (desc or "").lower()
    return ("OBJE" in f or ".FILE" in f or ".FORM" in f) or any(x in d for x in ("media", "file", "bild"))

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
_years_dashed_re = re.compile(r"\s((?:\d{4}-\d{4})|(?:\d{4}-)|(?:-\d{4}))$")

def _split_name_years_id(line: str) -> tuple[str, str, str]:
    if not line:
        return "", line, ""
    m_id = _last_id_re.search(line)
    if not m_id:
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
    id_str, name, years = _split_name_years_id(line)
    parts = [f"## #{id_str}" if id_str else "##"]
    if name:
        parts.append(name)
    if years:
        parts.append(years)
    return " ".join(parts).rstrip()

def _format_relation_from_line(label: str, line: str, warn_if_no_id: bool = False) -> str:
    id_str, name, years = _split_name_years_id(line)
    bits = [label]  # label ends with ':'
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
        return "Vigd:"
    if rid_u == "CHILD":
        return "Barn:"
    if rid_u == "PARENT":
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
    return rid

def generate_mainexport(in_path: Path, out_path: Path) -> int:
    doc = GedDocument(in_path)
    count = 0

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Persongalleri\n\n")

        for xref, (s, e) in doc.iter_individuals():
            header, fields, relations = doc.collect_fields_for_individual(s, e)
            f.write(_format_header_from_line(header) + "\n")

            # Collect key fields first
            birth_date = birth_place = birth_note = None
            death_date = death_place = death_note = None
            occu_text = occu_place = occu_date = None

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
                elif fid_u == "OCCU.DATE":
                    occu_date = _flatten(content)

            _write_birth_line(f, birth_date, birth_place, birth_note)
            _write_death_line(f, death_date, death_place, death_note)

            # Other fields — exclude all internal and OCCU fields
            for fid, desc, content in fields:
                content = _flatten(content)
                if not content:
                    continue
                fid_u = (fid or "").upper()
                if fid_u in (
                    "BIRT.DATE","BIRT.PLAC","BIRT.NOTE","BIRT._DESCRIPTION",
                    "DEAT.DATE","DEAT.PLAC","DEAT.NOTE","DEAT._DESCRIPTION","DEAT.AGE",
                    "OCCU","OCCU.PLAC","OCCU.DATE",
                ):
                    continue
                if _is_email_line(fid, desc, content) or _is_media_line(fid, desc):
                    continue
                f.write(f"{fid},{desc},{content}\n")

            # Relations come next
            for rid, rdesc, line in relations:
                line = _flatten(line)
                if not line:
                    continue
                if _is_email_line(rid, rdesc, line) or _is_media_line(rid, desc):
                    continue
                label = _map_relation_label(rid, line, doc)
                if label.endswith(":"):
                    f.write(_format_relation_from_line(label, line, warn_if_no_id=True) + "\n")
                else:
                    f.write(f"{label},{rdesc},{line}\n")

            # After relations, print Syssla (if exists)
            if occu_text or occu_place or occu_date:
                parts = ["Syssla:"]
                if occu_date:
                    parts.append(occu_date)
                if occu_text:
                    if occu_date:
                        parts[-1] = parts[-1] + ","
                    parts.append(occu_text)
                if occu_place:
                    parts.append(f"i {occu_place}")
                f.write(" ".join(parts) + "\n")

            f.write("\n")
            count += 1

    return count
