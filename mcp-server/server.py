import sys

from mcp.server import MCPServer

from tools import (
    get_student_count,
    get_students_by_subject,
    list_project_files,
    read_ci_report
)


mcp = MCPServer("Student Enrolment MCP")

AVAILABLE_TOOLS = [
    "student_count",
    "students_by_subject",
    "project_files",
    "ci_report",
]


@mcp.tool()
def student_count():
    return get_student_count()


@mcp.tool()
def students_by_subject(subject_code: str):
    return get_students_by_subject(subject_code)


@mcp.tool()
def project_files(directory_path: str = ".."):
    return list_project_files(directory_path)


@mcp.tool()
def ci_report(report_path: str = "../reports/report.json"):
    return read_ci_report(report_path)


if __name__ == "__main__":
    print("Starting Student Enrolment MCP Server...", file=sys.stderr)
    print("Server status: RUNNING", file=sys.stderr)
    print("Interact with MCP tools from a second terminal.", file=sys.stderr)
    print("Available tools:", file=sys.stderr)

    for tool in AVAILABLE_TOOLS:
        print(f"- {tool}", file=sys.stderr)

    mcp.run()