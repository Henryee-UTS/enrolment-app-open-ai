# Lab 7 Boundary Analysis — 2026-10-13

The standalone MCP server reads root enrolment.db. Docker's database service uses its own named-volume SQLite database. Both currently return 10 students and the same ASD101 students; future changes need not stay synchronized.

MCP tools are read-only but project_files and ci_report currently accept unrestricted relative/absolute paths. This lab server is local and should not be treated as a multi-user authorized filesystem gateway.

The HTTP MCP-labelled UI is a helper API demonstration, not an MCP client. Its success does not prove a stdio protocol round trip. Server startup diagnostics were moved to stderr after the real client reported a JSON-RPC parsing error from a stdout banner.
