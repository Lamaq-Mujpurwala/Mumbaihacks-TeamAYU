"""
Knowledge Agent Tools
Tools for RAG-based financial Q&A using Pinecone.
"""

from langchain_core.tools import tool

from app.core.pinecone_service import pinecone_service


@tool
def search_knowledge_base(query: str) -> dict:
    """
    Search the financial knowledge base for relevant information about any financial topic.
    Use this tool to find information about taxes, investments, banking, insurance, loans, etc.
    
    Args:
        query: The question or topic to search for (e.g., "What is SIP", "Section 80C benefits")
    
    Returns:
        Dict with search results including text and sources
    """
    if not pinecone_service.is_available():
        return {
            "status": "unavailable",
            "message": "Knowledge base is currently unavailable. Please try again later.",
            "results": []
        }
    
    results = pinecone_service.query(query, top_k=3)
    
    if not results:
        return {
            "status": "no_results",
            "message": f"No relevant information found for: {query}",
            "results": []
        }
    
    formatted_results = []
    for r in results:
        formatted_results.append({
            "text": r['text'],
            "source": r['metadata'].get('source', 'Financial Knowledge Base'),
            "relevance": round(r['score'], 4) if r.get('score') else None
        })
    
    # Combine all text for easier consumption
    combined_context = "\n\n---\n\n".join([r['text'] for r in results])
    sources = list(set([r['metadata'].get('source', 'Unknown') for r in results]))
    
    return {
        "status": "success",
        "query": query,
        "count": len(formatted_results),
        "context": combined_context,
        "sources": sources,
        "results": formatted_results
    }


# Export - single tool is cleaner and avoids Groq issues
KNOWLEDGE_TOOLS = [
    search_knowledge_base
]
