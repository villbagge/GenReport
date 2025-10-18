# src/genreport/reports/mainexport.py
from __future__ import annotations

import re
from pathlib import Path
from typing import Final

from ..ged import GedDocument
from ..idmap import get_id_for_xref, get_id_for_numeric, _is_media_only_placeholder
from ..relations import map_relation_label
from ..log import warn
from ..fieldfilters import process_field

__all__ = ["generate_mainexport"]

_FLATTEN_RE: Final = re.compile(r"\s*\n\s*")


def _flatten(text: str) -> str:
    return _FLATTEN_RE.sub(" / ", (text or "").strip())


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


_LAST_ID_RE: Final = re.compile(r",\s*(\d+)\s*$")
_YEARS_DASHED_RE: Final = re.compile(r"\s((?:\d{4}-\d{4})|(?:\d{4}-)|(?:-\d{4}))$")


def _split_name_years_id(line: str) -> tuple[str, str, str]:
    if not line:
        return "", line, ""
    m_id = _LAST_ID_RE.search(line)
    if not m_id:
        name = line.strip()
        m_y = _YEARS_DASHED_RE.search(name)
        years = ""
        if m_y:
            years = m_y.group(1)
            name = name[: m_y.start()].rstrip()
        return "", name, years
    id_str = m_id.group(1)
    left = line[: m_id.start()].rstrip()
    m_y = _YEARS_DASHED_RE.search(left)
    years = ""
    if m_y:
        years = m_y.group(1)
        name = left[: m_y.start()].rstrip()
    else:
        name = left
    return id_str, name, years


def generate_mainexport(in_path: Path, out_path: Path, idmap: dict[str, int]) -> int:
    doc = GedDocument(in_path)
    count = 0

    with open(out_path, "w", encoding="utf-8") as f:
        _write_line(f, "# Persongalleri")
        _write_line(f, "")  # blank line

        for xref, (s, e) in doc.iter_individuals():
            view = doc.build_individual_view(s, e)
            header_from_view = view.header

            # Fetch fields using the legacy call (for miscellaneous field emission).
            _, fields, _ = doc.collect_fields_for_individual(s, e)

            # Header
            _, name, years = _split_name_years_id(header_from_view)

            assigned = get_id_for_xref(idmap, xref)
            if assigned is None:
                if not _is_media_only_placeholder(doc, xref):
                    warn(f"⚠️  Warning: Missing assigned ID for {xref}")
                assigned = "?"
            _write_line(f, " ".join(p for p in ["##", f"#{assigned}", name, years] if p).strip())

            # Birth/Death
            birth_date  = _flatten(view.birth_date)
            birth_place = _flatten(view.birth_place)
            birth_note  = _flatten(view.birth_note)
            death_date  = _flatten(view.death_date)
            death_place = _flatten(view.death_place)
            death_note  = _flatten(view.death_note)

            # Occupation + Notes
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

            _write_birth_line(f, birth_date, birth_place, birth_note)
            _write_death_line(f, death_date, death_place, death_note)

            # Emit remaining fields; defer SOUR.TEXT to the end
            sour_text_blocks: list[str] = []

            for fid, desc, content in fields:
                content = content or ""
                fid_u = (fid or "").upper()

                # baseline skips
                if fid_u in (
                    "BIRT.DATE", "BIRT.PLAC", "BIRT.NOTE", "BIRT._DESCRIPTION",
                    "DEAT.DATE", "DEAT.PLAC", "DEAT.NOTE", "DEAT._DESCRIPTION", "DEAT.AGE",
                    "OCCU", "OCCU.PLAC", "OCCU.DATE",
                    "INDI.NOTE",
                ):
                    continue

                # media/email skip (unchanged)
                if _is_email_line(fid, desc, content) or _is_media_line(fid, desc):
                    continue

                # Decide & transform
                exclude, transformed, preserve_newlines = process_field(fid_u, desc, content)
                if exclude:
                    continue

                if fid_u == "SOUR.TEXT":
                    out_content = transformed if preserve_newlines else _flatten(transformed)
                    if out_content.strip():
                        sour_text_blocks.append(out_content.strip("\n"))
                    continue

                out_content = transformed if preserve_newlines else _flatten(transformed)
                if not out_content:
                    continue

                _write_line(f, f"{fid},{desc},{out_content}")

            # Relations (unchanged)
            for rid, rdesc, line in (view.relations_all or []):
                line = _flatten(line or "")
                if not line:
                    continue
                if _is_email_line(rid, rdesc, line) or _is_media_line(rid, rdesc):
                    continue

                label = map_relation_label(doc, rid, line)
                rel_id_str, rel_name, rel_years = _split_name_years_id(line)
                assigned_rel = None
                if rel_id_str:
                    assigned_rel = get_id_for_numeric(doc, idmap, rel_id_str)

                if rel_id_str and assigned_rel is None:
                    rx = doc._indi_num_to_xref.get(rel_id_str) or f"@I{rel_id_str}@"
                    if rx in doc.indi_map and not _is_media_only_placeholder(doc, rx):
                        warn(f"⚠️  Warning: Missing assigned ID for {rx}")

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

            # Syssla and Person notes (unchanged)
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

            # --- Källor (render SOUR.TEXT with rulers) ---
            if sour_text_blocks:
                _write_line(f, "### Källor:")
                for block in sour_text_blocks:
                    _write_line(f, "---")
                    # write cleaned multi-line content as-is
                    if block.endswith("\n"):
                        f.write(block)
                    else:
                        f.write(block + "\n")

            _write_line(f, "")  # blank line between people
            count += 1

    return count
