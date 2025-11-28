"""
Analyst Agent
LangGraph-powered agent for financial analysis.
Uses ReAct pattern with constrained tools.
"""

import os
from typing import Any, Dict
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

from app.langgraph_agents.tools.analyst_tools import ANALYST_TOOLS

load_dotenv()

# System prompt - keeps agent focused and prevents loops
ANALYST_SYSTEM_PROMPT = """You are a Financial Analyst Agent. Your ONLY job is to analyze transaction data.

CAPABILITIES:
1. get_spending_breakdown - Analyze spending by category
2. detect_spending_anomalies - Find unusual transactions  
3. forecast_balance - Predict future cash flow

RULES:
1. Use tools to fetch data - NEVER make up numbers or guess
2. Call ONE tool at a time, wait for result
3. After getting data, summarize findings clearly and STOP
4. If data shows "no_data" or "insufficient_data", inform user politely
5. Use Indian Rupees (₹) for all currency
6. Be concise - max 3-4 sentences for summary
7. If user asks something outside your scope, say "I can only help with spending analysis, anomaly detection, and cash flow forecasting."

IMPORTANT: After receiving tool results, provide your analysis and END your response. Do not call more tools unless absolutely necessary."""


def create_analyst_agent():
    """Create the Analyst Agent with ReAct pattern"""
    
    # Initialize LLM - Using llama-scout (30k TPM) to avoid rate limits
    # gpt-oss (8k TPM) is reserved for supervisor + planner
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not found in environment")
    
    llm = ChatGroq(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        temperature=0,
        groq_api_key=api_key
    )
    
    # Create agent with prompt passed as messages_modifier (new LangGraph API)
    # The prompt is passed as a SystemMessage in the messages
    agent = create_react_agent(
        llm,
        ANALYST_TOOLS,
        prompt=ANALYST_SYSTEM_PROMPT,  # New API uses 'prompt' parameter
    )
    
    return agent


# Global agent instance (lazy loaded)
_analyst_agent = None


def get_analyst_agent():
    """Get or create the analyst agent (singleton)"""
    global _analyst_agent
    if _analyst_agent is None:
        _analyst_agent = create_analyst_agent()
    return _analyst_agent


async def run_analyst(user_id: int, query: str) -> Dict[str, Any]:
    """
    Run the analyst agent with a user query.
    
    Args:
        user_id: The user's ID (injected into tool calls)
        query: The user's natural language query
    
    Returns:
        Dict with 'response' (str) and 'tool_calls' (list)
    """
    agent = get_analyst_agent()
    
    # Inject user_id into the query context
    augmented_query = f"[User ID: {user_id}] {query}"
    
    # Run agent
    config = {
        "recursion_limit": 10,  # Max 10 steps to prevent infinite loops
    }
    
    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=augmented_query)]},
        config=config
    )
    
    # Extract response
    messages = result.get("messages", [])
    
    # Get final AI response
    final_response = ""
    tool_calls = []
    
    for msg in messages:
        if hasattr(msg, 'content') and msg.type == "ai" and msg.content:
            final_response = msg.content
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            tool_calls.extend([tc['name'] for tc in msg.tool_calls])
    
    return {
        "response": final_response,
        "tool_calls": tool_calls,
        "message_count": len(messages)
    }


def run_analyst_sync(user_id: int, query: str) -> Dict[str, Any]:
    """Synchronous version of run_analyst"""
    import asyncio
    return asyncio.run(run_analyst(user_id, query))
