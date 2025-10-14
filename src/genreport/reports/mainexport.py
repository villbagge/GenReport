# src/genreport/reports/mainexport.py
from __future__ import annotations
import re
from pathlib import Path

from ..ged import GedDocument

# compact multi-line values to one line
_flatten_re = re.compile(r"\s*\n\s*")


def _flatten(text: str) -> str:
    return _flatten_re.sub(" / ", (text or "").strip())


def generate_mainexport(in_path: Path, out_path: Path) -> int:
    """
    Original 'flat' output:
      <header line>
      <field_id>,<desc>,<content>
      <relation_id>,<desc>,<line>
      <blank line>
    """
    doc = GedDocument(in_path)
    count = 0

    with open(out_path, "w", encoding="utf-8") as f:
        for xref, (s, e) in doc.iter_individuals():
            header, fields, relations = doc.collect_fields_for_individual(s, e)
            f.write(header + "\n")

            # fields
            for fid, desc, content in fields:
                content = _flatten(content)
                if content:
                    f.write(f"{fid},{desc},{content}\n")

            # relations
            for rid, rdesc, line in relations:
                line = _flatten(line)
                if line:
                    f.write(f"{rid},{rdesc},{line}\n")

            f.write("\n")
            count += 1

    return count
