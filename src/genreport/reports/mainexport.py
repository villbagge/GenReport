# === GENREPORT HEADER START ===
# GenReport — v0.3.3
# Commit: Add exception handling for seven siblings (9001–9007) and silence @I88888888@ warnings
# Date: 2025-10-17
# Files: mainexport.py
# Changes:
#   Auto-stamp from post-commit
# === GENREPORT HEADER END ===

# src/genreport/reports/mainexport.py
from __future__ import annotations
import re
from pathlib import Path
import sys

from ..ged import GedDocument
from ..idmap import get_id_for_xref, get_id_for_numeric, _is_media_only_placeholder

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


def _map_relation_label(rid: str, line: str, doc: GedDocument) -> str:
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


def generate_mainexport(in_path: Path, out_path: Path, idmap: dict[str, int]) -> int:
    doc = GedDocument(in_path)
    count = 0

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Persongalleri\n\n")

        for xref, (s, e) in doc.iter_individuals():
            header, fields, relations = doc.collect_fields_for_individual(s, e)

            _, name, years = _split_name_years_id(header)

            assigned = get_id_for_xref(idmap, xref)
            if assigned is None:
                # Suppress warning for media-only placeholders (e.g., @I88888888@)
                if not _is_media_only_placeholder(doc, xref):
                    print(f"⚠️  Warning: Missing assigned ID for {xref}", file=sys.stderr)
                assigned = "?"

            f.write(" ".join(p for p in ["##", f"#{assigned}", name, years] if p).strip() + "\n")

            birth_date = birth_place = birth_note = None
            death_date = death_place = death_note = None
            occu_text = occu_place = occu_date = None
            indi_notes: list[str] = []

            for fid, desc, content in fields:
                fid_u = (fid or "").upper()
                val = _flatten(content)

                if fid_u == "BIRT.DATE":
                    birth_date = val
                elif fid_u == "BIRT.PLAC":
                    birth_place = val
                elif fid_u == "BIRT.NOTE":
                    birth_note = val
                elif fid_u == "DEAT.DATE":
                    death_date = val
                elif fid_u == "DEAT.PLAC":
                    death_place = val
                elif fid_u == "DEAT.NOTE":
                    death_note = val
                elif fid_u == "OCCU":
                    occu_text = val
                elif fid_u == "OCCU.PLAC":
                    occu_place = val
                elif fid_u == "OCCU.DATE":
                    occu_date = val
                elif fid_u == "INDI.NOTE":
                    if val:
                        indi_notes.append(val)

            _write_birth_line(f, birth_date, birth_place, birth_note)
            _write_death_line(f, death_date, death_place, death_note)

            for fid, desc, content in fields:
                content = _flatten(content)
                if not content:
                    continue
                fid_u = (fid or "").upper()

                if fid_u in (
                    "BIRT.DATE", "BIRT.PLAC", "BIRT.NOTE", "BIRT._DESCRIPTION",
                    "DEAT.DATE", "DEAT.PLAC", "DEAT.NOTE", "DEAT._DESCRIPTION", "DEAT.AGE",
                    "OCCU", "OCCU.PLAC", "OCCU.DATE",
                    "INDI.NOTE",
                ):
                    continue
                if _is_email_line(fid, desc, content) or _is_media_line(fid, desc):
                    continue

                f.write(f"{fid},{desc},{content}\n")

            for rid, rdesc, line in relations:
                line = _flatten(line)
                if not line:
                    continue
                if _is_email_line(rid, rdesc, line) or _is_media_line(rid, rdesc):
                    continue

                label = _map_relation_label(rid, line, doc)
                rel_id_str, rel_name, rel_years = _split_name_years_id(line)
                assigned_rel = None
                if rel_id_str:
                    assigned_rel = get_id_for_numeric(doc, idmap, rel_id_str)

                # Also suppress warnings for placeholder relations
                if rel_id_str and assigned_rel is None:
                    rx = doc._indi_num_to_xref.get(rel_id_str) or f"@I{rel_id_str}@"
                    if rx in doc.indi_map and not _is_media_only_placeholder(doc, rx):
                        print(f"⚠️  Warning: Missing assigned ID for {rx}", file=sys.stderr)

                if label.endswith(":"):
                    bits = [label]
                    if assigned_rel is not None:
                        bits.append(f"#{assigned_rel}")
                    if rel_name:
                        bits.append(rel_name)
                    if rel_years:
                        bits.append(rel_years)
                    f.write(" ".join(bits).rstrip() + "\n")
                else:
                    f.write(f"{label},{rdesc},{line}\n")

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

            if indi_notes:
                f.write(f"Not: {' / '.join(indi_notes)}\n")

            f.write("\n")
            count += 1

    return count
