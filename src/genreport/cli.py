# src/genreport/cli.py
from __future__ import annotations
import argparse
from pathlib import Path
import sys

from .reports import generate_mainexport


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="genreport",
        description="Generate Markdown genealogy report from a GED file.",
    )
    parser.add_argument("--input", "-i", type=Path, required=True, help="Path to GED file")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("genreport_output.md"),
        help="Output file path (Markdown format)",
    )
    args = parser.parse_args()

    count = generate_mainexport(args.input, args.output)
    print(f"Exported {count} individuals to {args.output}")


if __name__ == "__main__":
    main()
