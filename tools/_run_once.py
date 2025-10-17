# tools/_run_once.py
from __future__ import annotations
import sys
import argparse
from pathlib import Path

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--src", required=True, help="Path to the source tree that has src/genreport")
    p.add_argument("--ged", required=True, help="Path to input GED file")
    p.add_argument("--root", default="1", help="Root individual (e.g. 1 or @I1@)")
    p.add_argument("--out", required=True, help="Output Markdown file path")
    args = p.parse_args()

    src_dir = Path(args.src).resolve()
    pkg_src = src_dir / "src"
    if not pkg_src.exists():
        sys.exit(f"Bad --src path (missing 'src'): {pkg_src}")

    # Put desired source at highest priority
    sys.path.insert(0, str(pkg_src))

    from genreport.ged import GedDocument
    from genreport.idmap import build_id_map
    from genreport.reports.mainexport import generate_mainexport

    in_path = Path(args.ged).resolve()
    out_path = Path(args.out).resolve()

    # Normalize root to @Ixxx@
    root_arg = args.root.strip()
    if not (root_arg.startswith("@") and root_arg.endswith("@")):
        root_arg = f"@I{root_arg}@"

    doc = GedDocument(in_path)
    idmap = build_id_map(doc, root_arg)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = generate_mainexport(in_path, out_path, idmap)
    print(f"[run_once] Wrote {out_path} ({count} individuals)")

if __name__ == "__main__":
    main()
