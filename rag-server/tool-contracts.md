# RAG Tool Contracts

## refresh_corpus
- Purpose: rebuild corpus and vector index
- Input: `caller` (optional)
- Output: `status`, `chunk_count`, `collection`, `corpus_path` or `error`
- Policy class: read + index update

## retrieve_context
- Purpose: retrieve relevant chunks
- Input: `query` (required), `k` (optional), `caller` (optional)
- Output: `status`, `results[]` with `chunk_id`, `source_id`, `authority_tier`, `distance`, `text`
- Policy class: read

## answer_question
- Purpose: answer from retrieved context only
- Input: `query` (required), `k` (optional), `caller` (optional)
- Output: `answer`, `citations[]`, `confidence_category`, `retrieval_summary` or `error`
- Policy class: read + grounded response

## Implementation notes

- Run from repository root; use `.venv-lab7/bin/python`. MCP configuration paths are relative to that working directory.
- `k` must be an integer 1–20. Blank queries are rejected. HTTP JSON body must be an object.
- Vector embeddings are deterministic lexical feature hashes (256 dimensions), not learned semantic embeddings.
- Retrieval removes candidates with no lexical overlap and filters explicit subject codes. Fewer than k results are possible.
- Source tiers are provenance labels, not evidence that a chunk answers the question. Confidence uses query coverage and is not a calibrated probability.
- General answers call local Ollama. Model failure returns an error, not successful answer text.
- Count answers use the aggregate count chunk; subject answers describe retrieved records, not a guaranteed complete list.
- Refresh replaces the derived corpus/index. Avoid concurrent refresh across HTTP and MCP processes.
- Local root SQLite and Docker database volume are independent data sources.
