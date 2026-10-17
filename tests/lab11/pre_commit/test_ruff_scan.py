
import subprocess
import sys


def test_ruff_scan_passes():
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--output-format=concise", "."],
        capture_output=True,
        text=True,
    )

    returncode = result.returncode
    assert returncode == 0, result.stdout + result.stderr
