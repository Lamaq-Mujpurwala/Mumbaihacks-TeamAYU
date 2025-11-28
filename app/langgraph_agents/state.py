"""
Shared State Definitions for LangGraph Agents
All agents communicate through this typed state.
"""

from typing import TypedDict, Annotated, Literal, Optional
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


# ==================== LANGGRAPH STATE ====================

class AgentState(TypedDict):
    """State shared across all agents in the graph"""
    # Core message history
    messages: Annotated[list, add_messages]
    
    # User context (injected at start)
    user_id: int
    raw_query: str
    
    # Routing state
    next_agent: Optional[str]  # Which agent to call next
    pending_agents: list[str]  # Agents still to be called
    completed_agents: list[str]  # Agents that have finished
    
    # Results accumulator
    agent_outputs: dict[str, dict]  # {"analyst": {...}, "planner": {...}}
    
    # Final output
    final_response: Optional[str]
    error: Optional[str]


# ==================== STRUCTURED OUTPUTS ====================

class RouterDecision(BaseModel):
    """Output from the router/supervisor"""
    agents_to_call: list[Literal["analyst", "knowledge", "planner", "transaction"]] = Field(
        description="List of agents to invoke for this query. Can be 1-3 agents."
    )
    reasoning: str = Field(
        description="Brief explanation of why these agents were selected"
    )


class AgentResponse(BaseModel):
    """Standard response format from all agents"""
    status: Literal["success", "error", "no_data"] = "success"
    summary: str = Field(description="Human-readable summary of the result")
    data: dict = Field(default_factory=dict, description="Structured data payload")
    

class ToolResult(BaseModel):
    """Wrapper for tool outputs to guide agent behavior"""
    success: bool
    data: dict
    message: str


# ==================== INTENT CLASSIFICATION ====================

AGENT_DESCRIPTIONS = {
    "analyst": "Analyzes spending patterns, detects anomalies, forecasts balance. Use for: 'how much did I spend', 'unusual transactions', 'predict my balance'",
    "knowledge": "Answers financial knowledge questions using RAG. Use for: 'what is SIP', 'explain 80C', 'how does UPI work'",
    "planner": "Manages budgets and savings goals. Use for: 'set budget', 'create goal', 'check my budgets'",
    "transaction": "Handles manual transactions and liabilities. Use for: 'add expense', 'show my loans', 'financial snapshot'"
}


# ==================== HELPER FUNCTIONS ====================

def create_initial_state(user_id: int, query: str) -> AgentState:
    """Create a fresh state for a new query"""
    return AgentState(
        messages=[],
        user_id=user_id,
        raw_query=query,
        next_agent=None,
        pending_agents=[],
        completed_agents=[],
        agent_outputs={},
        final_response=None,
        error=None
    )
