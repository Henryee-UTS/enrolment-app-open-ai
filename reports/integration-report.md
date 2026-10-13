# Lab 7 Integration Check — 2026-10-13

- Local MCP tool collector: passed all four function calls.
- Local SQLite count: 10; ASD101 records: John Smith and Sarah Jones.
- Docker frontend GET /: HTTP 200.
- Enrolment POST /mcp/student-count: returned 10.
- Enrolment POST /mcp/students-by-subject: returned both ASD101 students.
- Enrolment POST /mcp/ci-report: returned existing Lab 5 metadata (run 33055888704).
- This is existing CI evidence, not a newly triggered or independently verified GitHub run.
- HTTP MCP-labelled routes invoke Python/HTTP helpers directly; they do not use MCP transport.
- Actual MCP protocol checks are separately recorded in mcp-protocol-check.json.
