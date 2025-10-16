# === GENREPORT HEADER START ===
# GenReport — v0.3.0
# Commit: Merge OCCU and OCCU.PLAC into unified “Syssla” line
# Date: 2025-10-16
# Files: ged.py
# Changes:
#   Auto-stamp from post-commit
# === GENREPORT HEADER END ===


# src/genreport/ged.py
from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, Iterator, List, Tuple, Optional

from .normalize import htmlish_to_text, clean_place, normalize_date, year_from

LineRange = Tuple[int, int]
Field = Tuple[str, str, str]
Relation = Tuple[str, str, str]

DESC = {
    "NAME":"name","GIVN":"given name","SURN":"surname","NICK":"nickname","NPFX":"name prefix","NSFX":"name suffix",
    "SEX":"sex","BIRT":"birth","DEAT":"death","BURI":"burial","RESI":"residence","OCCU":"occupation","EDUC":"education",
    "MILI":"military service","EVEN":"event","TITL":"title","ALIA":"alias","FACT":"fact","DSCR":"description",
    "RELI":"religion","NATI":"nationality","IMMI":"immigration","EMIG":"emigration","BAPM":"baptism","CHR":"christening",
    "CONF":"confirmation",
    "DATE":"date","PLAC":"place","ADDR":"address","ADR1":"address line 1","ADR2":"address line 2","ADR3":"address line 3",
    "CITY":"city","STAE":"state","POST":"postal code","POSTAL_CODE":"postal code","CTRY":"country","TYPE":"type",
    "CAUS":"cause","NOTE":"note","TEXT":"text",
}

def tag_desc(field_id: str) -> str:
    parts = field_id.split(".")
    if len(parts) == 1:
        return DESC.get(parts[0], parts[0].lower())
    base = DESC.get(parts[0], parts[0].lower())
    sub = DESC.get(parts[1], parts[1].lower())
    return f"{base} {sub}"

# ---------- robust GED reader (UTF-8 preferred) with mojibake repair ----------
def _mojibake_score(s: str) -> int:
    return s.count("Ã") + s.count("Â") + s.count("â")

def _latin1_to_utf8_fix(s: str) -> str:
    before = _mojibake_score(s)
    if before == 0:
        return s
    try:
        fixed = s.encode("latin-1", errors="strict").decode("utf-8", errors="strict")
        after = _mojibake_score(fixed)
        if after < before:
            return fixed
    except Exception:
        try:
            fixed = s.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
            after = _mojibake_score(fixed)
            if after < before:
                return fixed
        except Exception:
            pass
    return s

def read_ged_lines(path: Path) -> List[str]:
    """
    Robustly read a GED file of unknown encoding.
    Prefer UTF-8/UTF-16 (BOM detected). If strict UTF-8 fails, try UTF-8 with replacement and
    keep it if replacements are tiny. Otherwise decode as Latin-1 and repair mojibake.
    """
    p = Path(path)
    raw = p.read_bytes()

    # UTF-16 BOM
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        try:
            text = raw.decode("utf-16")
            return text.replace("\x00", "").splitlines()
        except UnicodeDecodeError:
            pass

    # UTF-8 BOM
    if raw.startswith(b"\xef\xbb\xbf"):
        try:
            text = raw.decode("utf-8-sig")
            return text.splitlines()
        except UnicodeDecodeError:
            pass

    # 1) strict UTF-8
    try:
        text = raw.decode("utf-8")
        return text.replace("\x00", "").splitlines()
    except UnicodeDecodeError:
        pass

    # 2) UTF-8 with replacement: keep if very few replacements (better than Latin-1 mojibake)
    text_u8_rep = raw.decode("utf-8", errors="replace")
    rep_count = text_u8_rep.count("\uFFFD")
    if rep_count > 0 and rep_count / max(1, len(text_u8_rep)) < 0.0005:
        return text_u8_rep.replace("\x00", "").splitlines()

    # 3) Latin-1 path with mojibake repair
    try:
        text_l1 = raw.decode("latin-1")
    except Exception:
        text_l1 = raw.decode("latin-1", errors="ignore")

    fixed = _latin1_to_utf8_fix(text_l1)
    if _mojibake_score(fixed) > 0:
        fixed = "\n".join(_latin1_to_utf8_fix(ln) for ln in fixed.splitlines())
    return fixed.replace("\x00", "").splitlines()

# ---------- low-level parsing helpers ----------
def level_of(line: str) -> Optional[int]:
    m = re.match(r"^\s*(\d+)\s", line)
    return int(m.group(1)) if m else None

def tag_and_value(line: str) -> Tuple[str, str]:
    parts = line.strip().split(" ", 2)
    if len(parts) == 2:
        return parts[1], ""
    if len(parts) >= 3:
        if parts[1].startswith("@") and parts[1].endswith("@"):
            return parts[2], ""
        else:
            return parts[1], parts[2]
    return "", ""

def parse_blocks(lines: List[str], pattern: str) -> List[LineRange]:
    blocks: List[LineRange] = []
    i, n = 0, len(lines)
    comp = re.compile(pattern)
    while i < n:
        if comp.match(lines[i]):
            start = i
            i += 1
            while i < n and not re.match(r"^\s*0\s+", lines[i]):
                i += 1
            blocks.append((start, i))
        else:
            i += 1
    return blocks

def collect_text_with_continuations(lines: List[str], start_i: int, base_level: int) -> Tuple[str, int]:
    i = start_i + 1
    texts: List[str] = []
    while i < len(lines):
        line = lines[i]
        lvl = level_of(line)
        if lvl is None or lvl <= base_level:
            break
        tag, val = tag_and_value(line)
        if tag == "CONC":
            texts.append(val)
        elif tag == "CONT":
            texts.append("\n" + val)
        else:
            break
        i += 1
    return "".join(texts), i

def grab_subtree(lines: List[str], start: int, end: int, lvl: int):
    i = start
    while i < end:
        line = lines[i]
        l = level_of(line)
        if l is None or l < lvl:
            break
        if l == lvl:
            tag, val = tag_and_value(line)
            yield (l, tag, val, i)
        i += 1

def person_name_parts(lines: List[str], start: int, end: int) -> Tuple[str, str, str, str, str]:
    given = surname = nick = pre = suf = ""
    for l, tag, val, i in grab_subtree(lines, start + 1, end, 1):
        if tag == "NAME":
            full = (val or "")
            extra, j2 = collect_text_with_continuations(lines, i, 1)
            full += extra
            m = re.match(r"^(.*?)\s*/([^/]*)/(\s*(.*))?$", full.strip())
            if m:
                given = m.group(1).strip()
                surname = m.group(2).strip()
                trail = (m.group(4) or "").strip()
                if trail:
                    suf = trail
            # nested under NAME
            j = i + 1
            while j < end and (level_of(lines[j]) or 0) > 1:
                t2, v2 = tag_and_value(lines[j])
                if t2 == "GIVN":
                    given = v2 or given
                elif t2 == "SURN":
                    surname = v2 or surname
                elif t2 == "NICK":
                    extra2, k2 = collect_text_with_continuations(lines, j, level_of(lines[j]))
                    nick = (v2 + extra2).strip()
                    j = k2 - 1
                elif t2 == "NPFX":
                    pre = v2.strip()
                elif t2 == "NSFX":
                    suf = v2.strip()
                j += 1
            break
    return given, nick, surname, pre, suf

def formatted_name_line(given, nick, sur, pre, suf, by, dy, ged_id) -> str:
    parts = [given.strip()]
    nick = nick.strip().strip('"').strip("'")
    if nick:
        parts.append(nick)
    if sur:
        parts.append(sur.strip())
    name = " ".join([p for p in parts if p]).strip()
    sym = re.sub(r"\s+", "", (pre or "") + (suf or ""))
    if sym:
        name += " " + sym

    # --- dashed years here (so downstream can preserve exact intent) ---
    if by and dy:
        years = f"{by}-{dy}"
    elif by and not dy:
        years = f"{by}-"
    elif dy and not by:
        years = f"-{dy}"
    else:
        years = ""

    num = ged_id
    return f"{name} {years}, {num}".strip()

def get_id_number(xref: str) -> str:
    m = re.match(r"^@I(\d+)@$", xref)
    if m:
        return m.group(1)
    d = re.sub(r"\D", "", xref)
    return d if d else xref.strip("@")

# ---------- core document ----------
class GedDocument:
    """Parsed GED data with indices for individuals and families."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.lines = read_ged_lines(self.path)
        self.indi_map, self.fam_map = self._build_indices(self.lines)

        # numeric '123' -> '@I123@' fast map
        self._indi_num_to_xref: Dict[str, str] = {}
        for xref in self.indi_map.keys():
            m = re.search(r"@I(\d+)@", xref)
            if m:
                self._indi_num_to_xref[m.group(1)] = xref

        self.note_index = self._index_notes(self.lines)

    # ---------- indices ----------
    @staticmethod
    def _build_indices(lines: List[str]) -> Tuple[Dict[str, LineRange], Dict[str, LineRange]]:
        indi_blocks = parse_blocks(lines, r"^\s*0\s+@I[^@]*@\s+INDI\b")
        fam_blocks  = parse_blocks(lines, r"^\s*0\s+@F[^@]*@\s+FAM\b")
        indi_map: Dict[str, LineRange] = {}
        fam_map:  Dict[str, LineRange] = {}
        for s, e in indi_blocks:
            m = re.match(r"^\s*0\s+(@I[^@]*@)\s+INDI\b", lines[s])
            if m:
                indi_map[m.group(1)] = (s, e)
        for s, e in fam_blocks:
            m = re.match(r"^\s*0\s+(@F[^@]*@)\s+FAM\b", lines[s])
            if m:
                fam_map[m.group(1)] = (s, e)
        return indi_map, fam_map

    @staticmethod
    def _index_notes(lines: List[str]) -> Dict[str, str]:
        notes: Dict[str, str] = {}
        for s, e in parse_blocks(lines, r"^\s*0\s+@N[^@]*@\s+NOTE\b"):
            m = re.match(r"^\s*0\s+(@N[^@]*@)\s+NOTE\b", lines[s])
            if not m:
                continue
            key = m.group(1)
            buf: List[str] = []
            i = s + 1
            while i < e:
                lvl = level_of(lines[i])
                tag, val = tag_and_value(lines[i])
                if lvl == 1 and tag in ("CONC", "CONT", "TEXT"):
                    extra, i2 = collect_text_with_continuations(lines, i, lvl)
                    buf.append((val or "") + extra)
                    i = i2 - 1
                i += 1
            text = " ".join(t.strip() for t in buf if t.strip())
            text = re.sub(r"\s*\n\s*", " ", text)
            notes[key] = text
        return notes

    # ---------- iteration ----------
    def iter_individuals(self) -> Iterator[Tuple[str, LineRange]]:
        order: List[Tuple[int, str, int, int]] = []
        for xref, (s, e) in self.indi_map.items():
            n = re.sub(r"\D", "", xref)
            order.append((int(n) if n else 0, xref, s, e))
        order.sort()
        for _, xref, s, e in order:
            yield xref, (s, e)

    # ---------- per-person extraction ----------
    def collect_fields_for_individual(self, s: int, e: int) -> Tuple[str, List[Field], List[Relation]]:
        lines = self.lines
        given, nick, sur, pre, suf = person_name_parts(lines, s, e)

        # gather birth/death for header years
        birt_date = deat_date = ""
        i = s + 1
        while i < e:
            nxt = next(grab_subtree(lines, i, e, 1), (None, None, None, None))
            l, tag, val, idx = nxt
            if l is None:
                break
            if tag == "BIRT":
                j = idx + 1
                while j < e and (level_of(lines[j]) or 0) > 1:
                    t2, v2 = tag_and_value(lines[j])
                    if t2 == "DATE":
                        extra, j2 = collect_text_with_continuations(lines, j, level_of(lines[j]))
                        birt_date = normalize_date((v2 or "") + extra)
                        j = j2 - 1
                    j += 1
            elif tag == "DEAT":
                j = idx + 1
                while j < e and (level_of(lines[j]) or 0) > 1:
                    t2, v2 = tag_and_value(lines[j])
                    if t2 == "DATE":
                        extra, j2 = collect_text_with_continuations(lines, j, level_of(lines[j]))
                        deat_date = normalize_date((v2 or "") + extra)
                        j = j2 - 1
                    j += 1
            i = idx + 1

        by, dy = year_from(birt_date), year_from(deat_date)

        m = re.match(r"^\s*0\s+(@I[^@]*@)\s+INDI\b", lines[s])
        ged_xref = m.group(1)
        ged_num = get_id_number(ged_xref)
        header = formatted_name_line(given, nick, sur, pre, suf, by, dy, ged_num)

        # collect fields
        fields: List[Field] = []
        i = s + 1
        while i < e:
            lvl = level_of(lines[i])
            tag, val = tag_and_value(lines[i])
            if lvl != 1:
                i += 1
                continue

            # skip some admin tags at level 1
            if tag in ("FAMC", "FAMS", "RIN", "_UID", "_UPD", "NAME", "SEX"):
                i += 1
                continue

            content_lines: List[str] = []
            if val.strip():
                if tag in ("PLAC", "ADDR"):
                    content_lines.append(clean_place(val.strip()))
                else:
                    content_lines.append(htmlish_to_text(val.strip()))

            j = i + 1
            while j < e and (level_of(lines[j]) or 0) > lvl:
                t2, v2 = tag_and_value(lines[j])
                base_id = f"{tag}.{t2}"
                desc = tag_desc(base_id)

                if t2 in ("RIN", "_UID", "_UPD"):
                    j += 1
                    continue
                if tag == "NAME" and t2 in ("GIVN", "SURN"):
                    j += 1
                    continue

                if t2 == "PLAC":
                    extra, j2 = collect_text_with_continuations(lines, j, level_of(lines[j]))
                    place = clean_place((v2 or "") + extra)
                    if place:
                        fields.append((base_id, desc, place))
                    j = j2 - 1
                elif t2 in ("ADDR", "ADR1", "ADR2", "ADR3", "CITY", "STAE", "POST", "POSTAL_CODE", "CTRY"):
                    extra, j2 = collect_text_with_continuations(lines, j, level_of(lines[j]))
                    addr = ((v2 or "") + extra).strip()
                    if addr:
                        fields.append((base_id, desc, htmlish_to_text(addr)))
                    j = j2 - 1
                elif t2 == "DATE":
                    extra, j2 = collect_text_with_continuations(lines, j, level_of(lines[j]))
                    date = normalize_date((v2 or "") + extra)
                    if date:
                        fields.append((base_id, desc, date))
                    j = j2 - 1
                elif t2 == "NOTE":
                    extra, j2 = collect_text_with_continuations(lines, j, level_of(lines[j]))
                    if (v2 or "").strip().startswith("@") and (v2 or "").strip().endswith("@"):
                        resolved = self.note_index.get((v2 or "").strip(), "")
                        if resolved:
                            fields.append((base_id, desc, htmlish_to_text(resolved)))
                    else:
                        note = ((v2 or "") + extra).strip()
                        note = htmlish_to_text(note)
                        if note:
                            fields.append((base_id, desc, note))
                    j = j2 - 1
                elif t2 in ("CAUS", "TYPE", "TEXT"):
                    extra, j2 = collect_text_with_continuations(lines, j, level_of(lines[j]))
                    val2 = ((v2 or "") + extra).strip()
                    if val2:
                        fields.append((base_id, desc, htmlish_to_text(val2)))
                    j = j2 - 1
                else:
                    extra, j2 = collect_text_with_continuations(lines, j, level_of(lines[j]))
                    val2 = ((v2 or "") + extra).strip()
                    if val2:
                        fields.append((base_id, desc, htmlish_to_text(val2)))
                    j = j2 - 1
                j += 1

            if content_lines:
                content = ", ".join([c for c in content_lines if c])
                desc = tag_desc(tag)
                if content:
                    if tag in ("PLAC", "ADDR"):
                        content = clean_place(content)
                    fields.append((tag, desc, content))

            i = max(j, i + 1)

        # top-level individual NOTE
        i = s + 1
        while i < e:
            lvl = level_of(lines[i])
            tag, val = tag_and_value(lines[i])
            if lvl == 1 and tag == "NOTE":
                extra, i2 = collect_text_with_continuations(lines, i, lvl)
                if (val or "").strip().startswith("@") and (val or "").strip().endswith("@"):
                    resolved = self.note_index.get((val or "").strip(), "")
                    if resolved:
                        fields.append(("INDI.NOTE", "individual note", htmlish_to_text(resolved)))
                else:
                    note = ((val or "") + extra).strip()
                    if note:
                        fields.append(("INDI.NOTE", "individual note", htmlish_to_text(note)))
                i = i2 - 1
            i += 1

        # relations
        relations: List[Relation] = []
        famc: List[str] = []
        fams: List[str] = []

        i = s + 1
        while i < e:
            lvl = level_of(lines[i])
            tag, val = tag_and_value(lines[i])
            if lvl == 1 and tag == "FAMC":
                famc.append((val or "").strip())
            elif lvl == 1 and tag == "FAMS":
                fams.append((val or "").strip())
            i += 1

        def name_line_for_individual(indi_xref: str) -> str:
            if indi_xref not in self.indi_map:
                return ""
            ps, pe = self.indi_map[indi_xref]
            g, n, su, pr, sf = person_name_parts(lines, ps, pe)

            bd = dd = ""
            j = ps + 1
            while j < pe:
                nxt2 = next(grab_subtree(lines, j, pe, 1), (None, None, None, None))
                l2, t, v, idx = nxt2
                if l2 is None:
                    break
                if t == "BIRT":
                    k = idx + 1
                    while k < pe and (level_of(lines[k]) or 0) > 1:
                        t2, v2 = tag_and_value(lines[k])
                        if t2 == "DATE":
                            extra, k2 = collect_text_with_continuations(lines, k, level_of(lines[k]))
                            bd = normalize_date((v2 or "") + extra)
                            k = k2 - 1
                        k += 1
                elif t == "DEAT":
                    k = idx + 1
                    while k < pe and (level_of(lines[k]) or 0) > 1:
                        t2, v2 = tag_and_value(lines[k])
                        if t2 == "DATE":
                            extra, k2 = collect_text_with_continuations(lines, k, level_of(lines[k]))
                            dd = normalize_date((v2 or "") + extra)
                            k = k2 - 1
                        k += 1
                j = idx + 1
            by2, dy2 = year_from(bd), year_from(dd)
            gid = get_id_number(indi_xref)
            return formatted_name_line(g, n, su, pr, sf, by2, dy2, gid)

        # parents via FAMC
        for fam_id in famc:
            if fam_id not in self.fam_map:
                continue
            fs, fe = self.fam_map[fam_id]
            husb = wife = None
            j = fs + 1
            while j < fe:
                lvl = level_of(lines[j]); tag, val = tag_and_value(lines[j])
                if lvl == 1 and tag == "HUSB":
                    husb = (val or "").strip()
                if lvl == 1 and tag == "WIFE":
                    wife = (val or "").strip()
                j += 1
            if husb:
                nl = name_line_for_individual(husb)
                if nl:
                    relations.append(("PARENT", "parent", nl))
            if wife:
                nl = name_line_for_individual(wife)
                if nl:
                    relations.append(("PARENT", "parent", nl))

        # spouses & children via FAMS
        for fam_id in fams:
            if fam_id not in self.fam_map:
                continue
            fs, fe = self.fam_map[fam_id]
            husb = wife = None
            children: List[str] = []
            j = fs + 1
            while j < fe:
                lvl = level_of(lines[j]); tag, val = tag_and_value(lines[j])
                if lvl == 1 and tag == "HUSB":
                    husb = (val or "").strip()
                elif lvl == 1 and tag == "WIFE":
                    wife = (val or "").strip()
                elif lvl == 1 and tag == "CHIL":
                    children.append((val or "").strip())
                j += 1
            this_id = ged_xref
            sp = wife if husb == this_id else (husb if wife == this_id else None)
            if sp:
                nl = name_line_for_individual(sp)
                if nl:
                    relations.append(("SPOUSE", "spouse", nl))
            for c in children:
                nl = name_line_for_individual(c)
                if nl:
                    relations.append(("CHILD", "child", nl))

        return header, fields, relations

    # ---------- gender lookup ----------
    def get_gender_for_id(self, id_str: str) -> str:
        """
        Return 'M' (male), 'F' (female), or '' if unknown.
        Accepts '@I123@' or plain '123'.
        """
        if not id_str:
            return ""
        # direct xref?
        xref = id_str if id_str in self.indi_map else None
        if xref is None:
            digits = re.sub(r"\D", "", id_str)
            if digits:
                xref = self._indi_num_to_xref.get(digits)
                if xref is None:
                    cand = f"@I{digits}@"
                    if cand in self.indi_map:
                        xref = cand
        if xref is None:
            return ""
        s, e = self.indi_map[xref]
        i = s + 1
        while i < e:
            line = self.lines[i].strip()
            parts = line.split()
            if len(parts) >= 3 and parts[0] == "1" and parts[1].upper() == "SEX":
                sex = parts[2].upper()
                return sex if sex in ("M", "F") else ""
            i += 1
        return ""

__all__ = ["GedDocument"]
