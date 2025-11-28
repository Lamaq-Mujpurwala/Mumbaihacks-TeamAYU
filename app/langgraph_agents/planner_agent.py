"""
Planner Agent
LangGraph-powered agent for managing budgets and savings goals.
"""

import os
from typing import Any, Dict
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

from app.langgraph_agents.tools.planner_tools import PLANNER_TOOLS

load_dotenv()

# System prompt for the planner agent
PLANNER_SYSTEM_PROMPT = """You are a Financial Planner Agent. Your job is to help users manage their budgets and savings goals.

CAPABILITIES:
1. set_budget - Set or update a monthly budget for a category
2. remove_budget - Delete a budget
3. check_budget_status - Check spending vs budget limits
4. create_savings_goal - Create a new savings goal
5. add_to_goal - Add money to an existing goal (requires goal_id)
6. remove_goal - Delete a goal (requires goal_id)
7. get_goals_status - View all goals and their progress

RULES:
1. ALWAYS use tools to fetch or modify data - never guess
2. When user wants to update or delete a goal, FIRST call get_goals_status to find the goal_id
3. For budgets, use category names like "Food & Dining", "Shopping", "Entertainment", etc.
4. Use Indian Rupees (₹) for all amounts
5. Be encouraging about savings progress
6. After completing an action, summarize what was done

DUAL-ACTION HANDLING (IMPORTANT):
When you receive a query with [CONTEXT: A transaction was just recorded...]:
1. ALWAYS call get_goals_status FIRST to see the user's goals
2. Look for goals that match the purchase (e.g., "Gaming PC" goal matches "graphics card for gaming PC")
3. If a matching goal exists, call add_to_goal with the goal_id and the spent amount
4. If no matching goal exists, just acknowledge the expense was recorded

IMPORTANT: 
- To update a goal, you need the goal_id. Call get_goals_status first if you don't have it.
- Budget months are in YYYY-MM format (e.g., "2024-11")
- Be concise in your responses.
- When updating goal after a purchase, confirm what was added to which goal."""


def create_planner_agent():
    """Create the Planner Agent"""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not found")
    
    llm = ChatGroq(
        model="openai/gpt-oss-20b",
        temperature=0,
        groq_api_key=api_key
    )
    
    agent = create_react_agent(
        llm,
        PLANNER_TOOLS,
        prompt=PLANNER_SYSTEM_PROMPT,
    )
    
    return agent


# Global agent instance
_planner_agent = None


def get_planner_agent():
    """Get or create the planner agent"""
    global _planner_agent
    if _planner_agent is None:
        _planner_agent = create_planner_agent()
    return _planner_agent


async def run_planner(user_id: int, query: str) -> Dict[str, Any]:
    """
    Run the planner agent with a user query.
    
    Args:
        user_id: The user's ID
        query: The user's natural language query
    
    Returns:
        Dict with 'response' and 'tool_calls'
    """
    agent = get_planner_agent()
    
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
