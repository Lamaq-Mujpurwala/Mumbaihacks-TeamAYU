"""
Transaction Agent
LangGraph-powered agent for managing manual transactions and liabilities.
"""

import os
from typing import Any, Dict
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

from app.langgraph_agents.tools.transaction_tools import TRANSACTION_TOOLS

load_dotenv()

# System prompt for the transaction agent
TRANSACTION_SYSTEM_PROMPT = """You are a Transaction Agent. Your job is to help users record expenses, income, and view their liabilities.

CAPABILITIES:
1. add_expense - Record a manual expense/purchase
2. add_income - Record income received
3. get_recent_transactions - View recent transactions
4. get_liabilities_summary - View loans and credit card dues
5. get_financial_snapshot - Quick overview of cash flow and liabilities

RULES:
1. ALWAYS use tools to record or fetch data - never guess
2. When recording expenses, choose appropriate categories:
   - Electronics, Shopping, Food & Dining, Entertainment, Travel, Healthcare, Utilities, etc.
3. Use Indian Rupees (₹) for all amounts
4. For purchases, always use add_expense tool
5. Confirm what was recorded after each action
6. If user mentions buying something, record it as an expense

IMPORTANT:
- If user says "I spent/bought/purchased X for Y rupees", use add_expense
- Always include a description when adding transactions
- Be concise in responses"""


def create_transaction_agent():
    """Create the Transaction Agent"""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not found")
    
    llm = ChatGroq(
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        temperature=0,
        groq_api_key=api_key
    )
    
    agent = create_react_agent(
        llm,
        TRANSACTION_TOOLS,
        prompt=TRANSACTION_SYSTEM_PROMPT,
    )
    
    return agent


# Global agent instance
_transaction_agent = None


def get_transaction_agent():
    """Get or create the transaction agent"""
    global _transaction_agent
    if _transaction_agent is None:
        _transaction_agent = create_transaction_agent()
    return _transaction_agent


async def run_transaction(user_id: int, query: str) -> Dict[str, Any]:
    """
    Run the transaction agent with a user query.
    
    Args:
        user_id: The user's ID
        query: The user's natural language query
    
    Returns:
        Dict with 'response' and 'tool_calls'
    """
    agent = get_transaction_agent()
    
    # Inject user_id into the query context
    augmented_query = f"[User ID: {user_id}] {query}"
    
    config = {"recursion_limit": 15}
    
    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=augmented_query)]},
        config=config
    )
    
    messages = result.get("messages", [])
    
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
