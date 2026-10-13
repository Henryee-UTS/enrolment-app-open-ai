# Lab 7 Tool Review — 2026-10-13

- student_count: returns local SQLite aggregate.
- students_by_subject: normalizes subject and uses a parameterized SQL query.
- project_files: lists names; does not restrict paths to the project root.
- ci_report: reads existing JSON evidence; metadata alone does not prove a new CI pass.

The collector invokes tool functions, but does not validate every returned error payload or start an MCP client. Actual protocol checks must be interpreted separately. LLM assessment is saved in run-report.md and is commentary, not executable proof.
