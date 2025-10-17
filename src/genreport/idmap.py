# === GENREPORT HEADER START ===
# GenReport — v0.4.0
# Commit: Add automated verify_diff tool with Notepad integration
# Date: 2025-10-17
# Files: idmap.py
# Changes:
#   Auto-stamp from post-commit
# === GENREPORT HEADER END ===



# src/genreport/idmap.py
from __future__ import annotations
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict, deque
import re

from .ged import GedDocument, level_of, tag_and_value

# ---------------------------------------------------------------------
# Exception: fixed-number series for a specific sibling group
# ---------------------------------------------------------------------
SPECIAL_EXCEPTION_XREFS: list[str] = [
    "@I501665@",
    "@I501670@",
    "@I501674@",
    "@I501681@",
    "@I501682@",
    "@I501683@",
    "@I501684@",
]
SPECIAL_START = 9001  # Assign 9001, 9002, ... in this order

# ---------------------------------------------------------------------
# Basic GED helpers
# ---------------------------------------------------------------------

def _families_of_spouse(doc: GedDocument, indi_xref: str) -> List[str]:
    """Families where the person is a spouse (FAMS)."""
    if indi_xref not in doc.indi_map:
        return []
    s, e = doc.indi_map[indi_xref]
    fams: List[str] = []
    i = s + 1
    while i < e:
        if level_of(doc.lines[i]) == 1:
            tag, val = tag_and_value(doc.lines[i])
            if tag == "FAMS":
                fams.append((val or "").strip())
        i += 1
    return fams


def _parents_of(doc: GedDocument, indi_xref: str) -> List[str]:
    """Return [father?, mother?] (HUSB then WIFE) if a FAMC exists."""
    if indi_xref not in doc.indi_map:
        return []
    s, e = doc.indi_map[indi_xref]
    famc: Optional[str] = None
    i = s + 1
    while i < e:
        if level_of(doc.lines[i]) == 1:
            tag, val = tag_and_value(doc.lines[i])
            if tag == "FAMC":
                famc = (val or "").strip()
                break
        i += 1
    if not famc or famc not in doc.fam_map:
        return []
    fs, fe = doc.fam_map[famc]
    father = mother = None
    j = fs + 1
    while j < fe:
        if level_of(doc.lines[j]) == 1:
            tag, val = tag_and_value(doc.lines[j])
            if tag == "HUSB":
                father = (val or "").strip()
            elif tag == "WIFE":
                mother = (val or "").strip()
        j += 1
    out: List[str] = []
    if father:
        out.append(father)
    if mother:
        out.append(mother)
    return out


def _family_parents_children(doc: GedDocument, fam_xref: str) -> Tuple[Optional[str], Optional[str], List[str]]:
    if fam_xref not in doc.fam_map:
        return None, None, []
    s, e = doc.fam_map[fam_xref]
    husb = wife = None
    kids: List[str] = []
    i = s + 1
    while i < e:
        if level_of(doc.lines[i]) == 1:
            tag, val = tag_and_value(doc.lines[i])
            if tag == "HUSB":
                husb = (val or "").strip()
            elif tag == "WIFE":
                wife = (val or "").strip()
            elif tag == "CHIL":
                kids.append((val or "").strip())
        i += 1
    return husb, wife, kids


def _birth_tuple(doc: GedDocument, indi_xref: str) -> tuple:
    """Return sortable (YYYY,MM,DD) — unknowns → 9999 so they go last."""
    y = m = d = 9999
    if indi_xref in doc.indi_map:
        s, e = doc.indi_map[indi_xref]
        i = s + 1
        while i < e:
            if level_of(doc.lines[i]) == 1:
                tag, val = tag_and_value(doc.lines[i])
                if tag == "BIRT":
                    j = i + 1
                    while j < e and (level_of(doc.lines[j]) or 0) > 1:
                        t2, v2 = tag_and_value(doc.lines[j])
                        if t2 == "DATE" and v2:
                            m1 = re.search(r"(\d{4})(?:[- /.](\d{1,2}))?(?:[- /.](\d{1,2}))?", v2)
                            if m1:
                                try:
                                    y = int(m1.group(1))
                                    if m1.group(2):
                                        m = int(m1.group(2))
                                    if m1.group(3):
                                        d = int(m1.group(3))
                                except Exception:
                                    pass
                            break
                        j += 1
                    break
            i += 1
    return (y, m, d)


def _sort_children_oldest_first(doc: GedDocument, children: List[str]) -> List[str]:
    """Stable-sort children by birth date oldest→youngest."""
    indexed = list(enumerate(children))
    return [x for _, x in sorted(indexed, key=lambda t: (_birth_tuple(doc, t[1]), t[0]))]

# ---------------------------------------------------------------------
# Media-only placeholder detection
# ---------------------------------------------------------------------

def _is_media_only_placeholder(doc: GedDocument, xref: str) -> bool:
    """
    True if the INDI has no NAME and no family links (FAMC/FAMS) but has one or more OBJE.
    These are typically 'Unassociated photos' holders and should not be treated as people.
    """
    if xref not in doc.indi_map:
        return False
    s, e = doc.indi_map[xref]
    has_name = has_fam = has_obje = False
    i = s + 1
    while i < e:
        lvl = level_of(doc.lines[i])
        tag, val = tag_and_value(doc.lines[i])
        if lvl == 1:
            if tag == "NAME" and (val or "").strip():
                has_name = True
            elif tag in ("FAMC", "FAMS"):
                has_fam = True
            elif tag == "OBJE":
                has_obje = True
        i += 1
    return (not has_name) and (not has_fam) and has_obje

# ---------------------------------------------------------------------
# Connectivity
# ---------------------------------------------------------------------

def find_disconnected(doc: GedDocument, root_xref: str) -> Set[str]:
    """
    Return set of xrefs that are NOT connected to the root via spouse/parent/child edges,
    excluding media-only placeholder INDI records.
    """
    adj: Dict[str, Set[str]] = defaultdict(set)

    # Build undirected adjacency from families
    for fam_xref, (fs, fe) in doc.fam_map.items():
        husb = wife = None
        kids: List[str] = []
        i = fs + 1
        while i < fe:
            if level_of(doc.lines[i]) == 1:
                tag, val = tag_and_value(doc.lines[i])
                if tag == "HUSB":
                    husb = (val or "").strip()
                elif tag == "WIFE":
                    wife = (val or "").strip()
                elif tag == "CHIL":
                    kids.append((val or "").strip())
            i += 1
        if husb and wife:
            adj[husb].add(wife); adj[wife].add(husb)
        for c in kids:
            if husb:
                adj[husb].add(c); adj[c].add(husb)
            if wife:
                adj[wife].add(c); adj[c].add(wife)

    # Candidate people = all INDI except media-only placeholders
    all_people = {x for x in doc.indi_map.keys() if not _is_media_only_placeholder(doc, x)}

    # BFS from root
    visited: Set[str] = set()
    if root_xref in all_people:
        q = deque([root_xref])
        visited.add(root_xref)
        while q:
            u = q.popleft()
            for v in adj.get(u, ()):
                if v in all_people and v not in visited:
                    visited.add(v)
                    q.append(v)

    return all_people - visited

# ---------------------------------------------------------------------
# Ancestor layering
# ---------------------------------------------------------------------

def _ancestor_layers(doc: GedDocument, root_xref: str) -> List[List[str]]:
    """Return [[gen0],[gen1],...] left→right (father then mother)."""
    layers: List[List[str]] = []
    visited: Set[str] = set()
    current = [root_xref]
    while current:
        layer: List[str] = []
        for x in current:
            if x and x not in visited:
                visited.add(x)
                layer.append(x)
        if not layer:
            break
        layers.append(layer)
        nxt: List[str] = []
        for x in layer:
            nxt.extend([p for p in _parents_of(doc, x) if p])
        current = nxt
    return layers

# ---------------------------------------------------------------------
# ID assignment (no persistence) + exception list
# ---------------------------------------------------------------------

def build_id_map(doc: GedDocument, root_xref: str) -> Dict[str, int]:
    """
    Compute a fresh ID map each run.
    - Ancestors: 0=root, 1=father, 2=mother, then by layer left→right
    - Non-ancestors: next full thousand upward, by generation −1,0,1,2…
    - Exception: assign SPECIAL_EXCEPTION_XREFS to 9001, 9002, ...
    """
    idmap: Dict[str, int] = {}
    layers = _ancestor_layers(doc, root_xref)
    ancestor_list = [x for layer in layers for x in layer]
    ancestor_set = set(ancestor_list)

    next_id = 0
    for x in ancestor_list:
        idmap[x] = next_id
        next_id += 1

    last_ancestor = next_id - 1
    start_non_anc = ((last_ancestor // 1000) + 1) * 1000 if last_ancestor >= 0 else 1000

    buckets: Dict[int, List[str]] = defaultdict(list)
    seen: Set[str] = set()

    def _add(gen_idx: int, x: str):
        if not x or x in ancestor_set or x in idmap or x in seen:
            return
        seen.add(x)
        buckets[gen_idx].append(x)

    # Populate non-ancestor buckets
    for L, layer in enumerate(layers):
        for A in layer:
            for fam in _families_of_spouse(doc, A):
                husb, wife, kids = _family_parents_children(doc, fam)
                other = wife if husb == A else (husb if wife == A else None)
                if other and other not in ancestor_set:
                    _add(L, other)
                for c in kids:
                    if c not in ancestor_set:
                        _add(L - 1, c)

    # Order buckets
    root_father = root_mother = None
    if len(layers) >= 2 and layers[1]:
        root_father = layers[1][0] if len(layers[1]) >= 1 else None
        root_mother = layers[1][1] if len(layers[1]) >= 2 else None

    if -1 in buckets:
        kids_all: List[str] = []
        for fam in _families_of_spouse(doc, root_xref):
            _, _, kids = _family_parents_children(doc, fam)
            kids_all.extend([c for c in kids if c in buckets[-1]])
        seen_k = set(); uniq = []
        for c in kids_all:
            if c not in seen_k:
                seen_k.add(c); uniq.append(c)
        buckets[-1] = _sort_children_oldest_first(doc, uniq)

    if 0 in buckets:
        spouses_root = []
        for fam in _families_of_spouse(doc, root_xref):
            husb, wife, _ = _family_parents_children(doc, fam)
            other = wife if husb == root_xref else (husb if wife == root_xref else None)
            if other and other in buckets[0]:
                spouses_root.append(other)

        full_sibs: List[str] = []
        if root_father and root_mother:
            for fam in _families_of_spouse(doc, root_father):
                husb, wife, kids = _family_parents_children(doc, fam)
                if {husb, wife} == {root_father, root_mother}:
                    full_sibs = [c for c in kids if c != root_xref and c in buckets[0]]
                    break
        full_sibs = _sort_children_oldest_first(doc, list(dict.fromkeys(full_sibs)))

        order0 = spouses_root + full_sibs
        for x in buckets[0]:
            if x not in order0:
                order0.append(x)
        buckets[0] = order0

    for g in sorted(buckets.keys()):
        if g in (-1, 0):
            continue
        idxd = list(enumerate(buckets[g]))
        idxd.sort(key=lambda t: (_birth_tuple(doc, t[1]), t[0]))
        buckets[g] = [x for _, x in idxd]

    # Assign regular non-ancestor IDs
    next_non = start_non_anc
    used_ids: Set[int] = set(idmap.values())
    for g in sorted(buckets.keys()):
        for x in buckets[g]:
            if x not in idmap:
                while next_non in used_ids:
                    next_non += 1
                idmap[x] = next_non
                used_ids.add(next_non)
                next_non += 1

    # ------------------ EXCEPTION ASSIGNMENT ------------------
    # Assign the special seven siblings to 9001, 9002, ... (in the given order),
    # but do NOT overwrite if they already got an ID.
    curr = SPECIAL_START
    for x in SPECIAL_EXCEPTION_XREFS:
        if x in doc.indi_map and x not in idmap:
            while curr in used_ids:  # avoid collisions, just in case
                curr += 1
            idmap[x] = curr
            used_ids.add(curr)
            curr += 1
    # ----------------------------------------------------------

    return idmap

# ---------------------------------------------------------------------
# Lookup & pretty printing
# ---------------------------------------------------------------------

def get_id_for_xref(idmap: Dict[str, int], xref: str) -> Optional[int]:
    return idmap.get(xref)


def get_id_for_numeric(doc: GedDocument, idmap: Dict[str, int], num_str: str) -> Optional[int]:
    """Given '123', resolve to '@I123@' then return assigned id."""
    xref = doc._indi_num_to_xref.get(num_str)
    if not xref:
        cand = f"@I{num_str}@"
        if cand in doc.indi_map:
            xref = cand
    return idmap.get(xref) if xref else None


def _name_from_name_tag(raw: str) -> str:
    """Strip slashes and tidy spacing in GEDCOM NAME values."""
    raw = (raw or "").strip()
    name = raw.replace("/", " ").strip()
    name = re.sub(r"\s+", " ", name)
    return name


def person_name_and_years(doc: GedDocument, xref: str) -> str:
    """Return 'Full Name YYYY-YYYY' (partial if unknown)."""
    if xref not in doc.indi_map:
        return xref
    s, e = doc.indi_map[xref]
    name = None
    by = dy = None

    i = s + 1
    while i < e:
        lvl = level_of(doc.lines[i])
        tag, val = tag_and_value(doc.lines[i])
        if lvl == 1 and tag == "NAME" and name is None:
            name = _name_from_name_tag(val or "")
        if lvl == 1 and tag == "BIRT":
            j = i + 1
            while j < e and (level_of(doc.lines[j]) or 0) > 1:
                t2, v2 = tag_and_value(doc.lines[j])
                if t2 == "DATE" and v2:
                    m = re.search(r"(\d{4})", v2)
                    if m:
                        by = m.group(1)
                        break
                j += 1
        if lvl == 1 and tag == "DEAT":
            j = i + 1
            while j < e and (level_of(doc.lines[j]) or 0) > 1:
                t2, v2 = tag_and_value(doc.lines[j])
                if t2 == "DATE" and v2:
                    m = re.search(r"(\d{4})", v2)
                    if m:
                        dy = m.group(1)
                        break
                j += 1
        i += 1

    years = ""
    if by and dy:
        years = f" {by}-{dy}"
    elif by and not dy:
        years = f" {by}-"
    elif not by and dy:
        years = f" -{dy}"
    return f"{name or xref}{years}"
