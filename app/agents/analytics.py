"""
Financial Analytics Engine
Analyzes transaction data and returns structured insights.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import statistics
from pydantic import BaseModel, Field
from typing import Literal

from app.core import get_user_transactions


# ==================== PYDANTIC SCHEMAS ====================

class Insight(BaseModel):
    type: Literal["trend", "anomaly", "alert", "recommendation"]
    severity: Literal["low", "medium", "high"]
    message: str
    metadata: dict = Field(default_factory=dict)


class SpendingCategory(BaseModel):
    category: str
    amount: float
    percentage: float
    transaction_count: int


class SpendingAnalysisResponse(BaseModel):
    status: Literal["success", "no_data", "error"]
    total_spent: float
    period: str
    categories: List[SpendingCategory]
    insights: List[Insight] = Field(default_factory=list)


class AnomalyResponse(BaseModel):
    status: Literal["success", "no_data", "insufficient_data", "error"]
    anomalies_detected: int
    anomalies: List[dict]
    insights: List[Insight] = Field(default_factory=list)


# ==================== ANALYTICS ENGINE ====================

class FinancialAnalytics:
    """Financial Analyst Agent Logic"""
    
    def analyze_spending_patterns(self, user_id: int, days: int = 30, category: Optional[str] = None) -> Dict[str, Any]:
        """Analyze user spending patterns and return structured response."""
        start_date = (datetime.now() - timedelta(days=days)).date().isoformat()
        transactions = get_user_transactions(user_id, start_date=start_date)
        
        # Filter only debits
        debits = [t for t in transactions if t['type'] in ['DEBIT', 'debit'] and t['amount'] > 0]
        
        # Filter by category if provided
        if category:
            debits = [t for t in debits if t.get('category', '').lower() == category.lower()]
        
        if not debits:
            return SpendingAnalysisResponse(
                status="no_data",
                total_spent=0.0,
                period=f"last_{days}_days",
                categories=[],
                insights=[Insight(
                    type="alert",
                    severity="low",
                    message="No spending data found for this period."
                )]
            ).model_dump()
        
        # Category breakdown
        category_spending = defaultdict(float)
        category_counts = defaultdict(int)
        
        for txn in debits:
            cat = txn.get('category', 'Uncategorized') or 'Uncategorized'
            category_spending[cat] += txn['amount']
            category_counts[cat] += 1
        
        total_spent = sum(category_spending.values())
        
        # Build Category Objects
        categories_list = []
        for cat, amount in category_spending.items():
            percentage = round((amount / total_spent * 100), 2) if total_spent > 0 else 0
            categories_list.append(SpendingCategory(
                category=cat,
                amount=round(amount, 2),
                percentage=percentage,
                transaction_count=category_counts[cat]
            ))
            
        # Sort by amount desc
        categories_list.sort(key=lambda x: x.amount, reverse=True)
        
        # Generate Insights
        insights = []
        if total_spent > 0:
            top_cat = categories_list[0]
            if top_cat.percentage > 40:
                insights.append(Insight(
                    type="trend",
                    severity="medium",
                    message=f"High spending in {top_cat.category} ({top_cat.percentage}% of total).",
                    metadata={"category": top_cat.category, "percentage": top_cat.percentage}
                ))

        return SpendingAnalysisResponse(
            status="success",
            total_spent=round(total_spent, 2),
            period=f"last_{days}_days",
            categories=categories_list,
            insights=insights
        ).model_dump()

    def detect_anomalies(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Detect unusual spending spikes."""
        start_date = (datetime.now() - timedelta(days=days)).date().isoformat()
        transactions = get_user_transactions(user_id, start_date=start_date)
        
        if not transactions:
            return AnomalyResponse(
                status="no_data",
                anomalies_detected=0,
                anomalies=[],
                insights=[Insight(
                    type="alert",
                    severity="low",
                    message="No transaction data found for anomaly detection in this period."
                )]
            ).model_dump()
        
        debits = [t for t in transactions if t['type'] in ['DEBIT', 'debit'] and t['amount'] > 0]
        
        if len(debits) < 5:
            return AnomalyResponse(
                status="insufficient_data",
                anomalies_detected=0,
                anomalies=[],
                insights=[]
            ).model_dump()
        
        amounts = [t['amount'] for t in debits]
        mean_amount = statistics.mean(amounts)
        stdev_amount = statistics.stdev(amounts) if len(amounts) > 1 else 0
        
        # Threshold: Mean + 2 * StdDev
        threshold = mean_amount + (2 * stdev_amount)
        anomalies_found = [t for t in debits if t['amount'] > threshold]
        
        formatted_anomalies = []
        for txn in anomalies_found:
            formatted_anomalies.append({
                "date": txn['transaction_date'],
                "amount": txn['amount'],
                "category": txn.get('category', 'Uncategorized'),
                "narration": txn.get('narration', '')
            })
            
        insights = []
        if formatted_anomalies:
            insights.append(Insight(
                type="anomaly",
                severity="high" if len(formatted_anomalies) > 2 else "medium",
                message=f"Detected {len(formatted_anomalies)} unusual transactions above ₹{int(threshold)}.",
                metadata={"threshold": threshold, "count": len(formatted_anomalies)}
            ))
            
        return AnomalyResponse(
            status="success",
            anomalies_detected=len(formatted_anomalies),
            anomalies=formatted_anomalies,
            insights=insights
        ).model_dump()

    def forecast_cash_flow(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Predict end-of-month balance (Simple Projection)."""
        start_date = (datetime.now() - timedelta(days=days)).date().isoformat()
        transactions = get_user_transactions(user_id, start_date=start_date)
        
        if not transactions:
            return {"status": "no_data", "projected_balance": 0, "message": "No transaction data found."}

        debits = [t['amount'] for t in transactions if t['type'] in ['DEBIT', 'debit']]
        credits = [t['amount'] for t in transactions if t['type'] in ['CREDIT', 'credit']]
        
        total_debits = sum(debits)
        total_credits = sum(credits)
        
        daily_avg_expense = total_debits / days if days > 0 else 0
        daily_avg_income = total_credits / days if days > 0 else 0
        
        # Forecast for next 30 days
        projected_expenses = daily_avg_expense * 30
        projected_income = daily_avg_income * 30
        projected_net = projected_income - projected_expenses
        
        return {
            "status": "success",
            "period_analyzed": f"last_{days}_days",
            "total_income": round(total_credits, 2),
            "total_expenses": round(total_debits, 2),
            "daily_avg_income": round(daily_avg_income, 2),
            "daily_avg_expense": round(daily_avg_expense, 2),
            "projected_30day_income": round(projected_income, 2),
            "projected_30day_expenses": round(projected_expenses, 2),
            "projected_net": round(projected_net, 2),
            "trend": "positive" if projected_net > 0 else "negative"
        }


# Global instance
analytics = FinancialAnalytics()
