# src/genreport/fieldfilters.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass(frozen=True)
class FieldContext:
    """Lightweight context for a parsed field from collect_fields_for_individual."""
    field_id: str   # e.g., "SOUR.PAGE", "BIRT.DATE"
    desc: str       # human-friendly description (not used by rules yet)
    content: str    # flattened string content


# --- A tiny, resilient rule engine --------------------------------------------------------------

# A rule returns True if it CLAIMS the decision. First matching rule wins.
Rule = Callable[[FieldContext], Optional[bool]]
# - return True  => exclude this field
# - return False => explicitly keep this field (reserved for future)
# - return None  => no opinion; fall through to next rule


def _norm(s: Optional[str]) -> str:
    return (s or "").strip()


def _upper(s: Optional[str]) -> str:
    return _norm(s).upper()


def _lower(s: Optional[str]) -> str:
    return _norm(s).lower()


def rule_exclude_exact(field_id_upper: str) -> Rule:
    """Exclude when field_id matches exactly (case-insensitive)."""
    fid_u = field_id_upper.upper()

    def _rule(ctx: FieldContext) -> Optional[bool]:
        return True if _upper(ctx.field_id) == fid_u else None

    return _rule


def rule_exclude_when_contains(field_id_upper: str, needle_lower: str) -> Rule:
    """Exclude when field_id matches AND content contains the given substring (case-insensitive)."""
    fid_u = field_id_upper.upper()
    ned_l = needle_lower.lower()

    def _rule(ctx: FieldContext) -> Optional[bool]:
        if _upper(ctx.field_id) != fid_u:
            return None
        return True if ned_l in _lower(ctx.content) else None

    return _rule


# Registry: order matters (first match wins)
_RULES: List[Rule] = []

# --- Active rules -------------------------------------------------------------------------------
# SOUR.PAGE - exclude if containing www.myheritage
_RULES.append(rule_exclude_when_contains("SOUR.PAGE", "www.myheritage"))

# SOUR.TEXT - KEEP (rule removed intentionally)

# SOUR.ROLE - exclude
_RULES.append(rule_exclude_exact("SOUR.ROLE"))

# SOUR._LINK - exclude if containing www.myheritage
_RULES.append(rule_exclude_when_contains("SOUR._LINK", "www.myheritage"))

# SOUR._UID - exclude
_RULES.append(rule_exclude_exact("SOUR._UID"))

# -----------------------------------------------------------------------------------------------

def should_exclude_field(field_id: str, desc: str, content: str) -> bool:
    """
    Decide whether to exclude a field from emission.
    - Stable, order-sensitive rules (first match wins).
    - Returns False if no rule claims a decision (keep by default).
    """
    ctx = FieldContext(field_id=field_id, desc=desc, content=content)
    for rule in _RULES:
        decision = rule(ctx)
        if decision is not None:
            return bool(decision)
    return False
