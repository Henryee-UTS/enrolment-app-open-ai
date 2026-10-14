# Read configuration values from environment variables.
import os

# Connect to and query a SQLite database.
import sqlite3

# Build file paths relative to this Python file.
from pathlib import Path

# Type hints describe the expected inputs and outputs.
# They help readers and editors, but do not validate data automatically.
from typing import Any, Dict, List

# Use the OpenAI-compatible client to communicate with local Ollama.
from openai import OpenAI


# __file__ refers to this worker_agent.py file.
# parents[1] points to the multi-agent-server directory.
BASE_DIR = Path(__file__).resolve().parents[1]

# The parent of multi-agent-server is the project root.
APP_DIR = BASE_DIR.parent

# Location of the Worker's instructions.
PROMPT_PATH = BASE_DIR / "prompts" / "worker_prompt.txt"

# Use the SQLite database in the project root.
# This is separate from the database inside the Docker volume.
DATABASE_PATH = APP_DIR / "enrolment.db"


# Read the Ollama URL from the environment.
# If it is not set, use the local Ollama server.
OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL", "http://localhost:11434/v1"
)

# Select the model used to generate the summary.
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

# Environment variables are strings, so convert the timeout to a number.
OLLAMA_TIMEOUT_SECONDS = float(
    os.getenv("OLLAMA_TIMEOUT_SECONDS", "45")
)

# FAST_MODE controls the default response token budget.
# It does not switch models or guarantee faster execution.
FAST_MODE = os.getenv("FAST_MODE", "true").lower() == "true"

# Use 180 tokens in fast mode, otherwise 400.
# An explicit WORKER_MAX_TOKENS environment variable overrides this.
# Tokens are pieces of text, not the same as words.
WORKER_MAX_TOKENS = int(
    os.getenv("WORKER_MAX_TOKENS", "180" if FAST_MODE else "400")
)

# Create the model client.
# The URL points to Ollama; "ollama" is a placeholder API key.
# This Lab example does not explicitly disable automatic retries.
client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",
    timeout=OLLAMA_TIMEOUT_SECONDS,
)


def load_prompt() -> str:
    """Read the Worker instructions from the prompt file."""

    # UTF-8 supports standard text characters.
    # strip() removes whitespace from the beginning and end.
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def extract_subject_code(user_request: str) -> str:
    """Find an ASD subject code in the user's request."""

    # Convert to uppercase so "asd101" can match "ASD101".
    request_upper = user_request.upper()

    # Replace periods and commas with spaces, then split into words.
    # Example: "Summarize ASD101." becomes ["SUMMARIZE", "ASD101"].
    for token in request_upper.replace(".", " ").replace(",", " ").split():

        # Return the first word beginning with ASD.
        # This is a simple extraction rule, not full code validation.
        if token.startswith("ASD"):
            return token

    # Lab example default when no matching word is found.
    # This assumes ASD101 even if the user did not specify a subject.
    return "ASD101"


def _connect_db() -> sqlite3.Connection:
    """Open the existing local database."""

    # Avoid accidentally creating a new empty database
    # when the expected database file is missing.
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DATABASE_PATH}")

    # Open a regular SQLite connection.
    # The queries below only read data; this connection itself
    # is not explicitly restricted to read-only mode.
    conn = sqlite3.connect(DATABASE_PATH)

    # Allow column access by name, such as row["student_name"],
    # instead of only by position, such as row[1].
    conn.row_factory = sqlite3.Row

    return conn


def get_students_by_subject(subject_code: str) -> List[Dict[str, Any]]:
    """Retrieve database records for the requested subject."""

    conn = _connect_db()

    try:
        # A cursor executes SQL and retrieves its results.
        cursor = conn.cursor()

        # Select only the three fields needed for this task.
        # The ? is a parameter placeholder.
        # Pass subject_code separately instead of inserting it into SQL text.
        cursor.execute(
            """
            SELECT student_id, student_name, subject_code
            FROM students
            WHERE subject_code = ?
            ORDER BY student_id
            """,
            (subject_code,),
        )

        # fetchall() collects all matching rows.
        # Convert each SQLite Row into a normal Python dictionary.
        #
        # Example:
        # {"student_id": 1, "student_name": "John Smith",
        #  "subject_code": "ASD101"}
        return [dict(row) for row in cursor.fetchall()]

    finally:
        # Always close the connection, including when a query fails.
        conn.close()


def format_evidence(
    students: List[Dict[str, Any]],
    subject_code: str,
) -> str:
    """Convert database records into readable text for the model."""

    # An empty result is different from a database connection failure.
    if not students:
        return f"No students found for {subject_code}."

    lines = []

    # Create one line of evidence for each student.
    for student in students:
        lines.append(
            f"- {student['student_id']} | "
            f"{student['student_name']} | "
            f"{student['subject_code']}"
        )

    # Join the lines with newline characters.
    # Example:
    # - 1 | John Smith | ASD101
    # - 2 | Sarah Jones | ASD101
    return "\n".join(lines)


def call_model(
    user_request: str,
    subject_code: str,
    evidence_text: str,
) -> str:
    """Ask Qwen to generate an answer using the supplied evidence."""

    # Combine the saved instructions, task, subject, and database evidence.
    # Python retrieves the records; the model receives their text.
    #
    # Lab example limitation:
    # The saved prompt says 100 words, while this addition says 180.
    # These limits should be made consistent during improvement.
    prompt = f"""
{load_prompt()}

Constraints:
- Use only the provided Student Evidence.
- Do not invent students or fields.
- Return concise output under 180 words.

User Request:

{user_request}

Subject Code:

{subject_code}

Student Evidence:

{evidence_text}
"""

    try:
        # Send the prompt to the selected local model.
        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],

            # A low temperature reduces randomness.
            # It does not guarantee a correct answer.
            temperature=0.1,

            # Limit the number of tokens generated.
            max_tokens=WORKER_MAX_TOKENS,
        )

        # Read the text from the first returned response.
        # This extracts text; it does not verify factual accuracy
        # or check whether generation stopped at the token limit.
        return response.choices[0].message.content.strip()

    except Exception as exc:
        # If the model call fails, return a fallback message.
        # The database evidence is retained for human inspection.
        #
        # Important: this is Python-generated failure text,
        # not a successful answer from the model.
        return (
            "Output:\n"
            "Model output could not be generated.\n\n"
            "Evidence Used:\n"
            f"{evidence_text}\n\n"
            "Limitations:\n"
            f"Model call failed. Human review required. Error: {exc}"
        )


def generate_output(user_request: str) -> Dict[str, Any]:
    """Run the Worker process and package its result."""

    # Step 1: Determine which subject to query.
    subject_code = extract_subject_code(user_request)

    try:
        # Step 2: Retrieve real records from SQLite.
        students = get_students_by_subject(subject_code)

        # Step 3: Convert the records into text for the model.
        evidence_text = format_evidence(students, subject_code)

        # Step 4: Ask the model to produce an evidence-based response.
        output = call_model(user_request, subject_code, evidence_text)

        # Step 5: Return the source records alongside the response.
        # This allows the Reviewer to compare claims with evidence.
        #
        # Lab example limitation:
        # call_model() returns fallback text on model failure.
        # Therefore, this status can still be "success"
        # even when the model did not generate an answer.
        return {
            "status": "success",
            "agent": "worker_agent",
            "model": OLLAMA_MODEL,
            "subject_code": subject_code,

            # Count records in Python, rather than asking the model to count.
            "evidence_count": len(students),

            # Preserve the actual database records.
            "evidence": students,

            # Contains either model output or the failure fallback.
            "output": output,

            # This declares that approval is required.
            # It does not mean a human has already approved the result.
            "human_approval_required": True,
        }

    except (FileNotFoundError, sqlite3.Error) as exc:
        # Report a missing file or SQLite failure.
        # This handler is limited to these exception types.
        return {
            "status": "error",
            "agent": "worker_agent",
            "subject_code": subject_code,
            "evidence_count": 0,
            "evidence": [],
            "output": "Database evidence could not be retrieved.",
            "error": str(exc),
            "human_approval_required": True,
        }


# Run this demonstration only when this file is executed directly.
# Importing generate_output from another file will not run this block.
if __name__ == "__main__":
    import json

    # Use a fixed example request for the standalone Worker test.
    result = generate_output(
        "Generate a student enrolment summary for ASD101."
    )

    # Convert the result dictionary to readable JSON.
    # indent=2 adds indentation for easier reading.
    print(json.dumps(result, indent=2))