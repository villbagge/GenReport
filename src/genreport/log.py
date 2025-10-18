# src/genreport/log.py
from __future__ import annotations
import sys

def warn(message: str) -> None:
    """Emit a warning line to stderr. Text is printed verbatim."""
    print(message, file=sys.stderr)
