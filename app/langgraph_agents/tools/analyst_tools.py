"""
Analyst Agent Tools
READ-ONLY tools for analyzing transaction data.
"""

from typing import Optional, Union
from langchain_core.tools import tool

from app.agents.analytics import analytics
from app.core import database as db


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
        Dict with current balance, recent income, recent expenses, and net flow
    """
    from datetime import datetime, timedelta
    
    user_id = int(user_id)
    
    # Get transactions from last 30 days
    transactions = db.get_user_transactions(user_id, limit=100)
    
    if not transactions:
        return {
            "status": "no_data",
            "message": "No transaction data found. Please sync your bank account first.",
            "balance": 0
        }
    
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    recent_txns = [t for t in transactions if t['transaction_date'] >= thirty_days_ago]
    
    total_income = sum(t['amount'] for t in recent_txns if t['type'] in ('CREDIT', 'income'))
    total_expenses = sum(t['amount'] for t in recent_txns if t['type'] in ('DEBIT', 'expense'))
    net_flow = total_income - total_expenses
    
    # Get latest balance if available
    latest_balance = transactions[0].get('balance', 0) if transactions else 0
    
    return {
        "status": "success",
        "current_balance": latest_balance,
        "period": "Last 30 days",
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "net_cash_flow": round(net_flow, 2),
        "transaction_count": len(recent_txns)
    }


# Export all tools as a list for easy agent creation
ANALYST_TOOLS = [get_spending_breakdown, detect_spending_anomalies, forecast_balance, get_current_balance]
