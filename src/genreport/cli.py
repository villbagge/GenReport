# === GENREPORT HEADER START ===
# GenReport — v0.4.0
# Commit: Add files for diff testing
# Date: 2025-10-17
# Files: cli.py
# Changes:
#   Auto-stamp from post-commit
# === GENREPORT HEADER END ===


# src/genreport/cli.py
from __future__ import annotations
import argparse
from pathlib import Path
import sys

from .ged import GedDocument
from .idmap import build_id_map, find_disconnected, person_name_and_years
from .reports import generate_mainexport


def _unique_persongalleri_path(outdir: Path) -> Path:
    """
    Always write Markdown and always name it 'persongalleri.md'.
    If that exists, append a numeric suffix: persongalleri-2.md, -3.md, ...
    """
    outdir.mkdir(parents=True, exist_ok=True)
    base = outdir / "persongalleri.md"
    if not base.exists():
        return base
    i = 2
    while True:
        cand = outdir / f"persongalleri-{i}.md"
        if not cand.exists():
            return cand
        i += 1


def _resolve_root_xref(doc: GedDocument, root_arg: str | None) -> str:
    """
    Accepts @I123@ or 123. If omitted, defaults to the first individual in the file.
    """
    if root_arg:
        r = root_arg.strip()
        if r.startswith("@") and r.endswith("@"):
            xref = r
        else:
            xref = doc._indi_num_to_xref.get(r) or f"@I{r}@"
        if xref not in doc.indi_map:
            raise SystemExit(f"Root '{root_arg}' not found in GED.")
        return xref
    # default: first person in file
    try:
        return next(doc.iter_individuals())[0]
    except StopIteration:
        raise SystemExit("No individuals found in GED.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Markdown genealogy reports from GED files."
    )
    parser.add_argument("--input", required=True, help="Path to GED file")
    parser.add_argument(
        "--report",
        default="mainexport",
        help="Report type (default: mainexport)",
    )
    parser.add_argument(
        "--outdir",
        default=".",
        help="Directory where the output Markdown file will be written",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Root individual (@I123@ or 123) for custom ID numbering (root=0)",
    )
    parser.add_argument(
        "--allow-islands",
        action="store_true",
        help="Allow executing even if disconnected individuals (islands) are present",
    )

    args = parser.parse_args()

    in_path = Path(args.input)
    outdir = Path(args.outdir)

    if not in_path.exists():
        raise SystemExit(f"Input GED not found: {in_path}")

    # Build document and resolve root xref
    doc = GedDocument(in_path)
    root_xref = _resolve_root_xref(doc, args.root)

    # Strict connectivity by default
    islands = find_disconnected(doc, root_xref)
    if islands:
        # Prepare a readable preview list (limit to 20)
        preview = []
        for x in list(islands)[:20]:
            preview.append(f"  - {person_name_and_years(doc, x)}  ({x})")
        more = ""
        if len(islands) > 20:
            more = f"\n  ... and {len(islands) - 20} more"
        msg = (
            f"\n\033[91m✖ Connectivity check failed:\033[0m "
            f"Found {len(islands)} disconnected individual(s) not linked to the chosen root.\n"
            f"Examples:\n" + "\n".join(preview) + more +
            "\nTip: verify --root, fix family links, or re-run with --allow-islands to proceed anyway.\n"
        )
        if not args.allow_islands:
            sys.stderr.write(msg)
            raise SystemExit(2)
        else:
            sys.stderr.write(
                msg.replace("failed", "warning")
                   .replace("✖", "⚠")
            )

    # Build fresh in-memory ID map (no persistence)
    idmap = build_id_map(doc, root_xref)

    # We currently only implement 'mainexport'
    if args.report != "mainexport":
        print(f"Unknown report '{args.report}', using 'mainexport'.", file=sys.stderr)

    out_path = _unique_persongalleri_path(outdir)
    count = generate_mainexport(in_path, out_path, idmap)

    print(f"Exported {count} individuals to {out_path}")


if __name__ == "__main__":
    main()
