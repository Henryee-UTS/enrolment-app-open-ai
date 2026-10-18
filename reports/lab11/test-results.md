# Lab 11 Post-Commit Test Results

Date: 2026-10-18T10:03:42.236285+00:00

Status: PASS

```text
============================= test session starts ==============================
platform darwin -- Python 3.14.7, pytest-9.1.1, pluggy-1.7.0 -- /Users/ashley/Desktop/enrolment-app-open-ai-1/.venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/ashley/Desktop/enrolment-app-open-ai-1
configfile: pyproject.toml
plugins: platformdirs-4.13.0, anyio-4.14.2
collecting ... collected 9 items

tests/lab11/post_commit/test_api_endpoints.py::test_valid_api_endpoints[/-None] PASSED [ 11%]
tests/lab11/post_commit/test_api_endpoints.py::test_valid_api_endpoints[/students-None] PASSED [ 22%]
tests/lab11/post_commit/test_api_endpoints.py::test_valid_api_endpoints[/students/by-id-params2] PASSED [ 33%]
tests/lab11/post_commit/test_api_endpoints.py::test_valid_api_endpoints[/students/by-subject-params3] PASSED [ 44%]
tests/lab11/post_commit/test_api_endpoints.py::test_missing_student_id PASSED [ 55%]
tests/lab11/post_commit/test_api_endpoints.py::test_missing_subject_code PASSED [ 66%]
tests/lab11/post_commit/test_jwt_auth.py::test_valid_jwt PASSED          [ 77%]
tests/lab11/post_commit/test_jwt_auth.py::test_expired_jwt PASSED        [ 88%]
tests/lab11/post_commit/test_jwt_auth.py::test_invalid_signature PASSED  [100%]

============================== 9 passed in 0.57s ===============================

```
