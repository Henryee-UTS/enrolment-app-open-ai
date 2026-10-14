import os

from flask import Blueprint, request
import requests


# Group the Multi-Agent routes into a Flask Blueprint.
multi_agent_bp = Blueprint("multi_agent_mode", __name__)

# Docker Compose will override this with the host address.
MULTI_AGENT_SERVICE_URL = os.getenv(
    "MULTI_AGENT_SERVICE_URL",
    "http://localhost:5004",
)

try:
    MULTI_AGENT_SERVICE_TIMEOUT_SECONDS = int(
        os.getenv("MULTI_AGENT_SERVICE_TIMEOUT_SECONDS", "60")
    )
except ValueError:
    MULTI_AGENT_SERVICE_TIMEOUT_SECONDS = 60


def multi_agent_mode_is_enabled(req) -> bool:
    """Check the service setting and the request's mode header."""
    enabled = os.getenv(
        "MULTI_AGENT_ENABLED", "true"
    ).strip().lower() in ("1", "true", "yes", "on")

    if not enabled:
        return False

    mode_header = req.headers.get(
        "X-Multi-Agent-Mode", "on"
    ).strip().lower()

    return mode_header in ("1", "true", "yes", "on")


def multi_agent_disabled_response():
    """Reject requests when the feature is disabled."""
    return {
        "status": "error",
        "error": "Multi-Agent mode is disabled.",
    }, 403


@multi_agent_bp.post("/multi-agent/workflow")
def multi_agent_workflow():
    """Forward a workflow request to the Multi-Agent server."""
    if not multi_agent_mode_is_enabled(request):
        return multi_agent_disabled_response()

    data = request.get_json(silent=True) or {}
    user_request = data.get("user_request", "").strip()

    if not user_request:
        return {
            "status": "error",
            "error": "user_request is required",
        }, 400

    try:
        response = requests.post(
            f"{MULTI_AGENT_SERVICE_URL}/workflow",
            json={"user_request": user_request},
            timeout=MULTI_AGENT_SERVICE_TIMEOUT_SECONDS,
        )

        # Preserve the downstream response body and HTTP status.
        return response.json(), response.status_code

    except requests.RequestException as exc:
        return {
            "status": "error",
            "error": str(exc),
        }, 503


@multi_agent_bp.get("/multi-agent/workflow/status")
def multi_agent_workflow_status():
    """Forward a history query without starting a new workflow."""
    if not multi_agent_mode_is_enabled(request):
        return multi_agent_disabled_response()

    try:
        response = requests.get(
            f"{MULTI_AGENT_SERVICE_URL}/workflow/status",
            timeout=MULTI_AGENT_SERVICE_TIMEOUT_SECONDS,
        )
        return response.json(), response.status_code

    except requests.RequestException as exc:
        return {
            "status": "error",
            "error": str(exc),
        }, 503