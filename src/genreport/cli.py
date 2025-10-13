import argparse
from . import run

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="genreport",
        description="Generate Markdown genealogy reports from GED files.",
    )
    parser.add_argument("--input", help="Path to GED file", required=False)
    _ = parser.parse_args()
    run()

if __name__ == "__main__":
    main()
