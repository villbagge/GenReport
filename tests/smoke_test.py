import subprocess, sys

def test_cli_runs():
    """Smoke: programmet startar utan krasch och säger något med 'genreport'."""
    r = subprocess.run([sys.executable, "-m", "genreport"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "genreport" in (r.stdout + r.stderr).lower()
