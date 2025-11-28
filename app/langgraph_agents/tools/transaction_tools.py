"""
Transaction Agent Tools
Tools for managing manual transactions and viewing liabilities.
"""

from typing import Optional
from datetime import datetime
from langchain_core.tools import tool

from app.core import (
    get_db_connection,
    get_user_transactions,
    add_manual_transaction,
    get_or_create_category,
    get_user_loans,
    get_user_credit_cards
)


@tool
def add_expense(user_id: int, amount: float, category_name: str, description: str = None, date: str = None) -> dict:
    """
    Record a manual expense/purchase.
    
    Args:
        user_id: The user's ID
        amount: Amount spent in INR
        category_name: Category (e.g., "Shopping", "Electronics", "Food & Dining")
        description: Optional description of the purchase
        date: Optional date in YYYY-MM-DD format (defaults to today)
    
    Returns:
        Dict with status and transaction details
    """
    # Coerce types (Groq sometimes passes strings)
    user_id = int(user_id)
    amount = float(amount)
    
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    
    narration = description or f"{category_name} expense"
    
    # Use add_manual_transaction which handles everything
    txn_id = add_manual_transaction(user_id, amount, category_name, date, narration)
    
    return {
        "status": "success",
        "message": f"Recorded expense: ₹{amount:,.2f} for {category_name}",
        "transaction_id": txn_id,
        "transaction": {
            "amount": amount,
            "category": category_name,
            "description": narration,
            "date": date,
            "type": "expense"
        }
    }


@tool
def add_income(user_id: int, amount: float, source: str, description: str = None, date: str = None) -> dict:
    """
    Record a manual income entry.
    
    Args:
        user_id: The user's ID
        amount: Amount received in INR
        source: Source of income (e.g., "Salary", "Freelance", "Gift")
        description: Optional description
        date: Optional date in YYYY-MM-DD format (defaults to today)
    
    Returns:
        Dict with status and transaction details
    """
    user_id = int(user_id)
    amount = float(amount)
    
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    
    narration = description or f"Income from {source}"
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        category_id = get_or_create_category(conn, user_id, source, "income")
        cursor.execute('''
            INSERT INTO transactions (user_id, category_id, transaction_date, type, amount, category, narration, source)
            VALUES (?, ?, ?, 'CREDIT', ?, ?, ?, 'MANUAL')
        ''', (user_id, category_id, date, amount, source, narration))
        txn_id = cursor.lastrowid
    
    return {
        "status": "success",
        "message": f"Recorded income: ₹{amount:,.2f} from {source}",
        "transaction_id": txn_id,
        "transaction": {
            "amount": amount,
            "source": source,
            "description": narration,
            "date": date,
            "type": "income"
        }
    }


@tool
def get_recent_transactions(user_id: int, limit: int = 10) -> dict:
    """
    Get recent transactions for the user.
    
    Args:
        user_id: The user's ID
        limit: Number of transactions to return (default 10)
    
    Returns:
        Dict with list of recent transactions
    """
    user_id = int(user_id)
    limit = int(limit)
    
    transactions = get_user_transactions(user_id, limit=limit)
    
    if not transactions:
        return {
            "status": "no_transactions",
            "message": "No transactions found.",
            "transactions": []
        }
    
    result = []
    for t in transactions:
        result.append({
            "date": t['transaction_date'][:10] if t['transaction_date'] else "Unknown",
            "type": t['type'],
            "amount": t['amount'],
            "description": t.get('description', 'N/A'),
            "category": t.get('category_name', 'Uncategorized')
        })
    
    return {
        "status": "success",
        "count": len(result),
        "transactions": result
    }


@tool
def get_liabilities_summary(user_id: int) -> dict:
    """
    Get summary of all liabilities (loans, credit cards).
    
    Args:
        user_id: The user's ID
    
    Returns:
        Dict with loans and credit card details
    """
    user_id = int(user_id)
    
    loans = get_user_loans(user_id)
    credit_cards = get_user_credit_cards(user_id)
    
    total_loan_balance = sum(l['remaining_balance'] for l in loans) if loans else 0
    total_credit_due = sum(cc['current_balance'] for cc in credit_cards) if credit_cards else 0
    total_liabilities = total_loan_balance + total_credit_due
    
    loan_details = []
    for loan in loans:
        loan_details.append({
            "type": loan['loan_type'],
            "original_amount": loan['principal_amount'],
            "remaining": loan['remaining_balance'],
            "emi": loan['emi_amount'],
            "interest_rate": loan['interest_rate']
        })
    
    cc_details = []
    for cc in credit_cards:
        cc_details.append({
            "name": cc['card_name'],
            "limit": cc['credit_limit'],
            "current_balance": cc['current_balance'],
            "available": cc['credit_limit'] - cc['current_balance'],
            "due_date": cc.get('due_date', 'Not set')
        })
    
    return {
        "status": "success",
        "total_liabilities": total_liabilities,
        "loans": {
            "count": len(loan_details),
            "total_outstanding": total_loan_balance,
            "details": loan_details
        },
        "credit_cards": {
            "count": len(cc_details),
            "total_due": total_credit_due,
            "details": cc_details
        }
    }


@tool
def get_financial_snapshot(user_id: int) -> dict:
    """
    Get a quick financial snapshot - recent spending, income, and liabilities.
    
    Args:
        user_id: The user's ID
    
    Returns:
        Dict with comprehensive financial snapshot
    """
    from datetime import datetime, timedelta
    
    # Get transactions from last 30 days
    transactions = get_user_transactions(user_id, limit=100)
    
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    recent_txns = [t for t in transactions if t['transaction_date'] >= thirty_days_ago]
    
    total_income = sum(t['amount'] for t in recent_txns if t['type'] == 'CREDIT')
    total_expenses = sum(t['amount'] for t in recent_txns if t['type'] == 'DEBIT')
    net_flow = total_income - total_expenses
    
    # Get liabilities
    loans = get_user_loans(user_id)
    credit_cards = get_user_credit_cards(user_id)
    
    total_loan_balance = sum(l['remaining_balance'] for l in loans) if loans else 0
    total_credit_due = sum(cc['current_balance'] for cc in credit_cards) if credit_cards else 0
    
    return {
        "status": "success",
        "period": "Last 30 days",
        "cash_flow": {
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "net_flow": round(net_flow, 2),
            "status": "positive" if net_flow >= 0 else "negative"
        },
        "liabilities": {
            "total_loans": round(total_loan_balance, 2),
            "credit_card_dues": round(total_credit_due, 2),
            "total": round(total_loan_balance + total_credit_due, 2)
        },
        "transaction_count": len(recent_txns)
    }


# Export all transaction tools
TRANSACTION_TOOLS = [
    add_expense,
    add_income,
    get_recent_transactions,
    get_liabilities_summary,
    get_financial_snapshot
]
