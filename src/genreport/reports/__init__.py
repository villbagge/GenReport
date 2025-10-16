# === GENREPORT HEADER START ===
# GenReport — v0.3.0
# Commit: Fix encoding and restore full GedDocument implementation
# Date: 2025-10-16
# Files: __init__.py
# Changes:
#   Auto-stamp from post-commit
# === GENREPORT HEADER END ===






# src/genreport/reports/__init__.py
from .mainexport import generate_mainexport

__all__ = ["generate_mainexport"]
