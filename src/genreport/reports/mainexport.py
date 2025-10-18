# === GENREPORT HEADER START ===
# GenReport — v0.4.0
# Commit: Add automated verify_diff tool with Notepad integration
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


def _write_line(f, text: str = "") -> None:
    """
    Write a single line, ensuring exactly one trailing newline.
    Does not modify content except to add '\n' if missing.
    """
    if text is None:
        text = ""
    if text.endswith("\n"):
        f.write(text)
    else:
        f.write(text + "\n")


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
    _write_line(f, line)


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
    _write_line(f, line)


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
        _write_line(f, "# Persongalleri")
        _write_line(f, "")  # blank line

        for xref, (s, e) in doc.iter_individuals():
            # --- Use IndividualView for header + birth/death/occupation/notes + relations ---
            view = doc.build_individual_view(s, e)
            header_from_view = view.header

            # We still fetch fields using the legacy call (for miscellaneous field emission).
            _legacy_header, fields, _legacy_relations = doc.collect_fields_for_individual(s, e)

            # Header (unchanged behavior)
            _, name, years = _split_name_years_id(header_from_view)

            assigned = get_id_for_xref(idmap, xref)
            if assigned is None:
                # Suppress warning for media-only placeholders (e.g., @I88888888@)
                if not _is_media_only_placeholder(doc, xref):
                    print(f"⚠️  Warning: Missing assigned ID for {xref}", file=sys.stderr)
                assigned = "?"

            _write_line(f, " ".join(p for p in ["##", f"#{assigned}", name, years] if p).strip())

            # --- Birth/Death from IndividualView ---
            birth_date  = _flatten(view.birth_date)
            birth_place = _flatten(view.birth_place)
            birth_note  = _flatten(view.birth_note)
            death_date  = _flatten(view.death_date)
            death_place = _flatten(view.death_place)
            death_note  = _flatten(view.death_note)

            # --- Occupation + Notes from IndividualView ---
            occu_text_raw  = _flatten(view.occupation_text)
            occu_place_raw = _flatten(view.occupation_place)
            occu_date_raw  = _flatten(view.occupation_date)
            occu_text  = occu_text_raw or None
            occu_place = occu_place_raw or None
            occu_date  = occu_date_raw or None

            indi_notes = []
            if view.notes:
                for n in view.notes:
                    n_flat = _flatten(n)
                    if n_flat:
                        indi_notes.append(n_flat)

            # Write birth/death exactly as before
            _write_birth_line(f, birth_date, birth_place, birth_note)
            _write_death_line(f, death_date, death_place, death_note)

            # Emit remaining fields (unchanged filtering; skip OCCU/INDI.NOTE et al. as before)
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

                _write_line(f, f"{fid},{desc},{content}")

            # --- Relations NOW from IndividualView (order preserved) ---
            for rid, rdesc, line in (view.relations_all or []):
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
                    _write_line(f, " ".join(bits).rstrip())
                else:
                    _write_line(f, f"{label},{rdesc},{line}")

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
                _write_line(f, " ".join(parts))

            if indi_notes:
                _write_line(f, f"Not: {' / '.join(indi_notes)}")

            _write_line(f, "")  # blank line
            count += 1

    return count
