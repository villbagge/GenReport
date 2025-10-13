# src/genreport/reports/megaexport.py
from __future__ import annotations
import re
from pathlib import Path
from typing import TextIO

from ..ged import GedDocument

def generate_mainexport(in_path: Path, out_path: Path) -> int:
    """
    Recreates the current output format from your legacy script:
    Header line + (field_id,desc,content) lines + relations + blank line, per individual.
    Returns the number of individuals exported.
    """
    doc = GedDocument(in_path)
    count = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for xref, (s, e) in doc.iter_individuals():
            header, fields, relations = doc.collect_fields_for_individual(s, e)
            f.write(header + "\n")
            # fields
            for fid, desc, content in fields:
                content = content.strip()
                if not content:
                    continue
                content = re.sub(r"\s*\n\s*", " / ", content)  # flatten
                f.write(f"{fid},{desc},{content}\n")
            # relations
            for rid, rdesc, line in relations:
                if line.strip():
                    f.write(f"{rid},{rdesc},{line}\n")
            f.write("\n")
            count += 1
    return count
