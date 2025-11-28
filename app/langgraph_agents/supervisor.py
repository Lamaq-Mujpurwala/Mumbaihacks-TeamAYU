"""
Supervisor Agent (Router)
Routes user queries to the appropriate specialist agent(s).
Uses LangGraph StateGraph for multi-agent orchestration.
"""

import os
import json
from typing import Literal
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END

from app.langgraph_agents.state import AgentState, AGENT_DESCRIPTIONS, RouterDecision

load_dotenv()

# Router system prompt
ROUTER_SYSTEM_PROMPT = """You are a Financial Assistant Router. Your job is to analyze the user's query and decide which specialist agent(s) should handle it.

AVAILABLE AGENTS:
1. analyst - Analyzes spending patterns, detects anomalies, forecasts balance
   Use for: "how much did I spend", "unusual transactions", "predict my balance", "spending breakdown"

2. knowledge - Answers financial knowledge questions using a knowledge base
   Use for: "what is SIP", "explain 80C", "how does UPI work", "tax saving tips"

3. planner - Manages budgets and savings goals
   Use for: "set budget", "create goal", "check my budgets", "update goal", "add to goal"

4. transaction - Handles manual transactions and liabilities
   Use for: "add expense", "record purchase", "show my loans", "financial snapshot", "credit card dues"

CRITICAL ROUTING RULES:
1. Select 1-3 agents based on the query
2. For simple queries, use only 1 agent
3. **DUAL-ACTION RULE**: When user mentions buying/spending/purchasing something AND mentions what it's for (e.g., "for my gaming PC", "for gaming", "for MacBook", "for vacation"):
   - ALWAYS route to BOTH ["transaction", "planner"] in that ORDER
   - transaction records the expense
   - planner updates any related goal
4. Keywords suggesting goal-related purchase: "for my", "for gaming", "towards", "bought for", "gaming PC", "MacBook", "vacation", "trip", "phone", "laptop"
5. If user just says "bought X" without mentioning purpose, use only ["transaction"]
6. If unsure, default to "analyst" for spending questions or "knowledge" for general questions

EXAMPLES:
- "I spent 15000 on graphics card for my gaming PC" -> ["transaction", "planner"] (dual-action: expense + goal)
- "bought a new graphic card for 10000 for my Gaming PC" -> ["transaction", "planner"] (dual-action)
- "How much did I spend on food?" -> ["analyst"]
- "Set a budget of 5000 for shopping" -> ["planner"]
- "What is mutual fund?" -> ["knowledge"]
- "Add 5000 to my MacBook goal" -> ["planner"]
- "I bought a laptop for 80000" -> ["transaction"] (no goal mentioned)
- "paid 5000 for my Bali trip" -> ["transaction", "planner"] (trip goal likely exists)

OUTPUT FORMAT (JSON only):
{"agents_to_call": ["transaction", "planner"], "reasoning": "User bought something for a goal"}
"""


def create_router_llm():
    """Create the LLM for routing decisions"""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not found")
    
    return ChatGroq(
        model="openai/gpt-oss-20b",
        temperature=0,
        groq_api_key=api_key
    )


async def router_node(state: AgentState) -> AgentState:
    """
    Router node - decides which agents to call.
    """
    llm = create_router_llm()
    
    # Get routing decision from LLM
    messages = [
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        HumanMessage(content=f"User query: {state['raw_query']}")
    ]
    
    response = await llm.ainvoke(messages)
    
    # Parse the JSON response
    try:
        # Extract JSON from response
        content = response.content
        # Handle cases where LLM wraps JSON in markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        decision = json.loads(content.strip())
        agents_to_call = decision.get("agents_to_call", ["analyst"])
        reasoning = decision.get("reasoning", "")
    except (json.JSONDecodeError, IndexError):
        # Fallback to analyst if parsing fails
        agents_to_call = ["analyst"]
        reasoning = "Fallback to analyst due to parsing error"
    
    # Validate agents
    valid_agents = ["analyst", "knowledge", "planner", "transaction"]
    agents_to_call = [a for a in agents_to_call if a in valid_agents]
    
    if not agents_to_call:
        agents_to_call = ["analyst"]
    
    print(f"🔀 Router Decision: {agents_to_call} - {reasoning}")
    
    return {
        **state,
        "pending_agents": agents_to_call,
        "completed_agents": [],
        "next_agent": agents_to_call[0] if agents_to_call else None
    }


async def analyst_node(state: AgentState) -> AgentState:
    """Execute the analyst agent"""
    from app.langgraph_agents.analyst_agent import run_analyst
    
    print(f"📊 Analyst Agent processing...")
    result = await run_analyst(state["user_id"], state["raw_query"])
    
    # Store result
    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["analyst"] = {
        "response": result["response"],
        "tool_calls": result["tool_calls"]
    }
    
    # Update state
    completed = state.get("completed_agents", []) + ["analyst"]
    pending = [a for a in state.get("pending_agents", []) if a != "analyst"]
    
    return {
        **state,
        "agent_outputs": agent_outputs,
        "completed_agents": completed,
        "pending_agents": pending,
        "next_agent": pending[0] if pending else None
    }


async def knowledge_node(state: AgentState) -> AgentState:
    """Execute the knowledge agent"""
    from app.langgraph_agents.knowledge_agent import run_knowledge
    
    print(f"📚 Knowledge Agent processing...")
    result = await run_knowledge(state["user_id"], state["raw_query"])
    
    # Store result
    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["knowledge"] = {
        "response": result["response"],
        "tool_calls": result["tool_calls"],
        "sources": result.get("sources", [])
    }
    
    completed = state.get("completed_agents", []) + ["knowledge"]
    pending = [a for a in state.get("pending_agents", []) if a != "knowledge"]
    
    return {
        **state,
        "agent_outputs": agent_outputs,
        "completed_agents": completed,
        "pending_agents": pending,
        "next_agent": pending[0] if pending else None
    }


async def planner_node(state: AgentState) -> AgentState:
    """Execute the planner agent"""
    from app.langgraph_agents.planner_agent import run_planner
    
    print(f"📋 Planner Agent processing...")
    
    # Build context from previous agent outputs (for dual-action scenarios)
    context = ""
    agent_outputs = state.get("agent_outputs", {})
    
    if "transaction" in agent_outputs:
        txn_output = agent_outputs["transaction"]
        context = f"\n\n[CONTEXT: A transaction was just recorded. Details: {txn_output.get('response', '')}]\n"
        context += "Your task: Check if the user has any goals related to this purchase and update goal progress if applicable. First call get_goals_status to see all goals."
    
    query = state["raw_query"] + context
    result = await run_planner(state["user_id"], query)
    
    # Store result
    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["planner"] = {
        "response": result["response"],
        "tool_calls": result["tool_calls"]
    }
    
    completed = state.get("completed_agents", []) + ["planner"]
    pending = [a for a in state.get("pending_agents", []) if a != "planner"]
    
    return {
        **state,
        "agent_outputs": agent_outputs,
        "completed_agents": completed,
        "pending_agents": pending,
        "next_agent": pending[0] if pending else None
    }


async def transaction_node(state: AgentState) -> AgentState:
    """Execute the transaction agent"""
    from app.langgraph_agents.transaction_agent import run_transaction
    
    print(f"💳 Transaction Agent processing...")
    result = await run_transaction(state["user_id"], state["raw_query"])
    
    # Store result
    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["transaction"] = {
        "response": result["response"],
        "tool_calls": result["tool_calls"]
    }
    
    completed = state.get("completed_agents", []) + ["transaction"]
    pending = [a for a in state.get("pending_agents", []) if a != "transaction"]
    
    return {
        **state,
        "agent_outputs": agent_outputs,
        "completed_agents": completed,
        "pending_agents": pending,
        "next_agent": pending[0] if pending else None
    }


async def synthesizer_node(state: AgentState) -> AgentState:
    """Synthesize final response from all agent outputs"""
    print(f"✨ Synthesizing final response...")
    
    agent_outputs = state.get("agent_outputs", {})
    
    if len(agent_outputs) == 1:
        # Single agent - use its response directly
        agent_name = list(agent_outputs.keys())[0]
        final_response = agent_outputs[agent_name]["response"]
    else:
        # Multiple agents - combine responses
        llm = create_router_llm()
        
        combined_data = "\n\n".join([
            f"=== {agent.upper()} AGENT ===\n{data['response']}"
            for agent, data in agent_outputs.items()
        ])
        
        messages = [
            SystemMessage(content="""You are a Financial Assistant. Combine the following agent responses into a single, coherent response for the user.
            Be concise and helpful. Use Indian Rupees (₹) for currency."""),
            HumanMessage(content=f"User query: {state['raw_query']}\n\nAgent Responses:\n{combined_data}")
        ]
        
        response = await llm.ainvoke(messages)
        final_response = response.content
    
    return {
        **state,
        "final_response": final_response
    }


def determine_next_node(state: AgentState) -> str:
    """Determine the next node based on pending agents"""
    next_agent = state.get("next_agent")
    
    if next_agent:
        return next_agent
    else:
        return "synthesizer"


def create_supervisor_graph():
    """Create the supervisor StateGraph"""
    
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("knowledge", knowledge_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("transaction", transaction_node)
    workflow.add_node("synthesizer", synthesizer_node)
    
    # Set entry point
    workflow.set_entry_point("router")
    
    # Add conditional edges from router
    workflow.add_conditional_edges(
        "router",
        determine_next_node,
        {
            "analyst": "analyst",
            "knowledge": "knowledge",
            "planner": "planner",
            "transaction": "transaction",
            "synthesizer": "synthesizer"
        }
    )
    
    # Add conditional edges from each agent back to router logic
    for agent in ["analyst", "knowledge", "planner", "transaction"]:
        workflow.add_conditional_edges(
            agent,
            determine_next_node,
            {
                "analyst": "analyst",
                "knowledge": "knowledge",
                "planner": "planner",
                "transaction": "transaction",
                "synthesizer": "synthesizer"
            }
        )
    
    # Synthesizer goes to END
    workflow.add_edge("synthesizer", END)
    
    # Compile the graph
    return workflow.compile()


# Global supervisor instance
_supervisor = None


def get_supervisor():
    """Get or create the supervisor graph"""
    global _supervisor
    if _supervisor is None:
        _supervisor = create_supervisor_graph()
    return _supervisor


async def process_query(user_id: int, query: str) -> dict:
    """
    Main entry point - process a user query through the supervisor.
    
    Args:
        user_id: The user's ID
        query: Natural language query
        
    Returns:
        Dict with 'response' and metadata
    """
    supervisor = get_supervisor()
    
    # Create initial state
    initial_state = {
        "messages": [],
        "user_id": user_id,
        "raw_query": query,
        "next_agent": None,
        "pending_agents": [],
        "completed_agents": [],
        "agent_outputs": {},
        "final_response": None,
        "error": None
    }
    
    # Run the graph
    config = {"recursion_limit": 15}
    result = await supervisor.ainvoke(initial_state, config=config)
    
    return {
        "response": result.get("final_response", "I couldn't process your request."),
        "agents_used": result.get("completed_agents", []),
        "agent_outputs": result.get("agent_outputs", {})
    }
