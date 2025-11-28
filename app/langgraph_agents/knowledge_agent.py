"""
Knowledge Agent
LangGraph-powered agent for answering financial questions using RAG.
"""

import os
from typing import Any, Dict
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

from app.langgraph_agents.tools.knowledge_tools import KNOWLEDGE_TOOLS

load_dotenv()

# System prompt for the knowledge agent - simplified for Groq compatibility
KNOWLEDGE_SYSTEM_PROMPT = """You are a Financial Knowledge Expert for India.

You have ONE tool: search_knowledge_base
- Use it to search for ANY financial topic
- Pass the user's question as the query parameter

WORKFLOW:
1. Call search_knowledge_base with the user's question
2. Read the returned context
3. Answer based ONLY on the context provided
4. If no results found, say you don't have that information

RULES:
- Always search before answering
- Use ₹ for Indian Rupees
- Be accurate - cite sources when available
- Keep answers concise but complete"""


def create_knowledge_agent():
    """Create the Knowledge Agent"""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not found")
    
    llm = ChatGroq(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        temperature=0,
        groq_api_key=api_key
    )
    
    agent = create_react_agent(
        llm,
        KNOWLEDGE_TOOLS,
        prompt=KNOWLEDGE_SYSTEM_PROMPT,
    )
    
    return agent


# Global agent instance
_knowledge_agent = None


def get_knowledge_agent():
    """Get or create the knowledge agent"""
    global _knowledge_agent
    if _knowledge_agent is None:
        _knowledge_agent = create_knowledge_agent()
    return _knowledge_agent


async def run_knowledge(user_id: int, query: str) -> Dict[str, Any]:
    """
    Run the knowledge agent with a user query.
    
    Args:
        user_id: The user's ID (not used directly but kept for consistency)
        query: The user's natural language question
    
    Returns:
        Dict with 'response', 'tool_calls', and 'sources'
    """
    agent = get_knowledge_agent()
    
    config = {"recursion_limit": 10}
    
    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=query)]},
        config=config
    )
    
    messages = result.get("messages", [])
    
    final_response = ""
    tool_calls = []
    sources = []
    
    for msg in messages:
        if hasattr(msg, 'content') and msg.type == "ai" and msg.content:
            final_response = msg.content
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            tool_calls.extend([tc['name'] for tc in msg.tool_calls])
        # Extract sources from tool results
        if msg.type == "tool" and hasattr(msg, 'content'):
            try:
                import json
                content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                if isinstance(content, dict) and 'sources' in content:
                    sources.extend(content['sources'])
            except:
                pass
    
    return {
        "response": final_response,
        "tool_calls": tool_calls,
        "sources": list(set(sources)),
        "message_count": len(messages)
    }
