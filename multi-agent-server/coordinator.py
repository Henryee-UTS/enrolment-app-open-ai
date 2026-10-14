import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from agents.planner_agent import plan_workflow
from agents.worker_agent import generate_output
from agents.reviewer_agent import review_output


BASE_DIR = Path(__file__).resolve().parent
HISTORY_PATH = BASE_DIR / "workflow_history.jsonl"
AUDIT_PATH = BASE_DIR / "coordination_audit.jsonl"

# Maximum wait for each future.result() call.
# This is separate from the model client's request timeout.
AGENT_STEP_TIMEOUT_SECONDS = float(
    os.getenv("AGENT_STEP_TIMEOUT_SECONDS", "30")
)


def now_iso() -> str:
    """Return a timestamp with an explicit UTC timezone."""
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    """Append one JSON object as one line without removing old records."""
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")


def read_jsonl(path: Path) -> list[Dict[str, Any]]:
    """Read saved records, or return an empty list if no file exists."""
    if not path.exists():
        return []

    records = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    return records


def run_workflow(user_request: str) -> Dict[str, Any]:
    """Run the agents and save the combined result."""
    start_time = time.time()

    # Give this workflow a unique identifier for tracing its records.
    workflow_id = str(uuid.uuid4())

    # Lab behavior: Planner and Worker start concurrently.
    # The Worker does not receive the generated Planner plan.
    executor = ThreadPoolExecutor(max_workers=2)
    planner_future = executor.submit(plan_workflow, user_request)
    worker_future = executor.submit(generate_output, user_request)

    try:
        try:
            planner_result = planner_future.result(
                timeout=AGENT_STEP_TIMEOUT_SECONDS
            )
        except FutureTimeoutError:
            planner_future.cancel()
            planner_result = {
                "status": "timeout",
                "agent": "planner_agent",
                "plan": (
                    "Planner timed out. Continue with worker evidence "
                    "and human review."
                ),
                "human_approval_required": True,
            }

        try:
            worker_result = worker_future.result(
                timeout=AGENT_STEP_TIMEOUT_SECONDS
            )
        except FutureTimeoutError:
            worker_future.cancel()
            worker_result = {
                "status": "timeout",
                "agent": "worker_agent",
                "subject_code": "ASD101",
                "evidence_count": 0,
                "evidence": [],
                "output": "Worker timed out before generating output.",
                "human_approval_required": True,
            }
    finally:
        # This does not forcibly stop a thread already executing a model call.
        executor.shutdown(wait=False, cancel_futures=True)

    # Start the Reviewer after collecting the Worker result.
    reviewer_executor = ThreadPoolExecutor(max_workers=1)
    reviewer_future = reviewer_executor.submit(
        review_output,
        user_request,
        worker_result,
    )

    try:
        try:
            reviewer_result = reviewer_future.result(
                timeout=AGENT_STEP_TIMEOUT_SECONDS
            )
        except FutureTimeoutError:
            reviewer_future.cancel()
            reviewer_result = {
                "status": "timeout",
                "agent": "reviewer_agent",
                "review": (
                    "Reviewer timed out. Human must decide "
                    "based on available evidence."
                ),
                "human_approval_required": True,
            }
    finally:
        reviewer_executor.shutdown(wait=False, cancel_futures=True)

    duration_ms = int((time.time() - start_time) * 1000)

    # Preserve every agent's result for inspection.
    # Lab limitation: the outer status is always "success",
    # even when an individual agent returned an error or timeout.
    workflow_result = {
        "status": "success",
        "workflow_id": workflow_id,
        "timestamp": now_iso(),
        "duration_ms": duration_ms,
        "user_request": user_request,
        "participating_agents": [
            "planner_agent",
            "worker_agent",
            "reviewer_agent",
        ],
        "planner_result": planner_result,
        "worker_result": worker_result,
        "reviewer_result": reviewer_result,

        # No human decision is made automatically.
        "human_decision": {
            "required": True,
            "status": "pending",
            "allowed_values": [
                "Accept",
                "Partially Accept",
                "Reject",
            ],
        },
    }

    # Store a shorter audit record using the same workflow ID.
    audit_record = {
        "workflow_id": workflow_id,
        "timestamp": workflow_result["timestamp"],
        "duration_ms": duration_ms,
        "status": workflow_result["status"],
        "participating_agents": workflow_result["participating_agents"],
        "human_approval_required": True,
        "worker_status": worker_result.get("status"),
        "evidence_count": worker_result.get("evidence_count", 0),
    }

    append_jsonl(HISTORY_PATH, workflow_result)
    append_jsonl(AUDIT_PATH, audit_record)

    return workflow_result


def workflow_status() -> Dict[str, Any]:
    """Return saved record counts and the latest workflow."""
    history = read_jsonl(HISTORY_PATH)
    audit = read_jsonl(AUDIT_PATH)

    return {
        "status": "success",
        "workflow_history_count": len(history),
        "audit_record_count": len(audit),
        "latest_workflow": history[-1] if history else None,
    }


if __name__ == "__main__":
    result = run_workflow(
        "Generate a student enrolment summary for ASD101."
    )
    print(json.dumps(result, indent=2))