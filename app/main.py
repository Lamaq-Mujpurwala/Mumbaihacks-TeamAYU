"""
Financial Guardian API - FastAPI Endpoints
Main entry point for the LangGraph-powered multi-agent system.
Mirrors the original financial-guardian-backend API structure.
"""

import os
import sys
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure app is in path
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

load_dotenv()

# Initialize database on startup
from app.core import init_database
from app.core import database as db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("Starting Financial Guardian API...")
    init_database()
    print("Database initialized")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="Financial Guardian AI",
    description="Multi-Agent Financial System Backend (LangGraph)",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Request/Response Models ====================

# Chat Models
class ChatRequest(BaseModel):
    """Chat request - matches original concierge schema"""
    phone_number: Optional[str] = None  # Original field
    user_id: Optional[int] = None  # Direct user_id (new)
    message: str
    session_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "message": "How much did I spend on food this month?",
                "session_id": "session_123"
            }
        }


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    agents_used: Optional[List[str]] = None
    data: Optional[Dict[str, Any]] = None
    ui_actions: Optional[List[Dict[str, Any]]] = None
    success: bool = True
    error: Optional[str] = None


# Budget Models
class BudgetRequest(BaseModel):
    user_id: int
    category: str
    amount: float
    month: Optional[str] = None


# Goal Models
class GoalRequest(BaseModel):
    user_id: int
    name: str
    target_amount: float
    target_date: Optional[str] = None


class UpdateGoalRequest(BaseModel):
    user_id: int
    amount_to_add: float


# Transaction Models
class ManualTxnRequest(BaseModel):
    user_id: int
    amount: float
    category: str
    narration: str
    date: Optional[str] = None


# Data Sync Models
class SyncRequest(BaseModel):
    phone_number: str
    raw_data: Dict[str, Any]


class FreshnessRequest(BaseModel):
    phone_number: str


# Analysis Models
class AnalyzeRequest(BaseModel):
    user_id: int
    analysis_type: str = "spending_patterns"
    days: int = 30


# ==================== ROUTERS ====================

# Chat Router (Layer 1 - Concierge/User Facing)
chat_router = APIRouter(prefix="/api/chat", tags=["Chat"])

@chat_router.post("/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    """
    Main user interaction endpoint.
    Routes through LangGraph supervisor to appropriate agents.
    """
    try:
        from app.langgraph_agents.supervisor import process_query
        
        # Get user_id from phone_number or direct
        user_id = request.user_id
        if not user_id and request.phone_number:
            user_id = db.get_user_id(request.phone_number)
        
        if not user_id:
            return ChatResponse(
                response="User not found. Please sync your data first.",
                success=False
            )
        
        result = await process_query(user_id=user_id, query=request.message)
        
        return ChatResponse(
            response=result["response"],
            agents_used=result.get("agents_used", []),
            data=result.get("data"),
            success=True
        )
        
    except Exception as e:
        print(f"Chat error: {e}")
        return ChatResponse(
            response="I'm sorry, I encountered an error. Please try again.",
            agents_used=[],
            success=False,
            error=str(e)
        )


# Data Pipeline Router (Setu API Integration)
data_router = APIRouter(prefix="/api/data", tags=["Data Pipeline"])

@data_router.post("/sync-setu")
async def sync_setu_data(req: SyncRequest):
    """Sync data from Setu API to database"""
    try:
        # Store Setu data - this would process bank transactions
        user_id = db.get_or_create_user(req.phone_number)
        # In production: process req.raw_data and store transactions
        return {"success": True, "message": "Data synced successfully", "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@data_router.post("/freshness")
async def check_freshness(req: FreshnessRequest):
    """Check data freshness for a user"""
    user_id = db.get_user_id(req.phone_number)
    if not user_id:
        return {"is_fresh": False, "message": "User not found"}
    
    # Check when data was last updated
    transactions = db.get_user_transactions(user_id, limit=1)
    if transactions:
        last_date = transactions[0].get('transaction_date')
        return {"is_fresh": True, "last_sync": last_date}
    return {"is_fresh": False, "message": "No transaction data"}


# Agent Router (Direct Agent Access)
agent_router = APIRouter(prefix="/api/agent", tags=["Specialist Agents"])

@agent_router.post("/analyze")
async def agent_analyze(req: AnalyzeRequest):
    """Direct access to Financial Analyst Agent"""
    try:
        from app.langgraph_agents.analyst_agent import run_analyst
        
        query_map = {
            'spending_patterns': f"Analyze my spending patterns for the last {req.days} days",
            'anomalies': f"Detect any unusual spending in the last {req.days} days",
            'forecast': f"Forecast my cash flow for the next {req.days} days"
        }
        
        query = query_map.get(req.analysis_type, query_map['spending_patterns'])
        result = await run_analyst(req.user_id, query)
        
        return {
            "success": True,
            "analysis_type": req.analysis_type,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# UI Endpoints Router (Direct DB Access for Frontend)
ui_router = APIRouter(prefix="/api", tags=["UI Endpoints"])

# --- Budgets ---
@ui_router.get("/budgets")
async def get_budgets(user_id: int, month: Optional[str] = None):
    """Get budget status for a user"""
    month = month or datetime.now().strftime("%Y-%m")
    budgets = db.get_user_budgets(user_id, month)
    
    # Calculate spending per budget
    analysis = []
    total_budget = 0
    total_spent = 0
    
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        for budget in budgets:
            cat_id = budget['category_id']
            limit_amount = budget['amount_limit']
            cat_name = budget['category_name']
            
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total 
                FROM transactions 
                WHERE user_id = ? AND category_id = ? 
                AND strftime('%Y-%m', transaction_date) = ? 
                AND type = 'expense'
            """, (user_id, cat_id, month))
            
            row = cursor.fetchone()
            spent = row['total'] if row else 0
            
            status = "over" if spent > limit_amount else "warning" if spent > limit_amount * 0.9 else "under"
            
            analysis.append({
                "category": cat_name,
                "limit": limit_amount,
                "spent": spent,
                "remaining": limit_amount - spent,
                "percent_used": (spent / limit_amount * 100) if limit_amount > 0 else 0,
                "status": status
            })
            
            total_budget += limit_amount
            total_spent += spent
    
    return {
        "month": month,
        "total_budget": total_budget,
        "total_spent": total_spent,
        "overall_status": "over" if total_spent > total_budget else "under",
        "categories": analysis
    }


@ui_router.post("/budgets")
async def set_budget(req: BudgetRequest):
    """Set or update a budget"""
    month = req.month or datetime.now().strftime("%Y-%m")
    
    with db.get_db_connection() as conn:
        category_id = db.get_or_create_category(conn, req.user_id, req.category, "expense")
    
    budget_id = db.save_budget(req.user_id, category_id, req.amount, month)
    
    return {
        "status": "success",
        "message": f"Budget set for {req.category}: Rs.{req.amount}",
        "budget_id": budget_id
    }


@ui_router.put("/budgets")
async def update_budget(req: BudgetRequest):
    """Update a budget (alias for POST)"""
    return await set_budget(req)


@ui_router.delete("/budgets/{category}")
async def delete_budget(category: str, user_id: int, month: Optional[str] = None):
    """Delete a budget"""
    month = month or datetime.now().strftime("%Y-%m")
    
    with db.get_db_connection() as conn:
        category_id = db.get_or_create_category(conn, user_id, category, "expense")
    
    success = db.delete_budget(user_id, category_id, month)
    
    if success:
        return {"status": "success", "message": f"Budget removed for {category}"}
    else:
        return {"status": "error", "message": "Budget not found"}


# --- Goals ---
@ui_router.get("/goals")
async def get_goals(user_id: int):
    """Get all goals for a user"""
    goals = db.get_user_goals(user_id)
    
    result = []
    for goal in goals:
        progress = (goal['current_amount'] / goal['target_amount'] * 100) if goal['target_amount'] > 0 else 0
        result.append({
            **goal,
            "progress_percent": round(progress, 1),
            "remaining": goal['target_amount'] - goal['current_amount']
        })
    
    return {"goals": result, "count": len(result)}


@ui_router.post("/goals")
async def create_goal(req: GoalRequest):
    """Create a new savings goal"""
    goal_id = db.save_goal(req.user_id, req.name, req.target_amount, req.target_date)
    
    return {
        "status": "success",
        "message": f"Goal '{req.name}' created with target Rs.{req.target_amount}",
        "goal_id": goal_id
    }


@ui_router.put("/goals/{goal_id}")
async def update_goal(goal_id: int, req: UpdateGoalRequest):
    """Add funds to a goal"""
    success = db.update_goal_progress(req.user_id, goal_id, req.amount_to_add)
    
    if success:
        return {"status": "success", "message": f"Added Rs.{req.amount_to_add:,.2f} to goal"}
    else:
        return {"status": "error", "message": "Goal not found"}


@ui_router.delete("/goals/{goal_id}")
async def delete_goal(goal_id: int, user_id: int):
    """Delete a goal"""
    success = db.delete_goal(user_id, goal_id)
    
    if success:
        return {"status": "success", "message": "Goal deleted"}
    else:
        return {"status": "error", "message": "Goal not found"}


# --- Manual Transactions ---
@ui_router.post("/transactions/manual")
async def add_manual_transaction(req: ManualTxnRequest):
    """Add a manual cash transaction"""
    date = req.date or datetime.now().strftime("%Y-%m-%d")
    
    txn_id = db.add_manual_transaction(
        req.user_id, req.amount, req.category, date, req.narration
    )
    
    return {
        "status": "success",
        "message": f"Added transaction: Rs.{req.amount} for {req.category}",
        "transaction_id": txn_id
    }


@ui_router.get("/transactions/manual")
async def get_manual_transactions(user_id: int):
    """Get all manual transactions"""
    transactions = db.get_user_transactions(user_id, limit=100)
    manual_txns = [t for t in transactions if t.get('source') == 'MANUAL']
    
    return {"transactions": manual_txns, "count": len(manual_txns)}


@ui_router.get("/transactions")
async def get_all_transactions(user_id: int, limit: int = 50):
    """Get all transactions"""
    transactions = db.get_user_transactions(user_id, limit=limit)
    return {"transactions": transactions, "count": len(transactions)}


# --- Snapshot & Liabilities ---
@ui_router.get("/snapshot")
async def get_snapshot(user_id: int):
    """Get full financial snapshot"""
    month = datetime.now().strftime("%Y-%m")
    
    goals = db.get_user_goals(user_id)
    budgets = db.get_user_budgets(user_id, month)
    transactions = db.get_user_transactions(user_id, limit=10)
    loans = db.get_user_loans(user_id)
    credit_cards = db.get_user_credit_cards(user_id)
    
    # Calculate totals
    total_goals_target = sum(g['target_amount'] for g in goals)
    total_goals_saved = sum(g['current_amount'] for g in goals)
    total_budget = sum(b['amount_limit'] for b in budgets)
    total_loan_balance = sum(l['remaining_balance'] for l in loans) if loans else 0
    total_cc_due = sum(cc['current_balance'] for cc in credit_cards) if credit_cards else 0
    
    return {
        "user_id": user_id,
        "month": month,
        "summary": {
            "goals_count": len(goals),
            "goals_progress": f"Rs.{total_goals_saved:,.0f} / Rs.{total_goals_target:,.0f}",
            "budgets_count": len(budgets),
            "total_budget": f"Rs.{total_budget:,.0f}",
            "total_liabilities": f"Rs.{total_loan_balance + total_cc_due:,.0f}"
        },
        "goals": goals,
        "budgets": budgets,
        "recent_transactions": transactions,
        "loans": loans,
        "credit_cards": credit_cards
    }


@ui_router.get("/liabilities")
async def get_liabilities(user_id: int):
    """Get liabilities summary (loans + credit cards)"""
    loans = db.get_user_loans(user_id)
    credit_cards = db.get_user_credit_cards(user_id)
    
    total_loan_balance = sum(l['remaining_balance'] for l in loans) if loans else 0
    total_cc_due = sum(cc['current_balance'] for cc in credit_cards) if credit_cards else 0
    
    return {
        "loans": loans,
        "credit_cards": credit_cards,
        "total_loan_balance": total_loan_balance,
        "total_credit_card_due": total_cc_due,
        "total_liabilities": total_loan_balance + total_cc_due
    }


# ==================== Register Routers ====================
app.include_router(chat_router)
app.include_router(data_router)
app.include_router(agent_router)
app.include_router(ui_router)


# ==================== Health Check ====================
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "online",
        "service": "Financial Guardian AI",
        "version": "2.0.0",
        "architecture": "LangGraph Multi-Agent"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    from app.core.pinecone_service import pinecone_service
    
    return {
        "status": "healthy",
        "service": "financial-guardian-backend",
        "version": "2.0.0",
        "components": {
            "database": "connected",
            "pinecone": "connected" if pinecone_service.is_available() else "unavailable",
            "llm": "configured" if os.environ.get("GROQ_API_KEY") else "missing"
        }
    }


# ==================== Run Server ====================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 5001))
    print(f"Starting server on port {port}...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
