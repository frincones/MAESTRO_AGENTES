"""Response builder: formats retrieval results and constructs agent context."""

from __future__ import annotations

from typing import List, Optional

from models.search import RetrievalResult


def build_context(retrieval_result: RetrievalResult) -> str:
    """Build formatted context string from retrieval results for LLM consumption."""
    return retrieval_result.format_context()


def get_sources(retrieval_result: RetrievalResult) -> List[str]:
    """Extract unique source document names from results."""
    sources = set()
    for r in retrieval_result.results:
        if r.document_title:
            sources.add(r.document_title)
        elif r.document_source:
            sources.add(r.document_source)
    return sorted(sources)


def get_confidence(retrieval_result: RetrievalResult) -> str:
    """Determine confidence level based on retrieval quality."""
    if not retrieval_result.has_results:
        return "No data found"

    if retrieval_result.reflection_score is not None:
        score = retrieval_result.reflection_score
        if score >= 4:
            return f"High ({score}/5)"
        elif score >= 3:
            return f"Medium ({score}/5)"
        else:
            return f"Low ({score}/5)"

    if retrieval_result.results:
        avg_sim = sum(r.best_score for r in retrieval_result.results) / len(retrieval_result.results)
        if avg_sim >= 0.85:
            return "High"
        elif avg_sim >= 0.7:
            return "Medium"
        else:
            return "Low"

    return "Unknown"


def format_response_with_sources(
    response: str,
    retrieval_result: RetrievalResult,
) -> str:
    """Append source citations to the agent's response."""
    sources = get_sources(retrieval_result)
    if not sources:
        return response

    source_list = "\n".join(f"- {s}" for s in sources)
    return f"{response}\n\n---\n**Sources:**\n{source_list}"
