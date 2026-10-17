
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[3]

REQUIREMENTS = [
    "requirements.txt",
    "database-service/requirements.txt",
    "enrolment-service/requirements.txt",
    "mcp-server/requirements.txt",
    "multi-agent-server/requirements.txt",
]


@pytest.mark.parametrize("requirements_file", REQUIREMENTS)
def test_project_dependencies(requirements_file):
    result = subprocess.run(  # noqa: S603 - fixed command and trusted requirements paths
        [
            sys.executable,
            "-m",
            "pip_audit",
            "-r",
            str(PROJECT_ROOT / requirements_file),
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    assert result.returncode == 0, (
        f"Security audit failed for {requirements_file}\n"
        f"{result.stdout}\n{result.stderr}"
    )
