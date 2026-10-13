# Lab 7 MCP Model Validation — 2026-10-13

## Observed execution

The MCP collector passed and the Qwen implementation model call completed. The original runner buffered model output until both calls finished, so the implementation assessment text was not preserved and is not reconstructed here.

The Llama 3.1 8B review did not complete. Ollama server.log recorded HTTP 500 after 10m1s at 21:27:31 Australia/Sydney on 2026-10-13. The client automatically retried. The agent stopped only its own validation process during that retry.

## Status

- Tool/helper, HTTP and MCP protocol checks: passed; see integration-report.md and mcp-protocol-check.json.
- Full dual-model validation: INCOMPLETE (Llama timeout).
- New runner configuration disables automatic retries and accepts OLLAMA_TIMEOUT_SECONDS.
- scripts/run_lab_review.py saves each model result as soon as it returns, including errors.

Rerun when the local review model can respond:

```bash
.venv/bin/python -u scripts/run_lab_review.py mcp --timeout 600
```
