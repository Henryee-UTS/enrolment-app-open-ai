import json
import os
from pathlib import Path

from openai import OpenAI

# 1. 프롬프트 파일의 위치를 찾습니다.
BASE_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = BASE_DIR / "prompts" / "planner_prompt.txt"

# 2. 사용할 Ollama 주소와 모델을 설정합니다.
OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434/v1",
)
OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:0.5b",
)

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama",
    timeout=60,
    max_retries=0,
    )

# 3. 작성해 둔 업무 설명서를 읽습니다.
def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


# 4. 프로그램이 사용할 기본 역할 순서입니다.
def default_steps() -> list[dict]:
    return [
        {
            "step": 1,
            "agent": "planner_agent",
            "action": "Create workflow plan",
        },
        {
            "step": 2,
            "agent": "worker_agent",
            "action": "Retrieve student evidence and generate output",
        },
        {
            "step": 3,
            "agent": "reviewer_agent",
            "action": "Review output against evidence",
        },
        {
            "step": 4,
            "agent": "human_reviewer",
            "action": "Accept, partially accept, or reject",
        },
    ]

# 5. 업무 설명서와 사용자 요청을 모델에 전달합니다.
def call_model(user_request: str) -> str:
    response = client.chat.completions.create(
        model=OLLAMA_MODEL,
        messages=[
            {
                "role": "system",
                "content": load_prompt(),
            },
            {
                "role": "user",
                "content": user_request,
            },
        ],
        temperature=0.1,
        max_tokens=200,
    )

    choice = response.choices[0]
    plan = (choice.message.content or "").strip()

    if not plan:
        raise ValueError("Planner returned an empty response.")

    if choice.finish_reason == "length":
        raise ValueError("Planner response reached the token limit.")

    return plan

# 6. 결과를 정해진 형식으로 포장합니다.
def plan_workflow(user_request: str) -> dict:
    result = {
        "agent": "planner_agent",
        "model": OLLAMA_MODEL,
        "objective": user_request,
        "human_approval_required": True,
    }

    try:
        if not user_request.strip():
            raise ValueError("User request must not be empty.")

        plan = call_model(user_request)

        return {
            **result,
            "status": "success",
            "plan": plan,
            "steps": default_steps(),
        }

    except Exception as exc:
        return {
            **result,
            "status": "error",
            "error": str(exc),
            "plan": None,
            "steps": [],
        }


# 7. 이 파일을 직접 실행했을 때 사용할 연습 요청입니다.
if __name__ == "__main__":
    print("Requesting a plan from local Ollama...", flush=True)

    result = plan_workflow(
        "Generate a student enrolment summary for ASD101."
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result["status"] != "success":
        raise SystemExit(1)