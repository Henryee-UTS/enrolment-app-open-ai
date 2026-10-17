
"""Lab 11: Post-commit API endpoint tests."""

import os

import pytest
import requests


BASE_URL = os.getenv(
    "ENROLMENT_SERVICE_URL",
    "http://localhost:5001",
)


@pytest.mark.parametrize(
    "endpoint,params",
    [
        ("/", None),
        ("/students", None),
        ("/students/by-id", {"student_id": "1"}),
        ("/students/by-subject", {"subject_code": "ASD101"}),
    ],
)
def test_valid_api_endpoints(endpoint, params):
    response = requests.get(
        f"{BASE_URL}{endpoint}",
        params=params,
        timeout=10,
    )

    assert response.status_code == 200


def test_missing_student_id():
    response = requests.get(
        f"{BASE_URL}/students/by-id",
        timeout=10,
    )

    assert response.status_code == 400


def test_missing_subject_code():
    response = requests.get(
        f"{BASE_URL}/students/by-subject",
        timeout=10,
    )

    assert response.status_code == 400
