# src/genreport/normalize.py
import re, html

PROVINCE_MAP = {
    "BL":"Blekinge","BO":"Bohuslän","DR":"Dalarna","DS":"Dalsland","GO":"Gotland",
    "GÄ":"Gästrikland","HA":"Halland","HS":"Hälsingland","HR":"Härjedalen","JÄ":"Jämtland",
    "LA":"Lappland","ME":"Medelpad","NÄ":"Närke","SK":"Skåne","SM":"Småland",
    "SÖ":"Södermanland","UP":"Uppland","VR":"Värmland","VB":"Västerbotten","VG":"Västergötland",
    "VS":"Västmanland","ÅN":"Ångermanland","ÖL":"Öland","ÖG":"Östergötland"
}

COUNTRY_MAP = {
    "US":"USA","TR":"Turkiet","RU":"Ryssland","PL":"Polen","NO":"Norge","NL":"Nederländerna",
    "LV":"Lettland","IT":"Italien","IS":"Island","GB":"Storbrittanien","FR":"Frankrike",
    "FI":"Finland","DK":"Danmark","DE":"Tyskland","CZ":"Tjeckien","BE":"Belgien","EE":"Estland"
}

def htmlish_to_text(s: str) -> str:
    if not s: return ""
    t = s
    t = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", t)
    t = re.sub(r"(?i)</\s*p\s*>", "\n", t)
    t = re.sub(r"(?i)</\s*li\s*>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    prev=None; loops=0
    while prev != t and loops < 3:
        prev=t; t=html.unescape(t); loops+=1
    t = t.replace("\xa0"," ").replace("\u00A0"," ")
    t = re.sub(r"[ \t]{2,}", " ", t)
    lines = [ln.strip() for ln in t.splitlines()]
    while lines and not lines[0]: lines.pop(0)
    while lines and not lines[-1]: lines.pop()
    return "\n".join(lines)

def clean_place(text: str) -> str:
    if not text: return ""
    txt = text

    def _cc_swap(m):
        cc = m.group(1).upper()
        return COUNTRY_MAP.get(cc, m.group(0))

    # Swap .DE etc.
    txt = re.sub(r'(?<!\w)\.(US|TR|RU|PL|NO|NL|LV|IT|IS|GB|FR|FI|DK|DE|CZ|BE|EE)\b', _cc_swap, txt)
    # Swedish normalizations
    txt = re.sub(r"\b[Ss]n\b", "socken", txt)
    txt = re.sub(r"\bfö\b", "församling", txt)
    for abbr, full in PROVINCE_MAP.items():
        txt = re.sub(rf"\b{re.escape(abbr)}\b", full, txt)
    # Remove trailing ", Sverige"
    txt = re.sub(r",\s*Sverige\b", "", txt)
    txt = re.sub(r"[ ]{2,}", " ", txt)
    return txt.strip()

def normalize_date(d: str) -> str:
    if not d: return ""
    s = d.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s): return s
    m = re.search(r"(\d{4})", s); year = m.group(1) if m else ""

    month_map = {
        "JAN":"01","FEB":"02","MAR":"03","APR":"04","MAY":"05","JUN":"06","JUL":"07","AUG":"08","SEP":"09","OCT":"10","NOV":"11","DEC":"12",
        "JANUARI":"01","FEBRUARI":"02","MARS":"03","APRIL":"04","MAJ":"05","JUNI":"06","JULI":"07","AUGUSTI":"08","SEPTEMBER":"09","OKTOBER":"10","NOVEMBER":"11","DECEMBER":"12"
    }
    parts = s.replace(",", " ").split()
    if len(parts) >= 3:
        day = re.sub(r"\D", "", parts[0])
        mon = month_map.get(parts[1].upper())
        yr = re.search(r"\d{4}", parts[-1])
        if mon and yr:
            return f"{yr.group(0)}-{mon}-{(day.zfill(2) if day else '??')}"
    return year or s

def year_from(date_str: str) -> str:
    if not date_str: return ""
    mfull = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", date_str)
    if mfull: return mfull.group(1)
    m = re.search(r"(\d{4})", date_str)
    return m.group(1) if m else ""
