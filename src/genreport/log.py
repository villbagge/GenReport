from __future__ import annotations
import sys

__all__ = ["warn"]

def warn(message: str) -> None:
    """Emit a warning line to stderr. Text is printed verbatim."""
    print(message, file=sys.stderr)
