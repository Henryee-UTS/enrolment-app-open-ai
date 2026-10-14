import os

from flask import Flask, jsonify, request
from flask_cors import CORS

from coordinator import run_workflow, workflow_status


# Create the Flask application.
app = Flask(__name__)

# Enable cross-origin browser requests for this lab application.
# CORS is not authentication or access control.
CORS(app)


@app.get("/")
def health():
    """Check whether this API can respond."""
    return jsonify(
        {
            "service": "multi-agent-server",
            "status": "running",
        }
    )


@app.post("/workflow")
def workflow():
    """Read a task, execute the workflow, and return its result."""

    # Read the incoming JSON body.
    # If JSON parsing fails, use an empty dictionary.
    data = request.get_json(silent=True) or {}

    # The client must provide a non-empty user_request string.
    # This follows the lab's basic validation;
    # other JSON shapes and field types are not fully validated.
    user_request = data.get("user_request", "").strip()

    if not user_request:
        return jsonify(
            {
                "status": "error",
                "error": "user_request is required",
            }
        ), 400

    # This call waits for the Coordinator to return.
    # It also writes workflow and audit records.
    result = run_workflow(user_request)

    # HTTP 200 does not prove every agent succeeded
    # or that the generated answer is correct.
    return jsonify(result), 200


@app.get("/workflow/status")
def status():
    """Read saved workflow history without starting a new workflow."""
    return jsonify(workflow_status()), 200


if __name__ == "__main__":
    # Start the local development server.
    # 0.0.0.0 allows connections through available network interfaces.
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5004")),
        debug=True,
    )