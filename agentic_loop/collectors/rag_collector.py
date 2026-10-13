"""Collect static structure and saved runtime evidence; do not imply execution."""
import ast
from pathlib import Path

REQUIRED_RAG_TOOLS = ['refresh_corpus', 'retrieve_context', 'answer_question']


def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
    server_dir = app_dir / 'rag-server'
    required = ['rag_pipeline.py', 'rag_server.py', 'rag_http_server.py', 'rag_eval.py', 'requirements.txt']
    missing = [name for name in required if not (server_dir / name).is_file()]
    if missing:
        return False, 'RAG files missing: ' + ', '.join(missing)
    for name in ['rag_pipeline.py', 'rag_server.py']:
        try:
            tree = ast.parse((server_dir / name).read_text())
        except SyntaxError as exc:
            return False, f'{name}: {exc}'
        functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
        if not set(REQUIRED_RAG_TOOLS) <= functions:
            return False, f'{name}: required RAG tools missing'
    evidence = 'Static check passed: RAG pipeline and MCP server define all 3 tools. Static inspection does not prove runtime correctness.'
    metrics = server_dir / 'retrieval-metrics.md'
    if metrics.exists():
        evidence += '\nSaved retrieval metrics (not rerun by collector):\n' + metrics.read_text()[:3500]
    report = app_dir / 'reports' / 'rag-report.md'
    if report.exists():
        evidence += '\nSaved runtime evidence (not rerun by collector):\n' + report.read_text()[:4500]
    return True, evidence
