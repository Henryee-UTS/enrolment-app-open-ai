import json
from pathlib import Path


def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
    post_commit_dir = app_dir / "tests" / "lab11" / "post_commit"
    reports_dir = app_dir / "reports" / "lab11"

    required_paths = [
        post_commit_dir / "test_api_endpoints.py",
        post_commit_dir / "test_jwt_auth.py",
        reports_dir / "test-results.md",
        reports_dir / "test-audit.jsonl",
    ]

    missing = [
        str(path.relative_to(app_dir))
        for path in required_paths
        if not path.exists()
    ]

    if missing:
        return False, "CI/CD test evidence incomplete. Missing: " + ", ".join(missing)

    audit_lines = (
        (reports_dir / "test-audit.jsonl")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()
    )

    if not audit_lines:
        return False, "reports/lab11/test-audit.jsonl is empty. Run the post-commit tests first."

    try:
        latest_entry = json.loads(audit_lines[-1])
        latest_status = latest_entry.get("status", "UNKNOWN")
    except (json.JSONDecodeError, AttributeError):
        return False, "Latest test audit entry is not valid JSON."

    if latest_status not in ("PASS", "FAIL"):
        return False, "Latest test audit entry has an invalid status."

    return True, (
        "CI/CD test evidence: tests/lab11/post_commit/ contains API and JWT "
        "authentication tests; reports/lab11/test-results.md and test-audit.jsonl "
        f"exist (latest audit entry status: {latest_status})."
    )
