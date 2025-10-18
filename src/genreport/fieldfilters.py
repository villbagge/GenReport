# src/genreport/fieldfilters.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from .normalize import htmlish_to_markdown, format_bok_subfields

__all__ = ["process_field"]


@dataclass(frozen=True)
class FieldContext:
    field_id: str   # e.g., "SOUR.PAGE", "BIRT.DATE"
    desc: str
    content: str


# Decision rule
Rule = Callable[[FieldContext], Optional[bool]]
Transform = Callable[[FieldContext], Optional[Tuple[str, bool]]]
# Transform returns (new_content, preserve_newlines)
# - preserve_newlines=True  => report must NOT flatten this content
# - preserve_newlines=False => report may flatten (default behavior)


def _norm(s: Optional[str]) -> str:
    return (s or "").strip()


def _upper(s: Optional[str]) -> str:
    return _norm(s).upper()


def _lower(s: Optional[str]) -> str:
    return _norm(s).lower()


def rule_exclude_exact(field_id_upper: str) -> Rule:
    fid_u = field_id_upper.upper()

    def _rule(ctx: FieldContext) -> Optional[bool]:
        return True if _upper(ctx.field_id) == fid_u else None

    return _rule


def rule_exclude_when_contains(field_id_upper: str, needle_lower: str) -> Rule:
    fid_u = field_id_upper.upper()
    ned_l = needle_lower.lower()

    def _rule(ctx: FieldContext) -> Optional[bool]:
        if _upper(ctx.field_id) != fid_u:
            return None
        return True if ned_l in _lower(ctx.content) else None

    return _rule


def _looks_like_header(line: str) -> bool:
    """
    Heuristic for name-only lines we should drop at block edges:
    - No colon ':' and no digits
    - Not starting with labels we keep ('Bok', 'Källor', 'Källa')
    - Short-ish (<= 6 words)
    """
    s = (line or "").strip()
    if not s:
        return False
    low = s.lower()
    if ":" in s:
        return False
    if any(ch.isdigit() for ch in s):
        return False
    if low.startswith(("bok", "källor", "källa")):
        return False
    return len(s.split()) <= 6


def transform_sour_text_markdown(ctx: FieldContext) -> Optional[Tuple[str, bool]]:
    """
    If SOUR.TEXT is HTML-ish or contains links/URLs, convert to Markdown; remove links to
    www.myheritage entirely (URL + link text). Keep line breaks (preserve_newlines=True).
    Also removes raw URLs to that domain if present in plain text.
    Afterward, normalize Bok subfields per line, and drop header-ish lines at the
    start and end of the block.
    """
    if _upper(ctx.field_id) != "SOUR.TEXT":
        return None
    c = ctx.content or ""
    md = htmlish_to_markdown(c, block_domains=("www.myheritage",))

    # Apply Bok subfield normalization line-by-line
    lines: List[str] = [format_bok_subfields(ln) for ln in md.splitlines()]

    # Trim leading empties
    while lines and not lines[0].strip():
        lines.pop(0)
    # Trim trailing empties
    while lines and not lines[-1].strip():
        lines.pop()

    # Drop header-ish first line (names) if present
    if lines and _looks_like_header(lines[0]):
        lines.pop(0)
        while lines and not lines[0].strip():
            lines.pop(0)

    # Drop header-ish trailing line (names) if present
    if lines and _looks_like_header(lines[-1]):
        lines.pop()
        while lines and not lines[-1].strip():
            lines.pop()

    if not lines:
        return ("", True)

    md_fixed = "\n".join(lines)
    return (md_fixed, True)


# Registries: order matters
_RULES: List[Rule] = []
_TRANSFORMS: List[Transform] = []

# Exclusion rules (first match wins)
_RULES.append(rule_exclude_when_contains("SOUR.PAGE", "www.myheritage"))
# KEEP: SOUR.TEXT has no exclusion rule
_RULES.append(rule_exclude_exact("SOUR.ROLE"))
_RULES.append(rule_exclude_when_contains("SOUR._LINK", "www.myheritage"))
_RULES.append(rule_exclude_exact("SOUR._UID"))
# always exclude these
_RULES.append(rule_exclude_exact("SOUR.EVEN"))
_RULES.append(rule_exclude_exact("SOUR.QUAY"))

# Transforms
_TRANSFORMS.append(transform_sour_text_markdown)


def process_field(field_id: str, desc: str, content: str) -> Tuple[bool, str, bool]:
    """
    Returns (exclude, new_content, preserve_newlines).
    - Exclusion rules run first (first-match-wins).
    - If not excluded, transforms run in order (first match wins).
    - If no transform applies, content unchanged, preserve_newlines=False.
    """
    ctx = FieldContext(field_id=field_id, desc=desc, content=content)
    for rule in _RULES:
        decision = rule(ctx)
        if decision is not None:
            return bool(decision), content, False
    for tf in _TRANSFORMS:
        res = tf(ctx)
        if res is not None:
            new_c, keep_newlines = res
            return False, new_c, bool(keep_newlines)
    return False, content, False
