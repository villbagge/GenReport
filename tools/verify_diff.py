# tools/verify_diff.py
from __future__ import annotations
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
import difflib
import shlex

ALLOWED_PREFIXES_DEFAULT = ["SOUR."]  # Only allow changes to these line prefixes

def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    p = subprocess.Popen(cmd, cwd=str(cwd) if cwd else None,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate()
    return p.returncode, out, err

def read_text(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").splitlines(keepends=False)

def summarize_diff(a_lines: list[str], b_lines: list[str]) -> tuple[str, bool, list[str]]:
    """
    Returns (summary_text, ok, changed_lines)
    ok=True if all changes are within allowed prefixes
    """
    diff = list(difflib.ndiff(a_lines, b_lines))
    summary = []
    changed_lines = []  # raw changed lines without marker
    # We collapse '? ' helper lines from ndiff
    for line in diff:
        if line.startswith("?"):
            continue
        if line.startswith("- "):
            payload = line[2:]
            summary.append(f"- {payload[:50]}")
            changed_lines.append(payload)
        elif line.startswith("+ "):
            payload = line[2:]
            summary.append(f"+ {payload[:50]}")
            changed_lines.append(payload)
        elif line.startswith("  "):
            # equal line
            continue
    # Anything that is changed (added/removed) but where both sides share same prefix
    # will appear as +/- pairs. We also want a '≠' marker for changed lines at same position.
    # Use unified diff to detect modifications by context.
    udiff = list(difflib.unified_diff(a_lines, b_lines, n=0))
    for l in udiff:
        # lines start with '+' or '-' inside hunks; headers start with '---'/'+++'
        pass
    # For our summary we already show +/-; that's fine. We can also mark pairs as '≠' later if needed.

    # Enforce allowed prefixes
    allowed_prefixes = ALLOWED_PREFIXES_DEFAULT
    def allowed(line: str) -> bool:
        return any(line.startswith(pref) for pref in allowed_prefixes)

    ok = True
    for l in changed_lines:
        if l.strip() == "":  # blank lines allowed
            continue
        if not allowed(l):
            ok = False
            break

    # Build pretty header
    header = "seems ok" if ok else "bad changes detected"
    return header + "\n" + "\n".join(summary), ok, changed_lines

def main() -> None:
    ap = argparse.ArgumentParser(description="Verify diff between baseline ref and current code by running the report twice.")
    ap.add_argument("--ged", required=True, help="Path to GED file")
    ap.add_argument("--root", default="1", help="Root individual (e.g. 1 or @I1@)")
    ap.add_argument("--baseline", required=True, help="Git ref for baseline (e.g. v0.4.0 or a commit SHA)")
    ap.add_argument("--outdir", default=".", help="Directory to drop the two outputs and report")
    ap.add_argument("--allow-prefix", action="append", default=None,
                    help="Additional allowed line prefixes (can be given multiple times)")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    # Prepare temp worktree
    with tempfile.TemporaryDirectory(prefix="genreport_baseline_") as tmpdir:
        tmp = Path(tmpdir)
        wt = tmp / "baseline"
        # git worktree add --detach <wt> <ref>
        code, out, err = run(["git", "worktree", "add", "--detach", str(wt), args.baseline], cwd=repo_root)
        if code != 0:
            sys.stderr.write(err or out)
            sys.exit(f"Failed to create worktree for {args.baseline}")

        try:
            # Paths
            baseline_out = outdir / "persongalleri-baseline.md"
            current_out = outdir / "persongalleri-current.md"

            # Run baseline
            code, out, err = run([
                sys.executable, str(repo_root / "tools" / "_run_once.py"),
                "--src", str(wt),
                "--ged", str(Path(args.ged).resolve()),
                "--root", args.root,
                "--out", str(baseline_out),
            ], cwd=repo_root)
            if code != 0:
                sys.stderr.write(err or out)
                sys.exit("Baseline run failed")

            # Run current
            code, out, err = run([
                sys.executable, str(repo_root / "tools" / "_run_once.py"),
                "--src", str(repo_root),
                "--ged", str(Path(args.ged).resolve()),
                "--root", args.root,
                "--out", str(current_out),
            ], cwd=repo_root)
            if code != 0:
                sys.stderr.write(err or out)
                sys.exit("Current run failed")

            # Diff
            a_lines = read_text(baseline_out)
            b_lines = read_text(current_out)
            summary, ok, changed = summarize_diff(a_lines, b_lines)

            # Save full diff
            full_diff_path = outdir / "last_diff.txt"
            full = "\n".join(difflib.unified_diff(a_lines, b_lines, fromfile="baseline", tofile="current", lineterm=""))
            full_diff_path.write_text(full, encoding="utf-8")

            # Print result
            print(summary)
            print(f"\nFull diff written to: {full_diff_path}")

            # Exit code
            sys.exit(0 if ok else 1)
        finally:
            # Clean worktree (best-effort)
            run(["git", "worktree", "remove", "--force", str(wt)], cwd=repo_root)

if __name__ == "__main__":
    main()
