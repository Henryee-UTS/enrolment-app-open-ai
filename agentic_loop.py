import os
import sqlite3
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import OpenAI


# ------------------------------------------------------------
# PATHS AND ENVIRONMENT
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
DATABASE_NAME = BASE_DIR / "enrolment.db"
PROMPT_DIR = BASE_DIR / "prompts"

load_dotenv(dotenv_path=ENV_PATH)


# ------------------------------------------------------------
# AGENTIC LOOP PLAN
# ------------------------------------------------------------

PLAN = {
    "goal": (
        "Validate Student Enrolment App behaviour using "
        "a local multi-agent workflow"
    ),
    "checks": [
        "/students",
        "/students/{student_id}",
        "/students/by-id",
        "/students/by-subject",
    ],
}


# ------------------------------------------------------------
# OLLAMA CONFIGURATION
# ------------------------------------------------------------

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434/v1",
)

IMPLEMENTATION_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:0.5b",
)

REVIEW_MODEL = os.getenv(
    "OLLAMA_REVIEW_MODEL",
    "llama3.1:8b",
)


# ------------------------------------------------------------
# PROMPT ASSET LOADER
# ------------------------------------------------------------

def load_prompt(filename):
    """
    Load a prompt asset from the prompts directory.
    """

    prompt_path = PROMPT_DIR / filename

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}"
        )

    return prompt_path.read_text(
        encoding="utf-8"
    ).strip()


# ------------------------------------------------------------
# DATABASE VALIDATION
# ------------------------------------------------------------

def validate_student(student):
    student_id, student_name, subject_code = student

    if not isinstance(student_id, int):
        return False, "student_id must be an integer"

    if not student_name:
        return False, "student_name is required"

    if not subject_code:
        return False, "subject_code is required"

    return True, "ok"


def observe_data_quality():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    students = cursor.execute(
        """
        SELECT
            student_id,
            student_name,
            subject_code
        FROM students
        """
    ).fetchall()

    conn.close()

    if len(students) != 10:
        return (
            False,
            f"Expected 10 students but found {len(students)}",
        )

    for student in students:
        ok, message = validate_student(student)

        if not ok:
            return False, message

    return True, "Data validation passed"


def observe_subject_search(subject_code):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    students = cursor.execute(
        """
        SELECT
            student_id,
            student_name,
            subject_code
        FROM students
        WHERE subject_code = ?
        """,
        (subject_code,),
    ).fetchall()

    conn.close()

    if not students:
        return (
            False,
            f"No students found for subject code {subject_code}",
        )

    for student in students:
        if student[2] != subject_code:
            return (
                False,
                f"Unexpected subject code found: {student[2]}",
            )

    return (
        True,
        f"Subject search validation passed for {subject_code}",
    )


# ------------------------------------------------------------
# LIVE ENDPOINT VALIDATION
# ------------------------------------------------------------

def observe_live_endpoints():
    results = []

    try:
        response = requests.get(
            "http://127.0.0.1:5000/students",
            timeout=5,
        )

        results.append(
            f"/students -> HTTP {response.status_code}"
        )

    except Exception as exc:
        results.append(
            f"/students -> error: {exc}"
        )

    try:
        response = requests.get(
            (
                "http://127.0.0.1:5000/"
                "students/by-subject"
                "?subject_code=ASD101"
            ),
            timeout=5,
        )

        results.append(
            "/students/by-subject -> "
            f"HTTP {response.status_code}"
        )

    except Exception as exc:
        results.append(
            f"/students/by-subject -> error: {exc}"
        )

    return results


# ------------------------------------------------------------
# LOCAL MODEL CALL
# ------------------------------------------------------------

def call_model(
    model_name,
    system_prompt,
    user_prompt,
    max_tokens=120,
):
    try:
        client = OpenAI(
            base_url=OLLAMA_BASE_URL,
            api_key="ollama",
            timeout=180.0,
        )

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            max_tokens=max_tokens,
            temperature=0.1,
        )

        content = response.choices[0].message.content

        if content and content.strip():
            return content.strip(), None

        return "No response generated.", None

    except Exception as exc:
        return (
            None,
            f"{model_name} unavailable or timed out ({exc})",
        )


# ------------------------------------------------------------
# IMPLEMENTATION AGENT
# ------------------------------------------------------------

def get_implementation_agent_advice(observe_message):
    try:
        system_prompt = load_prompt(
            "implementation_system_prompt.txt"
        )

        task_prompt = load_prompt(
            "implementation_task_prompt.txt"
        )

        # Runtime Prompt Assembly:
        # Replace the placeholder with real validation evidence.
        task_prompt = task_prompt.replace(
            "{{VALIDATION_EVIDENCE}}",
            observe_message,
        )

        return call_model(
            IMPLEMENTATION_MODEL,
            system_prompt,
            task_prompt,
            max_tokens=120,
        )

    except Exception as exc:
        return (
            None,
            f"Implementation prompt loading failed ({exc})",
        )


# ------------------------------------------------------------
# REVIEW AGENT
# ------------------------------------------------------------

def get_review_agent_advice(
    implementation_message,
    observe_message,
):
    try:
        system_prompt = load_prompt(
            "review_system_prompt.txt"
        )

        task_prompt = load_prompt(
            "review_task_prompt.txt"
        )

        # Insert the Implementation Agent recommendation.
        task_prompt = task_prompt.replace(
            "{{IMPLEMENTATION_RECOMMENDATION}}",
            implementation_message,
        )

        # Insert the original validation evidence.
        task_prompt = task_prompt.replace(
            "{{VALIDATION_EVIDENCE}}",
            observe_message,
        )

        return call_model(
            REVIEW_MODEL,
            system_prompt,
            task_prompt,
            max_tokens=120,
        )

    except Exception as exc:
        return (
            None,
            f"Review prompt loading failed ({exc})",
        )


# ------------------------------------------------------------
# HUMAN REVIEW
# ------------------------------------------------------------

def human_review():
    print()
    print("HUMAN REVIEW")
    print("1 - Accept")
    print("2 - Partially Accept")
    print("3 - Reject")

    decision = input("Decision: ").strip()

    if decision == "1":
        return "Accept"

    if decision == "2":
        return "Partially Accept"

    return "Reject"


def adapt(decision):
    print()

    if decision == "Accept":
        print(
            "ADAPT: Accept the recommendation and "
            "record the supporting evidence."
        )

    elif decision == "Partially Accept":
        print(
            "ADAPT: Refine the relevant prompt asset, "
            "rerun validation, and compare the results."
        )

    else:
        print(
            "ADAPT: Reject the recommendation, document "
            "the rationale, and refine the prompt if required."
        )


# ------------------------------------------------------------
# MAIN AGENTIC LOOP
# ------------------------------------------------------------

def main():
    print("=" * 60)
    print("ASD LAB 03 AGENTIC LOOP")
    print("=" * 60)

    print()
    print("PLAN")
    print(PLAN)

    print()
    print("ACT")
    print("Check local database records and live endpoints")

    # Database validation
    ok_data, message_data = observe_data_quality()

    print()
    print("OBSERVE: Database Check")
    print(message_data)

    # Subject-code search validation
    ok_subject, message_subject = observe_subject_search(
        "ASD101"
    )

    print()
    print("OBSERVE: Subject Search Check")
    print(message_subject)

    # Live endpoint validation
    live_results = observe_live_endpoints()

    print()
    print("OBSERVE: Live Endpoint Check")

    for result in live_results:
        print(result)

    # Assemble objective validation evidence.
    observe_message = (
        f"Database Check: {message_data}\n"
        f"Subject Search Check: {message_subject}\n"
        f"Live Endpoint Checks:\n"
        + "\n".join(live_results)
    )

    # Implementation Agent
    print()
    print("IMPLEMENTATION AGENT")
    print(f"Model: {IMPLEMENTATION_MODEL}")

    implementation_advice, implementation_error = (
        get_implementation_agent_advice(
            observe_message
        )
    )

    if implementation_advice:
        print()
        print(implementation_advice)

    else:
        print()
        print(implementation_error)

        implementation_advice = (
            "Implementation Agent was unavailable. "
            "No valid implementation recommendation "
            "was generated."
        )

    # Review Agent
    print()
    print("REVIEW AGENT")
    print(f"Model: {REVIEW_MODEL}")

    review_advice, review_error = (
        get_review_agent_advice(
            implementation_advice,
            observe_message,
        )
    )

    if review_advice:
        print()
        print(review_advice)

    else:
        print()
        print(review_error)

    # Human approval
    print()
    print("HUMAN DECISION")

    decision = human_review()

    print()
    print(f"Decision: {decision}")

    adapt(decision)

    print()
    print("LOOP COMPLETE")


if __name__ == "__main__":
    main()