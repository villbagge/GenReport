# tools/verify_diff.py
from __future__ import annotations
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
import difflib
import shutil
import os

ALLOWED_PREFIXES_DEFAULT = ["SOUR."]

def resolve_git_exe() -> str:
    exe = shutil.which("git")
    if exe:
        return exe

    candidates = [
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\GitHubDesktop\app-*\resources\app\git\mingw64\bin\git.exe"),
    ]
    for c in candidates:
        if "*" in c:
            base = Path(c.split("\\app-")[0])
            if base.exists():
                for child in base.glob("GitHubDesktop\\app-*\\resources\\app\\git\\mingw64\\bin\\git.exe"):
                    return str(child)
        elif Path(c).exists():
            return c
    raise SystemExit("Could not find git.exe — please install Git for Windows or add it to PATH.")

def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    p = subprocess.Popen(
        cmd, cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    out, err = p.communicate()
    return p.returncode, out, err

def read_text(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").splitlines(keepends=False)

def latest_tag(git_exe: str, repo_root: Path) -> str:
    code, out, err = run([git_exe, "describe", "--tags", "--abbrev=0"], cwd=repo_root)
    if code != 0:
        sys.stderr.write(err or out or "")
        raise SystemExit("Failed to detect latest tag (do you have any tags?)")
    return out.strip()

def summarize_for_console(a_lines: list[str], b_lines: list[str], allowed_prefixes: list[str]) -> bool:
    """Return ok_flag only (no printed diff)."""
    diff = list(difflib.ndiff(a_lines, b_lines))
    changed_lines = []
    for line in diff:
        if line.startswith("?"):
            continue
        if line.startswith("- ") or line.startswith("+ "):
            changed_lines.append(line[2:])

    def allowed(line: str) -> bool:
        return (line.strip() == "") or any(line.startswith(pref) for pref in allowed_prefixes)

    ok = all(allowed(l) for l in changed_lines)
    return ok

def write_pretty_last_diff(a_lines: list[str], b_lines: list[str], dest: Path) -> None:
    sm = difflib.SequenceMatcher(a=a_lines, b=b_lines, autojunk=False)
    out_lines: list[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        elif tag == "delete":
            for i in range(i1, i2):
                out_lines.append(f"- {a_lines[i]}")
        elif tag == "insert":
            for j in range(j1, j2):
                out_lines.append(f"+ {b_lines[j]}")
        elif tag == "replace":
            len_old = i2 - i1
            len_new = j2 - j1
            n = min(len_old, len_new)
            for k in range(n):
                out_lines.append(f"≠ {a_lines[i1+k]} -> {b_lines[j1+k]}")
            if len_old > n:
                for i in range(i1 + n, i2):
                    out_lines.append(f"- {a_lines[i]}")
            if len_new > n:
                for j in range(j1 + n, j2):
                    out_lines.append(f"+ {b_lines[j]}")

    dest.write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")

def main() -> None:
    ap = argparse.ArgumentParser(description="Verify diff between baseline ref and current code by running the report twice.")
    ap.add_argument("--ged", required=True, help="Path to GED file")
    ap.add_argument("--root", default="1", help="Root individual (e.g. 1 or @I1@)")
    ap.add_argument("--baseline", default=None, help="Git ref for baseline (e.g. v0.4.0 or commit SHA). If omitted, latest tag is used.")
    ap.add_argument("--outdir", default=".", help="Directory for persongalleri-baseline/current outputs.")
    ap.add_argument("--allow-prefix", action="append", default=None, help="Extra allowed prefixes.")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    git_exe = resolve_git_exe()

    baseline_ref = args.baseline or latest_tag(git_exe, repo_root)
    print(f"[verify_diff] Using baseline: {baseline_ref}")

    with tempfile.TemporaryDirectory(prefix="genreport_baseline_") as tmpdir:
        tmp = Path(tmpdir)
        wt = tmp / "baseline"
        code, out, err = run([git_exe, "worktree", "add", "--detach", str(wt), baseline_ref], cwd=repo_root)
        if code != 0:
            sys.stderr.write(err or out)
            sys.exit(f"Failed to create worktree for {baseline_ref}")

        try:
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

            # Diff check
            a_lines = read_text(baseline_out)
            b_lines = read_text(current_out)

            allowed_prefixes = ALLOWED_PREFIXES_DEFAULT.copy()
            if args.allow_prefix:
                allowed_prefixes.extend(args.allow_prefix)

            ok = summarize_for_console(a_lines, b_lines, allowed_prefixes)

            last_diff_path = Path.cwd() / "last_diff.txt"
            write_pretty_last_diff(a_lines, b_lines, last_diff_path)

            if ok:
                print("✅ seems ok")
            else:
                print("❌ bad changes detected")

            print(f"Full diff written to: {last_diff_path}")
            os.startfile(last_diff_path)  # Opens in Notepad on Windows

            sys.exit(0 if ok else 1)

        finally:
            run([git_exe, "worktree", "remove", "--force", str(wt)], cwd=repo_root)

if __name__ == "__main__":
    main()
