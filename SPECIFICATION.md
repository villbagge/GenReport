# GenReport Specification (Updated v0.6.0)

## Overview

GenReport is a command-line tool for generating human-readable Markdown reports ("Persongalleri") from GEDCOM genealogical data files. Each individual entry is formatted to include birth, death, family relations, occupations, and relevant source material.

The output is intended for **readable documentation**, not for machine parsing.

---

## Architecture

**Core Modules**

* `src/genreport/normalize.py` — Utilities for text, place, and date normalization.
* `src/genreport/ged.py` — Parser and representation for GEDCOM data (`GedDocument`).
* `src/genreport/reports/mainexport.py` — Generates Markdown report output.
* `src/genreport/cli.py` — Command-line interface (`--input`, `--outdir`).
* `tools/verify_diff.py` — Utility for comparing output across versions.

**Public CLI API**

```
genreport --report mainexport --input <path_to_ged> --outdir <output_directory>
```

---

## Field Handling

### General

* Each individual is printed as a Markdown section (`## #ID Name`).
* Core fields (birth, death, occupation, relations) are rendered with dedicated formatters.
* All remaining GEDCOM fields are filtered or transformed via centralized rules in `fieldfilters.py`.

### Source Fields (`SOUR.*`)

All source fields are collected and printed together under a **"### Källor:"** heading at the end of each individual record.

#### Filtering Rules

| GEDCOM Field | Behavior                                 |
| ------------ | ---------------------------------------- |
| `SOUR.PAGE`  | Excluded if it contains `www.myheritage` |
| `SOUR.TEXT`  | Always included (converted to Markdown)  |
| `SOUR.ROLE`  | Always excluded                          |
| `SOUR._LINK` | Excluded if it contains `www.myheritage` |
| `SOUR._UID`  | Always excluded                          |
| `SOUR.EVEN`  | Always excluded                          |
| `SOUR.QUAY`  | Always excluded                          |

#### Markdown Conversion (`SOUR.TEXT`)

* HTML content within `SOUR.TEXT` is converted to Markdown.
* All hyperlinks containing `www.myheritage` are **removed entirely** (both URL and link text).
* Preserves line breaks and paragraph structure.
* Cleans up HTML artifacts (`<br>`, `<p>`, `<li>`, etc.) while unescaping entities (`&aring;` → `å`).

#### Bok Field Normalization

Within `SOUR.TEXT`, lines beginning with `Bok:` are automatically reformatted to ensure consistent spacing and labeling.

Recognized subfields include:

```
Land, Bok, Provins, Plats, Län, Sida, Församling (previously "fö"), Rad
```

Example transformation:

```
Input:
Bok:, Land: SwedenBokGrythyttan_AIIa7-1417, 1918 - 1935, Provins: VästmanlandPlatsSödra Högborn, Län: ÖrebroSida532, fö: GrythyttanRad2 Se hushållsmedlemmar

Output:
Bok: Land: Sweden, Bok: Grythyttan_AIIa7-1417, 1918 - 1935, Provins: Västmanland, Plats: Södra Högborn, Län: Örebro, Sida 532, Församling: Grythyttan, Rad 2 Se hushållsmedlemmar
```

This normalization ensures readability by inserting proper commas, colons, and spaces, while expanding `fö` to `Församling` and dropping colons from `Sida:` and `Rad:` labels.

#### Output Formatting

Each individual report includes a section similar to the following:

```
### Källor:
---
Födelse: 12 mar 1864 - Gåsborn
Hemvist: Mellan 1918 och 1935 - Södra Högborn, Grythyttan, Örebro, Västmanland, Sweden
Bok: Land: Sweden, Bok: Grythyttan_AIIa7-1417, 1918 - 1935, Provins: Västmanland, Plats: Södra Högborn, Län: Örebro, Sida 532, Församling: Grythyttan, Rad 2 Se hushållsmedlemmar
---
Födelse: 10 mar 1864 - Gåsborn Värml. län
Hemvist: Mellan 1918 och 1935 - Södra Högborn, Grythyttan, Örebro, Västmanland, Sweden
```

* Each `SOUR.TEXT` block is separated by a horizontal rule (`---`).
* Name-only header or footer lines (e.g. `Emma Kristina Samuelsdotter`) are automatically removed.
* Empty source blocks are skipped.

---

## Normalization

* Dates are normalized to `YYYY-MM-DD` when possible.
* Province and country codes are expanded (`VR` → `Värmland`, `US` → `USA`).
* Places are simplified for clarity (removing redundant `, Sverige`).

---

## Output Example

```
## #18 Emma Kristina Salomonsdotter ⁞⬤ 1864-1938
Född: 1864-03-12 i Värmland, Gåsborn socken [59.879, 14.333]
Död: 1938-06-21 i Västmanland, Grythyttan socken, Södra Högborn [59.642, 14.559]
Far: #37 Salomon Andersson ⁞⬤ 1819-1888
Mor: #38 Lisa Jansdotter ⁞⬤ 1826-1898
Vigd: #17 Karl Johan Sjö ⁞⬤ 1859-1919
Barn: #8 Anna Kristina Karlsson ⁞◕✻ 1890-1982
### Källor:
---
Födelse: 12 mar 1864 - Gåsborn
Hemvist: Mellan 1918 och 1935 - Södra Högborn, Grythyttan, Örebro, Västmanland, Sweden
Bok: Land: Sweden, Bok: Grythyttan_AIIa7-1417, 1918 - 1935, Provins: Västmanland, Plats: Södra Högborn, Län: Örebro, Sida 532, Församling: Grythyttan, Rad 2 Se hushållsmedlemmar
```

---

## Version

**Current Specification Version:** 0.6.0
**Last Updated:** 2025-10-18

Includes enhancements to source field filtering, Markdown conversion, and Bok formatting for robust, predictable output.
