import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from collectors import (
    architecture_collector,
    cicd_test_collector,
    deployment_collector,
    pre_test_collector,
    db_collector,
    devops_collector,
    endpoints_collector,
    mcp_collector,
    rag_collector,
)

from config.review_config import ModeConfig
from core.ai_runner import AIRunner
from core.prompt_registry import PromptRegistry

from pipelines import (
    architecture_pipeline,
    cicd_test_pipeline,
    deployment_pipeline,
    pre_test_pipeline,
    db_pipeline,
    devops_pipeline,
    endpoints_pipeline,
    mcp_pipeline,
    rag_pipeline,
)


COLLECTORS = {
    "db": db_collector.collect,
    "endpoints": endpoints_collector.collect,
    "architecture": architecture_collector.collect,
    "devops": devops_collector.collect,
    "mcp": mcp_collector.collect,
    "rag": rag_collector.collect,
    "pre_test": pre_test_collector.collect,
    "cicd_test": cicd_test_collector.collect,
    "deployment": deployment_collector.collect,
}


def _stage(mode_label: str, step: str, message: str) -> None:
    print(f"[{mode_label}][{step}] {message}")


def run_mode(
    mode: ModeConfig,
    app_dir: Path,
    repo_root: Path,
    prompts: PromptRegistry,
    ai: AIRunner,
) -> str:

    _stage(mode.label, "START", "Starting review flow")

    # LAB 10 - MULTI-AGENT WORKFLOW
    if mode.key == "multi_agent":
        _stage(mode.label, "API", "Starting Multi-Agent workflow")

        sample_request = "Generate a student enrolment summary for ASD101."
        user_request = input(
            f"Enter workflow request [{sample_request}]: "
        ).strip() or sample_request

        
        service_url = os.getenv(
            "MULTI_AGENT_WORKFLOW_URL",
            "http://127.0.0.1:5004/workflow",
        )

        parsed_url = urlsplit(service_url)

        if parsed_url.scheme not in ("http", "https") or not parsed_url.hostname:
            return "MULTI-AGENT FAILED: Only valid HTTP/HTTPS URLs are allowed."

        request = Request( # noqa: S310 - HTTP/HTTPS scheme validated above
            service_url,  
            data=json.dumps({
                "user_request": user_request
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=180) as response:  # noqa: S310 - URL scheme validated
                result = json.load(response)

        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            _stage(mode.label, "API", "Workflow request failed")
            return f"MULTI-AGENT FAILED: {exc}"

        _stage(mode.label, "DONE", "Workflow response received")
        return json.dumps(result, indent=2)


    _stage(mode.label, "OBSERVE", "Collecting evidence")

    collector = COLLECTORS[mode.key]
    ok, evidence = collector(app_dir, repo_root)

    if not ok:
        _stage(mode.label, "OBSERVE", "Failed")
        return f"OBSERVE FAILED: {evidence}"

    _stage(mode.label, "OBSERVE", "Complete")

    # -------------------------------------------------
    # DB + ENDPOINTS
    # -------------------------------------------------

    if mode.key in {"db", "endpoints"}:

        _stage(
            mode.label,
            "PROMPTS",
            f"Loading prompt family: {mode.prompt_family}",
        )

        system_prompt = prompts.read(
            mode.prompt_family,
            mode.implementation_prompts[0],
        )

        task_prompt = prompts.read(
            mode.prompt_family,
            mode.implementation_prompts[1],
        )

        context_prompt = prompts.read(
            mode.prompt_family,
            mode.implementation_prompts[2],
        )

        _stage(
            mode.label,
            "PROMPTS",
            "Loaded implementation prompt set",
        )

        if mode.key == "db":
            user_prompt = db_pipeline.build_user_prompt(
                task_prompt,
                context_prompt,
                evidence,
            )
        else:
            user_prompt = endpoints_pipeline.build_user_prompt(
                task_prompt,
                context_prompt,
                evidence,
            )

        _stage(
            mode.label,
            "LLM",
            "Running implementation model",
        )

        output, err = ai.call(
            system_prompt,
            user_prompt,
            review=False,
        )

        if err:
            _stage(mode.label, "LLM", "Failed")
            return f"MODEL FAILED: {err}"

        _stage(mode.label, "LLM", "Complete")
        _stage(mode.label, "DONE", "Review complete")

        return (
            f"OBSERVE: {evidence}\n\n"
            f"REVIEW: {output}"
        )

    # -------------------------------------------------
    # ARCHITECTURE
    # -------------------------------------------------

    if mode.key == "architecture":

        _stage(
            mode.label,
            "PROMPTS",
            f"Loading prompt family: {mode.prompt_family}",
        )

        system_prompt = prompts.read(
            mode.prompt_family,
            mode.implementation_prompts[0],
        )

        task_prompt = prompts.read(
            mode.prompt_family,
            mode.implementation_prompts[1],
        )

        implementation_user_prompt = (
            architecture_pipeline.build_implementation_prompt(
                task_prompt,
                evidence,
            )
        )

        _stage(
            mode.label,
            "PROMPTS",
            "Loaded architecture implementation prompts",
        )

        _stage(
            mode.label,
            "LLM",
            "Running architecture model",
        )

        implementation_output, err = ai.call(
            system_prompt,
            implementation_user_prompt,
            review=False,
        )

        if err:
            _stage(mode.label, "LLM", "Failed")
            return f"MODEL FAILED: {err}"

        _stage(
            mode.label,
            "LLM",
            "Architecture model complete",
        )

        review_system_prompt = prompts.read(
            mode.prompt_family,
            mode.review_prompts[0],
        )

        review_user_prompt = (
            architecture_pipeline.build_review_prompt(
                implementation_output,
                evidence,
            )
        )

        _stage(
            mode.label,
            "PROMPTS",
            "Loaded architecture review prompt",
        )

        _stage(
            mode.label,
            "LLM",
            "Running review model",
        )

        review_output, review_err = ai.call(
            review_system_prompt,
            review_user_prompt,
            review=True,
        )

        if review_err:
            review_output = review_err
            _stage(
                mode.label,
                "LLM",
                "Review model failed",
            )
        else:
            _stage(
                mode.label,
                "LLM",
                "Review model complete",
            )

        _stage(
            mode.label,
            "DONE",
            "Review complete",
        )

        return (
            f"OBSERVE: {evidence}\n\n"
            f"ARCHITECTURE: {implementation_output}\n"
            f"REVIEW: {review_output}"
        )

    # -------------------------------------------------
    # DEVOPS - LAB 5
    # -------------------------------------------------

    if mode.key == "devops":

        _stage(
            mode.label,
            "PROMPTS",
            f"Loading prompt family: {mode.prompt_family}",
        )

        task_prompt = prompts.read(
            mode.prompt_family,
            mode.implementation_prompts[0],
        )

        system_prompt = (
            "You are a precise DevOps review assistant. "
            "Use only supplied evidence and reply in at most 30 words."
        )

        implementation_user_prompt = (
            devops_pipeline.build_implementation_prompt(
                task_prompt,
                evidence,
            )
        )

        _stage(
            mode.label,
            "PROMPTS",
            "Loaded DevOps implementation prompt",
        )

        _stage(
            mode.label,
            "LLM",
            "Running DevOps implementation model",
        )

        implementation_output, err = ai.call(
            system_prompt,
            implementation_user_prompt,
            review=False,
        )

        if err:
            _stage(mode.label, "LLM", "Failed")
            return f"MODEL FAILED: {err}"

        _stage(
            mode.label,
            "LLM",
            "DevOps implementation model complete",
        )

        review_system_prompt = prompts.read(
            mode.prompt_family,
            mode.review_prompts[0],
        )

        review_user_prompt = (
            devops_pipeline.build_review_prompt(
                implementation_output,
                evidence,
            )
        )

        _stage(
            mode.label,
            "PROMPTS",
            "Loaded DevOps review prompt",
        )

        _stage(
            mode.label,
            "LLM",
            "Running DevOps review model",
        )

        review_output, review_err = ai.call(
            review_system_prompt,
            review_user_prompt,
            review=True,
        )

        if review_err:
            review_output = review_err
            _stage(
                mode.label,
                "LLM",
                "DevOps review model failed",
            )
        else:
            _stage(
                mode.label,
                "LLM",
                "DevOps review model complete",
            )

        _stage(
            mode.label,
            "DONE",
            "Review complete",
        )

        return (
            f"OBSERVE: {evidence}\n\n"
            f"DEVOPS: {implementation_output}\n"
            f"REVIEW: {review_output}"
        )

    # -------------------------------------------------
    # MCP - LAB 7
    # -------------------------------------------------

    if mode.key == "mcp":

        _stage(
            mode.label,
            "PROMPTS",
            f"Loading prompt family: {mode.prompt_family}",
        )

        task_prompt = prompts.read(
            mode.prompt_family,
            mode.implementation_prompts[0],
        )

        system_prompt = (
            "You are a precise MCP integration validator. "
            "Use only supplied evidence and reply in at most 40 words."
        )

        implementation_user_prompt = (
            mcp_pipeline.build_implementation_prompt(
                task_prompt,
                evidence,
            )
        )

        _stage(
            mode.label,
            "PROMPTS",
            "Loaded MCP implementation prompt",
        )

        _stage(
            mode.label,
            "LLM",
            "Running MCP implementation model",
        )

        implementation_output, err = ai.call(
            system_prompt,
            implementation_user_prompt,
            review=False,
        )

        if err:
            _stage(
                mode.label,
                "LLM",
                "Failed",
            )
            return f"MODEL FAILED: {err}"

        _stage(
            mode.label,
            "LLM",
            "MCP implementation model complete",
        )

        review_system_prompt = prompts.read(
            mode.prompt_family,
            mode.review_prompts[0],
        )

        review_user_prompt = (
            mcp_pipeline.build_review_prompt(
                implementation_output,
                evidence,
            )
        )

        _stage(
            mode.label,
            "PROMPTS",
            "Loaded MCP review prompt",
        )

        _stage(
            mode.label,
            "LLM",
            "Running MCP review model",
        )

        review_output, review_err = ai.call(
            review_system_prompt,
            review_user_prompt,
            review=True,
        )

        if review_err:
            review_output = review_err

            _stage(
                mode.label,
                "LLM",
                "Review model failed",
            )

        else:
            _stage(
                mode.label,
                "LLM",
                "Review model complete",
            )

        _stage(
            mode.label,
            "DONE",
            "Review complete",
        )

        return (
            f"OBSERVE: {evidence}\n\n"
            f"IMPLEMENTATION: {implementation_output}\n"
            f"REVIEW: {review_output}"
        )

    if mode.key == "rag":

        _stage(
            mode.label,
            "PROMPTS",
            f"Loading prompt family: {mode.prompt_family}",
        )

        task_prompt = prompts.read(
            mode.prompt_family,
            mode.implementation_prompts[0],
        )

        system_prompt = (
            "You are a precise RAG integration validator. "
            "Use only supplied evidence and reply in at most 40 words."
        )

        implementation_user_prompt = (
            rag_pipeline.build_implementation_prompt(
                task_prompt,
                evidence,
            )
        )

        _stage(
            mode.label,
            "PROMPTS",
            "Loaded RAG implementation prompt",
        )

        _stage(
            mode.label,
            "LLM",
            "Running RAG implementation model",
        )

        implementation_output, err = ai.call(
            system_prompt,
            implementation_user_prompt,
            review=False,
        )

        if err:
            _stage(
                mode.label,
                "LLM",
                "Failed",
            )
            return f"MODEL FAILED: {err}"

        _stage(
            mode.label,
            "LLM",
            "RAG implementation model complete",
        )

        review_system_prompt = "\n\n".join(
            prompts.read(mode.prompt_family, name) for name in mode.review_prompts
        )

        review_user_prompt = (
            rag_pipeline.build_review_prompt(
                implementation_output,
                evidence,
            )
        )

        _stage(
            mode.label,
            "PROMPTS",
            "Loaded RAG review and reasoning prompts",
        )

        _stage(
            mode.label,
            "LLM",
            "Running RAG review model",
        )

        review_output, review_err = ai.call(
            review_system_prompt,
            review_user_prompt,
            review=True,
        )

        if review_err:
            review_output = review_err

            _stage(
                mode.label,
                "LLM",
                "Review model failed",
            )

        else:
            _stage(
                mode.label,
                "LLM",
                "Review model complete",
            )

        _stage(
            mode.label,
            "DONE",
            "Review complete",
        )

        return (
            f"OBSERVE: {evidence}\n\n"
            f"IMPLEMENTATION: {implementation_output}\n"
            f"REVIEW: {review_output}"
        )


    # -------------------------------------------------
    # LAB 11 - PRE-TEST REVIEW
    # -------------------------------------------------

    if mode.key == "pre_test":
        _stage(mode.label, "PROMPTS", f"Loading prompt family: {mode.prompt_family}")

        task_prompt = prompts.read(
            mode.prompt_family, mode.implementation_prompts[0]
        )

        system_prompt = (
            "You are a precise pre-commit test reviewer. "
            "Use only supplied evidence and reply in at most 60 words."
        )

        implementation_user_prompt = (
            pre_test_pipeline.build_implementation_prompt(task_prompt, evidence)
        )

        _stage(mode.label, "PROMPTS", "Loaded pre-test implementation prompt")
        _stage(mode.label, "LLM", "Running pre-test implementation model")

        implementation_output, err = ai.call(
            system_prompt, implementation_user_prompt, review=False
        )

        if err:
            _stage(mode.label, "LLM", "Failed")
            return f"MODEL FAILED: {err}"

        _stage(mode.label, "LLM", "Pre-test implementation model complete")

        review_prompt_text = prompts.read(
            mode.prompt_family, mode.review_prompts[0]
        )

        review_user_prompt = pre_test_pipeline.build_review_prompt(
            implementation_output, evidence
        )

        _stage(mode.label, "PROMPTS", "Loaded pre-test review prompt")
        _stage(mode.label, "LLM", "Running pre-test review model")

        review_output, review_err = ai.call(
            review_prompt_text, review_user_prompt, review=True
        )

        if review_err:
            review_output = review_err
            _stage(mode.label, "LLM", "Review model failed")
        else:
            _stage(mode.label, "LLM", "Review model complete")

        _stage(mode.label, "DONE", "Review complete")

        return (
            f"OBSERVE: {evidence}\n\n"
            f"IMPLEMENTATION: {implementation_output}\n"
            f"REVIEW: {review_output}"
        )


    # -------------------------------------------------
    # LAB 11 - CI/CD TEST REVIEW
    # -------------------------------------------------

    if mode.key == "cicd_test":
        _stage(mode.label, "PROMPTS", f"Loading prompt family: {mode.prompt_family}")

        task_prompt = prompts.read(
            mode.prompt_family, mode.implementation_prompts[0]
        )

        system_prompt = (
            "You are a precise CI/CD test reviewer. "
            "Use only supplied evidence and reply in at most 60 words."
        )

        implementation_user_prompt = (
            cicd_test_pipeline.build_implementation_prompt(task_prompt, evidence)
        )

        _stage(mode.label, "PROMPTS", "Loaded CI/CD test implementation prompt")
        _stage(mode.label, "LLM", "Running CI/CD test implementation model")

        implementation_output, err = ai.call(
            system_prompt, implementation_user_prompt, review=False
        )

        if err:
            _stage(mode.label, "LLM", "Failed")
            return f"MODEL FAILED: {err}"

        _stage(mode.label, "LLM", "CI/CD test implementation model complete")

        review_prompt_text = prompts.read(
            mode.prompt_family, mode.review_prompts[0]
        )

        review_user_prompt = cicd_test_pipeline.build_review_prompt(
            implementation_output, evidence
        )

        _stage(mode.label, "PROMPTS", "Loaded CI/CD test review prompt")
        _stage(mode.label, "LLM", "Running CI/CD test review model")

        review_output, review_err = ai.call(
            review_prompt_text, review_user_prompt, review=True
        )

        if review_err:
            review_output = review_err
            _stage(mode.label, "LLM", "Review model failed")
        else:
            _stage(mode.label, "LLM", "Review model complete")

        _stage(mode.label, "DONE", "Review complete")

        return (
            f"OBSERVE: {evidence}\n\n"
            f"IMPLEMENTATION: {implementation_output}\n"
            f"REVIEW: {review_output}"
        )


    # -------------------------------------------------
    # LAB 11 - DEPLOYMENT REVIEW
    # -------------------------------------------------

    if mode.key == "deployment":
        _stage(mode.label, "PROMPTS", f"Loading prompt family: {mode.prompt_family}")

        task_prompt = prompts.read(
            mode.prompt_family, mode.implementation_prompts[0]
        )

        system_prompt = (
            "You are a precise Azure deployment reviewer. "
            "Use only supplied evidence and reply in at most 80 words."
        )

        implementation_user_prompt = (
            deployment_pipeline.build_implementation_prompt(task_prompt, evidence)
        )

        _stage(mode.label, "PROMPTS", "Loaded deployment implementation prompt")
        _stage(mode.label, "LLM", "Running deployment implementation model")

        implementation_output, err = ai.call(
            system_prompt, implementation_user_prompt, review=False
        )

        if err:
            _stage(mode.label, "LLM", "Failed")
            return f"MODEL FAILED: {err}"

        _stage(mode.label, "LLM", "Deployment implementation model complete")

        review_prompt_text = prompts.read(
            mode.prompt_family, mode.review_prompts[0]
        )

        review_user_prompt = deployment_pipeline.build_review_prompt(
            implementation_output, evidence
        )

        _stage(mode.label, "PROMPTS", "Loaded deployment review prompt")
        _stage(mode.label, "LLM", "Running deployment review model")

        review_output, review_err = ai.call(
            review_prompt_text, review_user_prompt, review=True
        )

        if review_err:
            review_output = review_err
            _stage(mode.label, "LLM", "Review model failed")
        else:
            _stage(mode.label, "LLM", "Review model complete")

        _stage(mode.label, "DONE", "Review complete")

        return (
            f"OBSERVE: {evidence}\n\n"
            f"IMPLEMENTATION: {implementation_output}\n"
            f"REVIEW: {review_output}"
        )

    return "Unknown mode."