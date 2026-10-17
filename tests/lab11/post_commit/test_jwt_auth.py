
"""Lab 11: JWT authentication tests."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from flask import Flask


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SERVICE_DIR = PROJECT_ROOT / "enrolment-service"

sys.path.insert(0, str(SERVICE_DIR))

from routes.auth import auth_bp  # noqa: E402

TEST_SECRET = "lab11-test-secret-not-for-production-2026"  # noqa: S105  # pragma: allowlist secret

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(auth_bp)

    return app.test_client()


def test_valid_jwt(client):
    token = jwt.encode(
        {
            "sub": "student-1",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    response = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.get_json()["status"] == "valid"
    assert response.get_json()["subject"] == "student-1"


def test_expired_jwt(client):
    token = jwt.encode(
        {
            "sub": "student-1",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    response = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "Token expired"


def test_invalid_signature(client):
    token = jwt.encode(
        {
            "sub": "student-1",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "different-test-secret-not-for-production",
        algorithm="HS256",
    )

    response = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "Invalid token"
