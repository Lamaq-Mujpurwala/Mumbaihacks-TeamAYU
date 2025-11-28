"""
Analyst Agent Tools
READ-ONLY tools for analyzing transaction data.
"""

from typing import Optional
from langchain_core.tools import tool

from app.agents.analytics import analytics


@tool
def get_spending_breakdown(user_id: int, days: int = 30, category: Optional[str] = None) -> dict:
    """
    Get spending breakdown by category for the last N days.
    
    Args:
        user_id: The user's ID
        days: Number of days to analyze (default 30)
        category: Optional specific category to filter by
    
    Returns:
        Dict with total_spent, categories breakdown, and insights
    """
    return analytics.analyze_spending_patterns(user_id, days, category)


@tool
def detect_spending_anomalies(user_id: int, days: int = 30) -> dict:
    """
    Detect unusual or high-value transactions in the specified period.
    
    Args:
        user_id: The user's ID
        days: Number of days to analyze (default 30)
    
    Returns:
        Dict with anomalies list and insights about unusual spending
    """
    return analytics.detect_anomalies(user_id, days)


@tool
def forecast_balance(user_id: int, days: int = 30) -> dict:
    """
    Predict future balance based on spending and income trends.
    
    Args:
        user_id: The user's ID  
        days: Number of historical days to base forecast on (default 30)
    
    Returns:
        Dict with projected_balance and trend analysis
    """
    return analytics.forecast_cash_flow(user_id, days)


# Export all tools as a list for easy agent creation
ANALYST_TOOLS = [get_spending_breakdown, detect_spending_anomalies, forecast_balance]
