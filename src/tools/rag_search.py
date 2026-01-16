"""RAG search tool - demonstrates auth-agnostic tool implementation."""
from typing import Dict, Any

from src.models import Principal


async def rag_search(principal: Principal, query: str) -> Dict[str, Any]:
    """
    Search over RAG knowledge base.

    This tool is completely auth-agnostic:
    - Receives the authenticated Principal
    - Assumes authorization already happened
    - Contains NO auth/authz logic
    - Focuses purely on business logic

    Args:
        principal: The authenticated caller (for logging/audit)
        query: Search query

    Returns:
        Search results
    """
    # Simulate RAG search
    results = [
        {
            "chunk_id": "doc_1_chunk_3",
            "content": f"Sample result for query: {query}",
            "score": 0.95
        },
        {
            "chunk_id": "doc_2_chunk_7",
            "content": f"Another relevant result for: {query}",
            "score": 0.87
        }
    ]

    return {
        "query": query,
        "results": results,
        "count": len(results),
        "principal_id": principal.principal_id,  # For audit logging
        "tenant_id": principal.tenant_id
    }
