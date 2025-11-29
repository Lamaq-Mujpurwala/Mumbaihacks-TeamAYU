"""
Transaction Agent Tools
Tools for managing manual transactions and viewing liabilities.
"""

from typing import Optional, Union
from datetime import datetime
from langchain_core.tools import tool

from app.core import (
    get_db_connection,
    get_user_transactions,
    add_manual_transaction,
    get_or_create_category,
    get_user_loans,
    get_user_credit_cards,
    update_user_balance,
    get_user_balance,
    recalculate_user_balance,
    get_user_budgets
)


@tool
def add_expense(user_id: Union[int, str], amount: Union[int, float, str], category_name: str, description: str = None, date: str = None) -> dict:
    """
    Record a manual expense/purchase.
    
    Args:
        user_id: The user's ID (number)
        amount: Amount spent in INR
        category_name: Category (e.g., "Shopping", "Electronics", "Food & Dining")
        description: Optional description of the purchase
        date: Optional date in YYYY-MM-DD format (defaults to today)
    
    Returns:
        Dict with status, transaction details, and budget impact if applicable
    """
    # Coerce types (Groq sometimes passes strings)
    user_id = int(user_id)
    amount = float(amount)
    
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    
    narration = description or f"{category_name} expense"
    
    # Use add_manual_transaction which handles everything (including category matching)
    txn_id = add_manual_transaction(user_id, amount, category_name, date, narration)
    
    # Check if this expense affects any budget
    month = date[:7]  # Extract YYYY-MM from date
    budget_impact = None
    
    budgets = get_user_budgets(user_id, month)
    if budgets:
        # Find if any budget matches this category
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Get the category_id that was used for this transaction
            category_id = get_or_create_category(conn, user_id, category_name, "expense")
            
            for budget in budgets:
                if budget['category_id'] == category_id:
                    # Calculate current spending for this budget
                    cursor.execute("""
                        SELECT COALESCE(SUM(amount), 0) as total 
                        FROM transactions 
                        WHERE user_id = ? AND category_id = ? 
                        AND strftime('%Y-%m', transaction_date) = ? 
                        AND type IN ('DEBIT', 'debit', 'expense')
                    """, (user_id, category_id, month))
                    
                    row = cursor.fetchone()
                    total_spent = row['total'] if row else 0
                    budget_limit = budget['amount_limit']
                    remaining = budget_limit - total_spent
                    percent_used = (total_spent / budget_limit * 100) if budget_limit > 0 else 0
                    
                    if total_spent > budget_limit:
                        status = "over_budget"
                    elif percent_used > 90:
                        status = "warning"
                    else:
                        status = "within_budget"
                    
                    budget_impact = {
                        "category": budget['category_name'],
                        "budget_limit": budget_limit,
                        "total_spent": round(total_spent, 2),
                        "remaining": round(remaining, 2),
                        "percent_used": round(percent_used, 1),
                        "status": status
                    }
                    break
    
    response = {
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
    
    if budget_impact:
        response["budget_impact"] = budget_impact
        if budget_impact["status"] == "over_budget":
            response["message"] += f" ⚠️ You've exceeded your {budget_impact['category']} budget by ₹{abs(budget_impact['remaining']):,.2f}!"
        elif budget_impact["status"] == "warning":
            response["message"] += f" ⚠️ You've used {budget_impact['percent_used']:.0f}% of your {budget_impact['category']} budget."
    
    return response


@tool
def add_income(user_id: Union[int, str], amount: Union[int, float, str], source: str, description: str = None, date: str = None) -> dict:
    """
    Record a manual income entry.
    
    Args:
        user_id: The user's ID (number)
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
    
    # Update user balance (CREDIT = income)
    update_user_balance(user_id, amount, 'CREDIT', date)
    
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
def get_recent_transactions(user_id: Union[int, str], limit: Union[int, str] = 10) -> dict:
    """
    Get recent transactions for the user.
    
    Args:
        user_id: The user's ID (number)
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
def get_liabilities_summary(user_id: Union[int, str]) -> dict:
    """
    Get summary of all liabilities (loans, credit cards).
    
    Args:
        user_id: The user's ID (number)
    
    Returns:
        Dict with loans and credit card details
    """
    user_id = int(user_id)
    
    loans = get_user_loans(user_id)
    credit_cards = get_user_credit_cards(user_id)
    
    total_loan_balance = sum(l['principal_amount'] for l in loans) if loans else 0
    total_credit_due = sum(cc['outstanding_amount'] for cc in credit_cards) if credit_cards else 0
    total_liabilities = total_loan_balance + total_credit_due
    
    loan_details = []
    for loan in loans:
        loan_details.append({
            "name": loan['name'],
            "principal_amount": loan['principal_amount'],
            "emi": loan['emi_amount'],
            "next_due_date": loan.get('next_due_date', 'Not set')
        })
    
    cc_details = []
    for cc in credit_cards:
        cc_details.append({
            "name": cc['card_name'],
            "limit": cc['limit_amount'],
            "outstanding": cc['outstanding_amount'],
            "available": cc['limit_amount'] - cc['outstanding_amount'],
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
def get_financial_snapshot(user_id: Union[int, str]) -> dict:
    """
    Get a quick financial snapshot - current balance, recent spending, income, and liabilities.
    
    Args:
        user_id: The user's ID (number)
    
    Returns:
        Dict with comprehensive financial snapshot including current balance
    """
    from datetime import datetime, timedelta
    
    user_id = int(user_id)
    
    # Get current balance from user_balance table
    balance_data = get_user_balance(user_id)
    
    if not balance_data:
        # Recalculate if no balance record exists
        balance_data = recalculate_user_balance(user_id)
    
    # Get transactions from last 30 days for activity summary
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    transactions = get_user_transactions(user_id, start_date=thirty_days_ago, limit=100)
    
    recent_income = sum(t['amount'] for t in transactions if t['type'] in ('CREDIT', 'credit', 'income'))
    recent_expenses = sum(t['amount'] for t in transactions if t['type'] in ('DEBIT', 'debit', 'expense'))
    recent_net_flow = recent_income - recent_expenses
    
    # Get liabilities
    loans = get_user_loans(user_id)
    credit_cards = get_user_credit_cards(user_id)
    
    total_loan_balance = sum(l['principal_amount'] for l in loans) if loans else 0
    total_credit_due = sum(cc['outstanding_amount'] for cc in credit_cards) if credit_cards else 0
    
    return {
        "status": "success",
        "current_balance": round(balance_data['current_balance'], 2),
        "all_time": {
            "total_income": round(balance_data['total_income'], 2),
            "total_expenses": round(balance_data['total_expenses'], 2)
        },
        "recent_activity": {
            "period": "Last 30 days",
            "income": round(recent_income, 2),
            "expenses": round(recent_expenses, 2),
            "net_flow": round(recent_net_flow, 2),
            "status": "positive" if recent_net_flow >= 0 else "negative"
        },
        "liabilities": {
            "total_loans": round(total_loan_balance, 2),
            "credit_card_dues": round(total_credit_due, 2),
            "total": round(total_loan_balance + total_credit_due, 2)
        },
        "transaction_count": len(transactions)
    }


# Export all transaction tools
TRANSACTION_TOOLS = [
    add_expense,
    add_income,
    get_recent_transactions,
    get_liabilities_summary,
    get_financial_snapshot
]
