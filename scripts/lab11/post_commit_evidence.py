"""Run Lab 11 post-commit tests and generate release evidence."""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    reports = root / "reports" / "lab11"
    reports.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests/lab11/post_commit/",
        "-v",
    ]

    result = subprocess.run(  # noqa: S603 - fixed pytest command
        command,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout + result.stderr
    print(output)

    timestamp = datetime.now(timezone.utc).isoformat()
    status = "PASS" if result.returncode == 0 else "FAIL"

    (reports / "post_commit.log").write_text(output, encoding="utf-8")

    (reports / "test-results.md").write_text(
        "# Lab 11 Post-Commit Test Results\n\n"
        f"Date: {timestamp}\n\n"
        f"Status: {status}\n\n"
        "```text\n"
        + output
        + "\n```\n",
        encoding="utf-8",
    )

    with (reports / "test-audit.jsonl").open(
        "a", encoding="utf-8"
    ) as file:
        file.write(json.dumps({
            "timestamp": timestamp,
            "status": status,
            "exit_code": result.returncode,
            "source": "post_commit_tests",
        }) + "\n")

    print(f"Lab 11 test status: {status}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
