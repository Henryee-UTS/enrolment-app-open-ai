"""Persist actual model assessments, including timeouts, for one lab mode."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'agentic_loop'))
from config.review_config import build_mode_config
from core.ai_runner import AIRunner
from core.orchestrator import run_mode
from core.prompt_registry import PromptRegistry

parser = argparse.ArgumentParser()
parser.add_argument('mode', choices=['mcp', 'rag'])
parser.add_argument('--timeout', type=float, default=120)
args = parser.parse_args()
os.environ['OLLAMA_TIMEOUT_SECONDS'] = str(args.timeout)

class RecordingRunner(AIRunner):
    def call(self, system_prompt, user_prompt, *, review=False, max_tokens=180):
        response = super().call(system_prompt, user_prompt, review=review, max_tokens=max_tokens)
        print(('REVIEW' if review else 'IMPLEMENTATION') + ' CALL: ' + str(response), flush=True)
        with report.open('a') as stream:
            stream.write('\n## ' + ('Review' if review else 'Implementation') + ' model call\n\n')
            stream.write((response[1] or response[0] or 'Empty response') + '\n')
        return response

report = ROOT / 'reports' / ('rag-validation-report.md' if args.mode == 'rag' else 'run-report.md')
report.write_text(f'# {args.mode.upper()} Model Validation\n\nActual local run; timeout {args.timeout}s per request; no automatic retries.\n')
result = run_mode(build_mode_config()[args.mode], ROOT, ROOT, PromptRegistry(ROOT), RecordingRunner())
with report.open('a') as stream:
    stream.write('\n## Orchestrator output\n\n' + result + '\n')
print(result, flush=True)
