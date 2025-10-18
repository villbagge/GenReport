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
from typing import Final, Dict, List, Sequence

__all__ = [
    # existing exports (required elsewhere)
    "htmlish_to_text",
    "clean_place",
    "normalize_date",
    "year_from",
    # new/extended exports
    "htmlish_to_markdown",
    "format_bok_subfields",
    "PROVINCE_MAP",
    "COUNTRY_MAP",
]

# ----- Constants ---------------------------------------------------------------------------------

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

# ----- Precompiled regexes ----------------------------------------------------------------------

# htmlish_to_text / markdown
_RE_BR: Final = re.compile(r"(?i)<\s*br\s*/?\s*>")
_RE_P_CLOSE: Final = re.compile(r"(?i)</\s*p\s*>")
_RE_LI_CLOSE: Final = re.compile(r"(?i)</\s*li\s*>")
_RE_ANY_TAG: Final = re.compile(r"<[^>]+>")
_RE_SPACES: Final = re.compile(r"[ \t]{2,}")

# anchors for markdown conversion
_RE_A_HREF: Final = re.compile(
    r"(?is)<\s*a\b([^>]*?)\bhref\s*=\s*(?P<q>['\"])(?P<href>.*?)(?P=q)([^>]*)>(?P<text>.*?)</\s*a\s*>"
)
_RE_A_EMPTY_OR_NOHREF: Final = re.compile(r"(?is)<\s*a\b(?![^>]*\bhref=)[^>]*>\s*</\s*a\s*>")

# raw URLs (to purge blocked domains even if not in <a>)
_RE_RAW_URL: Final = re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE)

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

# ----- Bok sub-field normalization ---------------------------------------------------------------

# Recognized Bok keys (we glue/space/label around these)
# NOTE: For Sida/Rad we later drop the colon per your request (e.g., "Sida 532", "Rad 2")
_BOK_KEYS: Final = ("Land", "Bok", "Provins", "Plats", "Län", "Sida", "Rad", "fö")

# Insert colon+space after a key when it is glued to the value:
# LandSweden -> Land: Sweden, Sida204 -> Sida: 204, fö.Färnebo -> fö: Färnebo
_RE_BOK_GLUE_AFTER_KEY: Final = re.compile(
    r"\b("
    r"Land|Bok|Provins|Plats|Län|Sida|Rad|fö\.?"
    r")\s*([A-ZÅÄÖ0-9])"
)

# Ensure comma-space before the next key if missing:
# "... SwedenBok: Färnebo" -> "... Sweden, Bok: Färnebo"
_RE_BOK_COMMA_BEFORE_NEXT_KEY: Final = re.compile(
    r"([^\s,])\s*("
    r"Land|Bok|Provins|Plats|Län|Sida|Rad|fö"
    r")\b"
)

# Normalize 'fö.' to 'fö'
_RE_BOK_FO_DOT: Final = re.compile(r"\bfö\.\b", re.IGNORECASE)

# Tidy odd "Bok:," openings and ensure space after "Bok:"
_RE_BOK_PREFIX_COMMA: Final = re.compile(r"\bBok:\s*,")
_RE_BOK_PREFIX_SPACE: Final = re.compile(r"\bBok:\s*")

# Replace label "fö" with "Församling" (any case)
_RE_LABEL_FO: Final = re.compile(r"\bfö\b\s*:", re.IGNORECASE)

# After we’ve created "Sida: 204" / "Rad: 2", remove the colon per requested style.
_RE_SIDA_COLON: Final = re.compile(r"\bSida:\s+")
_RE_RAD_COLON: Final = re.compile(r"\bRad:\s+")


# ----- Helpers -----------------------------------------------------------------------------------

def _strip_empty_ends(lines: List[str]) -> List[str]:
    i, j = 0, len(lines) - 1
    while i <= j and not lines[i]:
        i += 1
    while j >= i and not lines[j]:
        j -= 1
    return lines[i : j + 1]


def _remove_remaining_tags(s: str) -> str:
    return _RE_ANY_TAG.sub("", s)


# ----- Public API: HTML-ish normalization -------------------------------------------------------

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
    t = _RE_BR.sub("\n", s)
    t = _RE_P_CLOSE.sub("\n", t)
    t = _RE_LI_CLOSE.sub("\n", t)
    t = _RE_ANY_TAG.sub("", t)

    prev = None
    loops = 0
    while prev != t and loops < 3:
        prev = t
        t = html.unescape(t)
        loops += 1

    t = t.replace("\xa0", " ").replace("\u00A0", " ")
    t = _RE_SPACES.sub(" ", t)

    lines = [ln.strip() for ln in t.splitlines()]
    lines = _strip_empty_ends(lines)
    return "\n".join(lines)


def htmlish_to_markdown(s: str, block_domains: Sequence[str] = ()) -> str:
    """
    Convert light HTML to conservative Markdown:
    - <br>, </p>, </li> -> newline
    - <a href="URL">Text</a>:
        * If href contains any domain in block_domains (case-insensitive),
          remove the entire link (both URL and link text).
        * Else render as [Text](URL)
    - Bare anchors without href are dropped.
    - Remove remaining tags, unescape entities (x3), keep line breaks.
    - Also remove any raw URLs whose host matches block_domains.
    - Collapse runs of spaces/tabs on each line; trim empty leading/trailing lines.
    """
    if not s:
        return ""
    t = s

    # Normalize line breaks
    t = _RE_BR.sub("\n", t)
    t = _RE_P_CLOSE.sub("\n", t)
    t = _RE_LI_CLOSE.sub("\n", t)

    # Remove empty/no-href anchors like <a id="..."></a>
    t = _RE_A_EMPTY_OR_NOHREF.sub("", t)

    # Prepare blocked list
    block_l = [d.lower() for d in block_domains]

    def _blocked(href: str) -> bool:
        h = (href or "").lower()
        return any(d in h for d in block_l)

    # Convert <a href=...>text</a>
    def _a_to_md(m: re.Match[str]) -> str:
        href = (m.group("href") or "").strip()
        text = (m.group("text") or "")
        if _blocked(href):
            return ""  # drop whole link including text
        inner = _remove_remaining_tags(text)
        inner_prev = None
        loops = 0
        while inner_prev != inner and loops < 3:
            inner_prev = inner
            inner = html.unescape(inner)
            loops += 1
        if not href:
            return inner
        return f"[{inner}]({href})"

    t = _RE_A_HREF.sub(_a_to_md, t)

    # Drop any other tags
    t = _RE_ANY_TAG.sub("", t)

    # Remove raw URLs from blocked domains
    if block_l:
        def _rm_blocked_raw(m: re.Match[str]) -> str:
            return "" if _blocked(m.group(0)) else m.group(0)
        t = _RE_RAW_URL.sub(_rm_blocked_raw, t)

    # Unescape entities globally (up to 3 passes)
    prev = None
    loops = 0
    while prev != t and loops < 3:
        prev = t
        t = html.unescape(t)
        loops += 1

    # Whitespace normalization per line (preserve line breaks)
    t = t.replace("\xa0", " ").replace("\u00A0", " ")
    lines = [_RE_SPACES.sub(" ", ln.strip()) for ln in t.splitlines()]
    lines = _strip_empty_ends(lines)
    return "\n".join(lines)


# ----- Bok sub-field normalization ---------------------------------------------------------------

def format_bok_subfields(line: str) -> str:
    """
    Normalize a line that contains Bok info:
      - Fix 'Bok:,' -> 'Bok:' and enforce 'Bok: ' (space after).
      - Turn glued key+value into 'Key: Value' (Land, Bok, Provins, Plats, Län, Sida, Rad, fö).
      - Insert ', ' before the next key if missing.
      - Replace label 'fö' with 'Församling'.
      - Remove colon after 'Sida:' and 'Rad:' -> 'Sida 532', 'Rad 2'.
      - Collapse multiple spaces (preserve line breaks).
    Keeps other content intact; preserves existing punctuation like ', 1891 - 1895'.
    """
    if "Bok" not in line:
        return line

    s = line

    # Tidy 'Bok:' prefix(s)
    s = _RE_BOK_PREFIX_COMMA.sub("Bok:", s)
    # Ensure a single space after every 'Bok:' label
    s = _RE_BOK_PREFIX_SPACE.sub("Bok: ", s)

    # Normalize fö. -> fö
    s = _RE_BOK_FO_DOT.sub("fö", s)

    # Insert colon after key if immediately followed by a value (capital/digit)
    def _glue_fix(m: re.Match[str]) -> str:
        key = m.group(1)
        nxt = m.group(2)
        key = "fö" if key.lower().startswith("fö") else key
        return f"{key}: {nxt}"

    s = _RE_BOK_GLUE_AFTER_KEY.sub(_glue_fix, s)

    # Ensure comma-space before a new key if missing
    s = _RE_BOK_COMMA_BEFORE_NEXT_KEY.sub(r"\1, \2", s)

    # Replace 'fö:' label with 'Församling:'
    s = _RE_LABEL_FO.sub("Församling: ", s)

    # Drop colon for Sida / Rad labels per requested style
    s = _RE_SIDA_COLON.sub("Sida ", s)
    s = _RE_RAD_COLON.sub("Rad ", s)

    # Collapse double spaces (do not touch line breaks)
    s = re.sub(r"[ ]{2,}", " ", s)
    return s


# ----- Other public API (unchanged behavior) ----------------------------------------------------

def clean_place(text: str) -> str:
    if not text:
        return ""
    txt = text

    def _cc_swap(m: re.Match[str]) -> str:
        cc = m.group(1).upper()
        return COUNTRY_MAP.get(cc, m.group(1))

    txt = _RE_CC_SWAP.sub(_cc_swap, txt)
    txt = _RE_SN.sub("socken", txt)
    txt = _RE_FO.sub("församling", txt)

    for abbr, full in PROVINCE_MAP.items():
        txt = re.sub(rf"\b{re.escape(abbr)}\b", full, txt)

    txt = _RE_TRAILING_SVERIGE.sub("", txt)
    txt = _RE_MULTI_SPACE.sub(" ", txt)
    return txt.strip()


def normalize_date(d: str) -> str:
    if not d:
        return ""
    s = d.strip()
    if _RE_ISO_FULL.match(s):
        return s
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
    return year or s


def year_from(date_str: str) -> str:
    if not date_str:
        return ""
    mfull = _RE_DATE_YMD.search(date_str)
    if mfull:
        return mfull.group(1)
    m = _RE_FIRST_YEAR.search(date_str)
    return m.group(1) if m else ""
