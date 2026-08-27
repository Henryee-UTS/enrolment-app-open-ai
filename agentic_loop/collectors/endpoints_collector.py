import os
import re
from pathlib import Path

import requests


ROUTE_PATTERN = re.compile(r"@\w+_bp\.(get|post)\(\"([^\"]+)\"\)")


def _test_endpoint(base_url: str, method: str, path: str) -> str:
    url = f"{base_url}{path}"

    try:
        if method.upper() == "GET":
            if path == "/students/by-id":
                response = requests.get(
                    url,
                    params={"student_id": "1"},
                    timeout=5,
                )
            elif path == "/students/by-subject":
                response = requests.get(
                    url,
                    params={"subject_code": "ASD101"},
                    timeout=5,
                )
            else:
                response = requests.get(url, timeout=5)

        elif method.upper() == "POST":
            if path in {"/architecture-review", "/pattern-selection", "/adr-review"}:
                response = requests.post(
                    url,
                    data={
                        "architecture_request":
                            "Review the three-service Student Enrolment architecture."
                    },
                    timeout=30,
                )
            else:
                response = requests.post(
                    url,
                    data={"question": "Explain the Student Enrolment App briefly."},
                    timeout=30,
                )

        else:
            return f"{method.upper()} {path} [UNSUPPORTED METHOD]"

        elapsed_ms = int(response.elapsed.total_seconds() * 1000)
        return f"{method.upper()} {path} returned {response.status_code} in {elapsed_ms}ms"

    except requests.exceptions.ConnectionError:
        return f"{method.upper()} {path} [CONNECTION REFUSED - app not running]"
    except requests.exceptions.Timeout:
        return f"{method.upper()} {path} [TIMEOUT]"
    except Exception as exc:
        return f"{method.upper()} {path} [ERROR: {type(exc).__name__}]"


def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
    flask_base_url = os.getenv("FLASK_BASE_URL", "http://localhost:5001")

    route_files = [
        app_dir / "enrolment-service" / "routes" / "normal_ui.py",
        app_dir / "enrolment-service" / "routes" / "ai_mode.py",
    ]

    missing = [str(path.relative_to(app_dir)) for path in route_files if not path.exists()]
    if missing:
        return False, "Missing route files: " + ", ".join(missing)

    endpoints: list[tuple[str, str]] = []

    for route_file in route_files:
        content = route_file.read_text(encoding="utf-8")
        for method, route in ROUTE_PATTERN.findall(content):
            endpoints.append((method, route))

    if not endpoints:
        return False, "No Flask routes found in route files."

    evidence_parts = []
    connection_failures = 0

    for method, route in sorted(set(endpoints)):
        result = _test_endpoint(flask_base_url, method, route)
        evidence_parts.append(result)

        if "CONNECTION REFUSED" in result:
            connection_failures += 1

    evidence = "Live endpoint evidence: " + "; ".join(evidence_parts) + "."

    if connection_failures == len(endpoints):
        return False, "Flask app not running. Start the app first, then run the agentic loop."

    return True, evidence
