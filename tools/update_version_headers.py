# tools/update_version_headers.py
from __future__ import annotations
import argparse, subprocess, sys, datetime, glob
from pathlib import Path
from typing import Iterable

HEADER_START = "# === GENREPORT HEADER START ==="
HEADER_END   = "# === GENREPORT HEADER END ==="

TEMPLATE = """{start}
# GenReport — {version}
# Commit: {message}
# Date: {date}
# Files: {filename}
# Changes:
#   {changes}
{end}
"""

def get_git_info() -> tuple[str, str, str]:
    """Return (version, message, date) from git; fall back to placeholders."""
    def run(cmd: list[str]) -> str:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8").strip()
    try:
        # tag like v0.2.0 if present
        version = run(["git", "describe", "--tags", "--abbrev=0"])
    except Exception:
        version = "untracked"
    try:
        message = run(["git", "log", "-1", "--pretty=%s"])
        date = run(["git", "log", "-1", "--pretty=%cs"])  # YYYY-MM-DD
    except Exception:
        message = "(no commit message)"
        date = datetime.date.today().isoformat()
    return version, message, date

def build_header(version: str, message: str, date: str, filename: str, changes: str) -> str:
    safe_changes = changes.replace("\n", "\n#   ").strip() or "(see commit)"
    return TEMPLATE.format(
        start=HEADER_START,
        version=version,
        message=message,
        date=date,
        filename=filename,
        changes=safe_changes,
        end=HEADER_END,
    )

def apply_header(path: Path, version: str, message: str, date: str, changes: str) -> bool:
    text = path.read_text(encoding="utf-8")
    header = build_header(version, message, date, path.name, changes)

    if HEADER_START in text and HEADER_END in text:
        pre, rest = text.split(HEADER_START, 1)
        _, post = rest.split(HEADER_END, 1)
        new_text = pre + header + post
    else:
        # insert at very top, then a blank line
        new_text = header + "\n" + text

    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False

def iter_targets(files: list[str], globs: list[str]) -> Iterable[Path]:
    seen: set[Path] = set()
    for f in files:
        p = Path(f)
        if p.exists():
            seen.add(p.resolve())
    for pattern in globs:
        for g in glob.glob(pattern, recursive=True):
            p = Path(g)
            if p.suffix == ".py" and p.exists():
                seen.add(p.resolve())
    return sorted(seen)

def main() -> int:
    ap = argparse.ArgumentParser(description="Update GenReport version headers in files.")
    ap.add_argument("--version", help="Version/tag, e.g. v0.2.0. Use --auto to read from git.")
    ap.add_argument("--message", help="Commit message. Use --auto for last commit.")
    ap.add_argument("--date", help="Date YYYY-MM-DD. Use --auto for last commit.")
    ap.add_argument("--changes", default="", help="One-line change summary for header.")
    ap.add_argument("--files", nargs="*", default=[], help="Explicit files to update")
    ap.add_argument("--glob", nargs="*", default=["src/genreport/**/*.py"], help="Glob(s) of files")
    ap.add_argument("--auto", action="store_true", help="Take version/message/date from git")
    args = ap.parse_args()

    if args.auto:
        gv, gm, gd = get_git_info()
        version = gv
        message = args.message or gm
        date = args.date or gd
    else:
        version = args.version or "untracked"
        message = args.message or "(no message)"
        date = args.date or datetime.date.today().isoformat()

    changed = False
    targets = list(iter_targets(args.files, args.glob))
    if not targets:
        print("No target files found.")
        return 1

    for p in targets:
        if apply_header(p, version=version, message=message, date=date, changes=args.changes):
            print(f"Updated header in {p}")
            changed = True

    return 0 if changed else 0

if __name__ == "__main__":
    sys.exit(main())
