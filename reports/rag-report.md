# Lab 8 RAG Runtime Report — 2026-10-13

## Observed execution

- ChromaDB refresh succeeded with `vector_store_status: ready`.
- Vector retrieval found db_student_1 and db_student_2 for ASD101.
- Subject answer named John Smith and Sarah Jones with root enrolment.db citations.
- Student count answer returned 10 using the aggregate chunk even with k=1.
- Missing subject XYZ999 returned Insufficient evidence, no citations, confidence Unknown.
- 7 isolated offline regression tests passed (`tests/test_rag.py`).
- 11 HTTP checks passed through the rebuilt Docker enrolment service and local RAG server: page serving, health, refresh, retrieval, two answers, missing subject, disabled mode, invalid k, blank query, invalid JSON body.
- Actual HTTP responses: `reports/rag-http-checks.json`.
- MCP protocol: all 3 RAG tools listed and retrieve_context called successfully; `reports/mcp-protocol-check.json`.
- Frontend HTML was served and inspected; browser interaction/visual rendering was not automated.

## Retrieval metrics

Measured after refreshing the corpus including the Lab 7 evidence reports:

| Query | P@5 | R@5 |
|---|---:|---:|
| students enrolled in ASD101 | 0.4 | 1.0 |
| student count | 0.2 | 1.0 |
| CI report status | 0.2 | 1.0 |

Relevance labels use corpus source/chunk identity, not broad keyword matching. P@5 retains a fixed denominator of 5 even if fewer results are returned. These three queries are a small fixture benchmark, not a general quality guarantee. See rag-server/retrieval-metrics.md for actual IDs.

## Changes from supplied example

- Updated MCP wrapper for installed MCP 2.2; startup logs use stderr.
- Host-local URLs use localhost; Docker proxy uses host.docker.internal:5003.
- Hash features span the full vector rather than only the first 32 positions.
- Removed authority-first ranking that could prioritize irrelevant DB chunks.
- Added query validation, explicit subject filtering, count grounding, conservative confidence, and model-failure errors.
- JSON in the browser uses textContent to avoid interpreting retrieved content as HTML.
- Collector explicitly distinguishes static checks from saved runtime evidence.
- Serialized in-process corpus operations; do not concurrently refresh from separate MCP/HTTP processes.

## Limitations and reflection

1. refresh_corpus builds/indexes evidence; retrieve_context finds up to k chunks; answer_question returns a grounded response and citations.
2. Precision measures retrieved relevance and recall measures relevant evidence recovered. Neither alone proves that generated prose is correct.
3. Collector checks Python structure and required tool definitions, then includes saved metrics and runtime evidence. It does not independently rerun tests.
4. Qwen proposes an assessment and Llama reviews it; both can be wrong. Actual test outputs remain the primary evidence.

This is a lexical hash-vector baseline, not semantic embedding search. General free-form answers still need human citation review. Root SQLite and Docker DB are separate. Evidence is limited to the current seeded data. LLM validation results and failures belong in rag-validation-report.md.

## Final verification boundary

The final source passed 7 regression tests. The 11 HTTP checks passed before the last changes to missing-source handling and empty-index auto-refresh. A final HTTP rerun was requested but declined, so it was not executed. Saved metrics describe the corpus snapshot used by the recorded tests; refresh after changing report files can alter retrieval rankings. Qwen assessment completed; Llama review timed out. Lab 8 dual-model validation remains incomplete.
