
import json
import subprocess
import sys
from pathlib import Path


BASELINE_PATH = Path(__file__).resolve().parents[3] / ".secrets.baseline"


def test_detect_secrets_scan_passes():
    # Load previously audited false positives
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    reviewed = set()

    for filename, findings in baseline.get("results", {}).items():
        for finding in findings:
            assert finding.get("is_secret") is False, (
                f"Unreviewed baseline finding in {filename}"
            )
            reviewed.add((
                filename,
                finding["type"],
                finding["hashed_secret"],
            ))

    # Run a fresh secret scan
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "detect_secrets",
            "scan",
            "--exclude-files",
            r"(^|/)\.secrets\.baseline$|legacy-lab3/.*",
            
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    scan_results = json.loads(result.stdout)

    # Fail if a secret is not in the audited baseline
    new_findings = []

    for filename, findings in scan_results.get("results", {}).items():
        for finding in findings:
            identity = (
                filename,
                finding["type"],
                finding["hashed_secret"],
            )

            if identity not in reviewed:
                new_findings.append((
                    filename,
                    finding.get("line_number"),
                    finding["type"],
                ))

    assert not new_findings, (
        f"New or unapproved potential secrets: {new_findings}"
    )
