from pathlib import Path

from rag_pipeline import retrieve_context, read_corpus

METRICS_PATH = Path(__file__).resolve().parent / "retrieval-metrics.md"

BENCHMARKS = [
    {"query": "students enrolled in ASD101"},
    {"query": "student count"},
    {"query": "CI report status"},
]


def relevant_ids(query: str) -> set[str]:
    corpus = read_corpus()
    if query == "students enrolled in ASD101":
        return {c["chunk_id"] for c in corpus if "Student record:" in c["text"] and "subject_code=ASD101." in c["text"]}
    if query == "student count":
        return {c["chunk_id"] for c in corpus if c["chunk_id"] in {"db_student_count", "db_service_student_count"}}
    return {c["chunk_id"] for c in corpus if c["source_id"] == "reports/report.json"}


def evaluate_query(benchmark: dict) -> dict:
    response = retrieve_context(benchmark["query"], 5)
    if response.get("status") != "success":
        raise RuntimeError(response)
    retrieved = [r["chunk_id"] for r in response["results"][:5]]
    expected = relevant_ids(benchmark["query"])
    if not expected:
        raise RuntimeError("Benchmark has no labelled relevant chunks")
    relevant = set(retrieved) & expected
    return {
        "query": benchmark["query"],
        "retrieved_chunk_ids": retrieved,
        "relevant_chunk_ids": sorted(relevant),
        "expected_chunk_ids": sorted(expected),
        "p_at_5": len(relevant) / 5,
        "r_at_5": len(relevant) / len(expected),
    }


def write_metrics_report(results: list[dict]) -> None:
    lines = ["# Retrieval Metrics", ""]
    for result in results:
        lines.append(f"## {result['query']}")
        lines.append(f"- Retrieved: {result['retrieved_chunk_ids']}")
        lines.append(f"- Relevant: {result['relevant_chunk_ids']}")
        lines.append(f"- Expected: {result['expected_chunk_ids']}")
        lines.append(f"- P@5: {result['p_at_5']}")
        lines.append(f"- R@5: {result['r_at_5']}")
        lines.append("")
    METRICS_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    results = []
    for benchmark in BENCHMARKS:
        result = evaluate_query(benchmark)
        results.append(result)
        print("Query:", result["query"])
        print("Retrieved:", result["retrieved_chunk_ids"])
        print("Relevant:", result["relevant_chunk_ids"])
        print("P@5:", result["p_at_5"])
        print("R@5:", result["r_at_5"])
        print("---")
    write_metrics_report(results)


if __name__ == "__main__":
    main()
