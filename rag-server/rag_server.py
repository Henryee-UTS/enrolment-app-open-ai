import sys
from mcp.server import MCPServer

from rag_pipeline import answer_question as answer_question_impl
from rag_pipeline import refresh_corpus as refresh_corpus_impl
from rag_pipeline import retrieve_context as retrieve_context_impl

mcp = MCPServer("Student Enrolment RAG MCP")
AVAILABLE_TOOLS = ["refresh_corpus", "retrieve_context", "answer_question"]


@mcp.tool()
def refresh_corpus(caller: str = "student"):
    return refresh_corpus_impl(caller=caller)


@mcp.tool()
def retrieve_context(query: str, k: int = 5, caller: str = "student"):
    return retrieve_context_impl(query=query, k=k, caller=caller)


@mcp.tool()
def answer_question(query: str, k: int = 5, caller: str = "student"):
    return answer_question_impl(query=query, k=k, caller=caller)


if __name__ == "__main__":
    print("Starting RAG MCP server (stdio)", file=sys.stderr)
    mcp.run()
