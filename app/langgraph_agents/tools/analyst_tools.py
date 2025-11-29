"""
Analyst Agent Tools
READ-ONLY tools for analyzing transaction data.
"""

from typing import Optional, Union
from langchain_core.tools import tool

from app.agents.analytics import analytics
from app.core import database as db
from app.core import get_user_balance, recalculate_user_balance


@tool
def get_spending_breakdown(user_id: Union[int, str], days: Union[int, str] = 30, category: Optional[str] = None) -> dict:
    """
    Get spending breakdown by category for the last N days.
    
    Args:
        user_id: The user's ID (number)
        days: Number of days to analyze (default 30)
        category: Optional specific category to filter by
    
    Returns:
        Dict with total_spent, categories breakdown, and insights
    """
    # Coerce types (Groq sometimes passes strings)
    user_id = int(user_id)
    days = int(days)
    return analytics.analyze_spending_patterns(user_id, days, category)


@tool
def detect_spending_anomalies(user_id: Union[int, str], days: Union[int, str] = 30) -> dict:
    """
    Detect unusual or high-value transactions in the specified period.
    
    Args:
        user_id: The user's ID (number)
        days: Number of days to analyze (default 30)
    
    Returns:
        Dict with anomalies list and insights about unusual spending
    """
    user_id = int(user_id)
    days = int(days)
    return analytics.detect_anomalies(user_id, days)


@tool
def forecast_balance(user_id: Union[int, str], days: Union[int, str] = 30) -> dict:
    """
    Predict future balance based on spending and income trends.
    
    Args:
        user_id: The user's ID (number)
        days: Number of historical days to base forecast on (default 30)
    
    Returns:
        Dict with projected_balance and trend analysis
    """
    user_id = int(user_id)
    days = int(days)
    return analytics.forecast_cash_flow(user_id, days)


@tool
def get_current_balance(user_id: Union[int, str]) -> dict:
    """
    Get the user's current account balance and recent financial summary.
    Use this when user asks "what is my balance" or "how much money do I have".
    
    Args:
        user_id: The user's ID (number)
    
    Returns:
        Dict with current balance, total income, total expenses, and net flow
    """
    from datetime import datetime, timedelta
    
    user_id = int(user_id)
    
    # First, try to get balance from the user_balance table (primary source)
    balance_data = get_user_balance(user_id)
    
    if balance_data:
        # Calculate recent activity (last 30 days) for context
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        transactions = db.get_user_transactions(user_id, start_date=thirty_days_ago, limit=100)
        
        recent_income = sum(t['amount'] for t in transactions if t['type'] in ('CREDIT', 'credit', 'income'))
        recent_expenses = sum(t['amount'] for t in transactions if t['type'] in ('DEBIT', 'debit', 'expense'))
        recent_net_flow = recent_income - recent_expenses
        
        return {
            "status": "success",
            "current_balance": round(balance_data['current_balance'], 2),
            "total_income": round(balance_data['total_income'], 2),
            "total_expenses": round(balance_data['total_expenses'], 2),
            "last_transaction_date": balance_data.get('last_transaction_date'),
            "last_updated": balance_data.get('last_updated'),
            "recent_activity": {
                "period": "Last 30 days",
                "income": round(recent_income, 2),
                "expenses": round(recent_expenses, 2),
                "net_flow": round(recent_net_flow, 2)
            },
            "transaction_count": len(transactions)
        }
    
    # Fallback: If no balance record exists, recalculate from transactions
    transactions = db.get_user_transactions(user_id, limit=100)
    
    if not transactions:
        return {
            "status": "no_data",
            "message": "No transaction data found. Please sync your bank account first.",
            "current_balance": 0,
            "total_income": 0,
            "total_expenses": 0
        }
    
    # Recalculate and store balance for future use
    balance_info = recalculate_user_balance(user_id)
    
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    recent_txns = [t for t in transactions if t['transaction_date'] >= thirty_days_ago]
    
    recent_income = sum(t['amount'] for t in recent_txns if t['type'] in ('CREDIT', 'credit', 'income'))
    recent_expenses = sum(t['amount'] for t in recent_txns if t['type'] in ('DEBIT', 'debit', 'expense'))
    recent_net_flow = recent_income - recent_expenses
    
    return {
        "status": "success",
        "current_balance": round(balance_info['current_balance'], 2),
        "total_income": round(balance_info['total_income'], 2),
        "total_expenses": round(balance_info['total_expenses'], 2),
        "last_transaction_date": balance_info.get('last_transaction_date'),
        "recent_activity": {
            "period": "Last 30 days",
            "income": round(recent_income, 2),
            "expenses": round(recent_expenses, 2),
            "net_flow": round(recent_net_flow, 2)
        },
        "transaction_count": len(recent_txns)
    }


# Export all tools as a list for easy agent creation
ANALYST_TOOLS = [get_spending_breakdown, detect_spending_anomalies, forecast_balance, get_current_balance]
