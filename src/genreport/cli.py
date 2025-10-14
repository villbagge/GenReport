# src/genreport/cli.py
from __future__ import annotations
import argparse
from pathlib import Path

from .reports import generate_mainexport


def _next_available_persongalleri(outdir: Path) -> Path:
    """
    Generate 'persongalleri.md' in outdir; if it exists, use 'persongalleri (2).md',
    then 'persongalleri (3).md', etc.
    """
    base = outdir / "persongalleri.md"
    if not base.exists():
        return base
    n = 2
    while True:
        candidate = outdir / f"persongalleri ({n}).md"
        if not candidate.exists():
            return candidate
        n += 1


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="genreport",
        description="Generate a Markdown genealogy gallery from a GED file.",
    )
    parser.add_argument("--input", "-i", type=Path, required=True, help="Path to GED file")
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("."),
        help="Output directory (filename is fixed to persongalleri.md with numbering if needed)",
    )
    args = parser.parse_args()

    outdir: Path = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = _next_available_persongalleri(outdir)

    count = generate_mainexport(args.input, out_path)
    print(f"Exported {count} individuals to {out_path}")


if __name__ == "__main__":
    main()
