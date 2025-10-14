# src/genreport/reports/mainexport.py
from __future__ import annotations
import re
from pathlib import Path

from ..ged import GedDocument

# compact multi-line values to one line
_flatten_re = re.compile(r"\s*\n\s*")


def _flatten(text: str) -> str:
    return _flatten_re.sub(" / ", (text or "").strip())


def _is_email_line(fid: str, desc: str, content: str) -> bool:
    """Filter out anything related to email."""
    f = (fid or "").upper()
    d = (desc or "").lower()
    c = (content or "")
    if "EMAIL" in f:
        return True
    if "email" in d:
        return True
    if c.strip().upper() == "EMAIL":
        return True
    if "@" in c:
        return True
    return False


def _is_media_line(fid: str, desc: str) -> bool:
    """Filter out media/attachments (OBJE/FILE/FORM and the like)."""
    f = (fid or "").upper()
    d = (desc or "").lower()
    if "OBJE" in f or f.endswith(".FILE") or ".FILE" in f or f.endswith(".FORM") or ".FORM" in f:
        return True
    if "media" in d or "file" in d or "bild" in d:
        return True
    return False


def _write_birth_line(f, date: str | None, place: str | None, note: str | None) -> None:
    """Compose and write 'Född: <date> i <place>[, Not: <note>]'."""
    d = (date or "").strip()
    p = (place or "").strip()
    n = (note or "").strip()

    if not (d or p or n):
        return

    line = "Född:"
    if d:
        line += f" {d}"
    if p:
        line += f" i {p}"
    if n:
        line += f", Not: {n}"
    f.write(line + "\n")


def _write_death_line(f, date: str | None, place: str | None, note: str | None) -> None:
    """Compose and write 'Avliden: <date> i <place>[, Not: <note>]'."""
    d = (date or "").strip()
    p = (place or "").strip()
    n = (note or "").strip()

    if not (d or p or n):
        return

    line = "Avliden:"
    if d:
        line += f" {d}"
    if p:
        line += f" i {p}"
    if n:
        line += f", Not: {n}"
    f.write(line + "\n")


def generate_mainexport(in_path: Path, out_path: Path) -> int:
    """
    Output format (Markdown-friendly flat text):
      # Persongalleri
      ## <header>
      Född: ...
      Avliden: ...
      <other fields>
      <relations>
      <blank line>
    """
    doc = GedDocument(in_path)
    count = 0

    with open(out_path, "w", encoding="utf-8") as f:
        # H1 at the very top
        f.write("# Persongalleri\n\n")

        for xref, (s, e) in doc.iter_individuals():
            header, fields, relations = doc.collect_fields_for_individual(s, e)
            f.write(f"## {header}\n")

            # --- Collect birth and death fields first ---
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

            # --- Write merged birth and death lines ---
            _write_birth_line(f, birth_date, birth_place, birth_note)
            _write_death_line(f, death_date, death_place, death_note)

            # --- Write remaining fields (filtered) ---
            for fid, desc, content in fields:
                content = _flatten(content)
                if not content:
                    continue
                fid_u = (fid or "").upper()

                # Skip birth/death lines that we merged
                if fid_u in (
                    "BIRT.DATE",
                    "BIRT.PLAC",
                    "BIRT.NOTE",
                    "DEAT.DATE",
                    "DEAT.PLAC",
                    "DEAT.NOTE",
                    "DEAT._DESCRIPTION",
                ):
                    continue

                if _is_email_line(fid, desc, content):
                    continue
                if _is_media_line(fid, desc):
                    continue

                f.write(f"{fid},{desc},{content}\n")

            # --- Relations (filtered for email/media) ---
            for rid, rdesc, line in relations:
                line = _flatten(line)
                if not line:
                    continue
                if _is_email_line(rid, rdesc, line):
                    continue
                if _is_media_line(rid, rdesc):
                    continue
                f.write(f"{rid},{rdesc},{line}\n")

            f.write("\n")
            count += 1

    return count
