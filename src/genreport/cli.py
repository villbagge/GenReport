# src/genreport/cli.py
from __future__ import annotations
import argparse
from pathlib import Path
import sys

from .reports import generate_mainexport

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="genreport",
        description="Generate Markdown/CSV-like genealogy reports from a GED file.",
    )
    parser.add_argument("--input", "-i", type=Path, required=True, help="Path to GED file")
    parser.add_argument(
        "--report",
        "-r",
        choices=["mainexport"],
        default="mainexport",
        help="Which report to run (default: mainexport)",
    )
    parser.add_argument(
        "--output", "-o", type=Path, default=Path("genreport_output.txt"), help="Output file path"
    )
    args = parser.parse_args()

    if args.report == "mainexport":
        count = generate_mainexport(args.input, args.output)
        print(f"Exported {count} individuals to {args.output}")
    else:
        print(f"Unknown report: {args.report}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
