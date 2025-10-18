# === GENREPORT HEADER START ===
# GenReport — v0.4.0
# Commit: Add automated verify_diff tool with Notepad integration
# Date: 2025-10-17
# Files: normalize.py
# Changes:
#   Auto-stamp from post-commit
# === GENREPORT HEADER END ===



# src/genreport/normalize.py
from __future__ import annotations

import html
import re
from typing import Final, Dict, List

__all__ = [
    "htmlish_to_text",
    "clean_place",
    "normalize_date",
    "year_from",
    "PROVINCE_MAP",
    "COUNTRY_MAP",
]

# ----- Constants (unchanged content) -------------------------------------------------------------

PROVINCE_MAP: Final[Dict[str, str]] = {
    "BL": "Blekinge",
    "BO": "Bohuslän",
    "DR": "Dalarna",
    "DS": "Dalsland",
    "GO": "Gotland",
    "GÄ": "Gästrikland",
    "HA": "Halland",
    "HS": "Hälsingland",
    "HR": "Härjedalen",
    "JÄ": "Jämtland",
    "LA": "Lappland",
    "ME": "Medelpad",
    "NÄ": "Närke",
    "SK": "Skåne",
    "SM": "Småland",
    "SÖ": "Södermanland",
    "UP": "Uppland",
    "VR": "Värmland",
    "VB": "Västerbotten",
    "VG": "Västergötland",
    "VS": "Västmanland",
    "ÅN": "Ångermanland",
    "ÖL": "Öland",
    "ÖG": "Östergötland",
}

COUNTRY_MAP: Final[Dict[str, str]] = {
    "US": "USA",
    "TR": "Turkiet",
    "RU": "Ryssland",
    "PL": "Polen",
    "NO": "Norge",
    "NL": "Nederländerna",
    "LV": "Lettland",
    "IT": "Italien",
    "IS": "Island",
    "GB": "Storbrittanien",
    "FR": "Frankrike",
    "FI": "Finland",
    "DK": "Danmark",
    "DE": "Tyskland",
    "CZ": "Tjeckien",
    "BE": "Belgien",
    "EE": "Estland",
}

# ----- Precompiled regexes (identical semantics to previous inline usage) -----------------------

# htmlish_to_text
_RE_BR: Final = re.compile(r"(?i)<\s*br\s*/?\s*>")
_RE_P_CLOSE: Final = re.compile(r"(?i)</\s*p\s*>")
_RE_LI_CLOSE: Final = re.compile(r"(?i)</\s*li\s*>")
_RE_ANY_TAG: Final = re.compile(r"<[^>]+>")
_RE_SPACES: Final = re.compile(r"[ \t]{2,}")

# clean_place
_RE_CC_SWAP: Final = re.compile(
    r"(?<!\w)\.(US|TR|RU|PL|NO|NL|LV|IT|IS|GB|FR|FI|DK|DE|CZ|BE|EE)\b"
)
_RE_SN: Final = re.compile(r"\b[Ss]n\b")
_RE_FO: Final = re.compile(r"\bfö\b")
_RE_TRAILING_SVERIGE: Final = re.compile(r",\s*Sverige\b")
_RE_MULTI_SPACE: Final = re.compile(r"[ ]{2,}")

# normalize_date / year_from
_RE_ISO_FULL: Final = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RE_FIRST_YEAR: Final = re.compile(r"(\d{4})")
_RE_LAST_PART_YEAR: Final = re.compile(r"\d{4}")
_RE_NON_DIGITS: Final = re.compile(r"\D")
_RE_DATE_YMD: Final = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


# ----- Helpers -----------------------------------------------------------------------------------

def _strip_empty_ends(lines: List[str]) -> List[str]:
    """Remove leading/trailing empty lines (in-place style, but returns a new list)."""
    i, j = 0, len(lines) - 1
    while i <= j and not lines[i]:
        i += 1
    while j >= i and not lines[j]:
        j -= 1
    return lines[i : j + 1]


# ----- Public API --------------------------------------------------------------------------------

def htmlish_to_text(s: str) -> str:
    """
    Convert lightly-HTML-ish text to plain text:
    - <br>, </p>, </li> -> newline
    - remove all other tags
    - repeatedly html.unescape (up to 3 passes, until stable)
    - replace NBSP with space
    - collapse runs of spaces/tabs
    - trim leading/trailing empty lines
    """
    if not s:
        return ""
    t = s

    # Tag-level replacements (same order as before)
    t = _RE_BR.sub("\n", t)
    t = _RE_P_CLOSE.sub("\n", t)
    t = _RE_LI_CLOSE.sub("\n", t)
    t = _RE_ANY_TAG.sub("", t)

    # Unescape HTML entities up to 3 iterations or until stable
    prev = None
    loops = 0
    while prev != t and loops < 3:
        prev = t
        t = html.unescape(t)
        loops += 1

    # Whitespace normalization identical to previous logic
    t = t.replace("\xa0", " ").replace("\u00A0", " ")
    t = _RE_SPACES.sub(" ", t)

    # Line trimming (keep exact semantics)
    lines = [ln.strip() for ln in t.splitlines()]
    lines = _strip_empty_ends(lines)
    return "\n".join(lines)


def clean_place(text: str) -> str:
    """
    Normalize place strings:
    - Swap leading dot-country codes (e.g., .DE -> Tyskland) using COUNTRY_MAP.
    - Swedish normalizations: 'Sn'->'socken', 'fö'->'församling'.
    - Expand province abbreviations (e.g., 'SM' -> 'Småland') using PROVINCE_MAP.
    - Remove trailing ', Sverige'.
    - Collapse double spaces.
    """
    if not text:
        return ""
    txt = text

    def _cc_swap(m: re.Match[str]) -> str:
        cc = m.group(1).upper()
        return COUNTRY_MAP.get(cc, m.group(0))

    # Swap .DE etc.
    txt = _RE_CC_SWAP.sub(_cc_swap, txt)

    # Swedish normalizations
    txt = _RE_SN.sub("socken", txt)
    txt = _RE_FO.sub("församling", txt)

    # Province expansions (order/behavior preserved)
    for abbr, full in PROVINCE_MAP.items():
        txt = re.sub(rf"\b{re.escape(abbr)}\b", full, txt)

    # Remove trailing ", Sverige"
    txt = _RE_TRAILING_SVERIGE.sub("", txt)

    # Normalize spaces
    txt = _RE_MULTI_SPACE.sub(" ", txt)
    return txt.strip()


def normalize_date(d: str) -> str:
    """
    Best-effort normalization:
    - If already YYYY-MM-DD, return as-is.
    - Else, try 'DD MON YYYY' or 'DD <month_name> YYYY' (sv/en months) -> YYYY-MM-DD (day '??' if missing).
    - Else, return first 4-digit year found; if none, return the original string.
    """
    if not d:
        return ""
    s = d.strip()

    # Exact ISO date
    if _RE_ISO_FULL.match(s):
        return s

    # First 4-digit year (used as fallback)
    m = _RE_FIRST_YEAR.search(s)
    year = m.group(1) if m else ""

    month_map: Final[Dict[str, str]] = {
        "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04", "MAY": "05", "JUN": "06",
        "JUL": "07", "AUG": "08", "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
        "JANUARI": "01", "FEBRUARI": "02", "MARS": "03", "APRIL": "04", "MAJ": "05",
        "JUNI": "06", "JULI": "07", "AUGUSTI": "08", "SEPTEMBER": "09", "OKTOBER": "10",
        "NOVEMBER": "11", "DECEMBER": "12",
    }

    parts = s.replace(",", " ").split()
    if len(parts) >= 3:
        day = _RE_NON_DIGITS.sub("", parts[0])
        mon = month_map.get(parts[1].upper())
        yr = _RE_LAST_PART_YEAR.search(parts[-1])
        if mon and yr:
            return f"{yr.group(0)}-{mon}-{(day.zfill(2) if day else '??')}"

    # Fallback: just a year (or original string if no year)
    return year or s


def year_from(date_str: str) -> str:
    """
    Extract a 4-digit year from a date-like string.
    - Prefer YYYY from an ISO date YYYY-MM-DD.
    - Else, the first 4-digit sequence anywhere in the string.
    """
    if not date_str:
        return ""
    mfull = _RE_DATE_YMD.search(date_str)
    if mfull:
        return mfull.group(1)
    m = _RE_FIRST_YEAR.search(date_str)
    return m.group(1) if m else ""
