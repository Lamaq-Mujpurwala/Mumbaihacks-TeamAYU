"""
Planner Agent Tools
Tools for managing budgets and savings goals.
"""

from typing import Optional, Union
from datetime import datetime
from langchain_core.tools import tool

from app.core import (
    get_db_connection,
    get_user_budgets,
    save_budget,
    delete_budget,
    get_or_create_category,
    get_user_goals,
    save_goal,
    update_goal_progress,
    delete_goal,
    get_user_transactions
)


# ==================== BUDGET TOOLS ====================

@tool
def set_budget(user_id: Union[int, str], category_name: str, amount: Union[int, float, str], month: str = None) -> dict:
    """
    Set or update a monthly budget for a specific category.
    
    Args:
        user_id: The user's ID
        category_name: Name of the category (e.g., "Food & Dining", "Shopping")
        amount: Budget limit amount in INR
        month: Month in YYYY-MM format (defaults to current month)
    
    Returns:
        Dict with status and budget details
    """
    # Coerce types (Groq sometimes passes strings)
    user_id = int(user_id)
    amount = float(amount)
    
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    with get_db_connection() as conn:
        category_id = get_or_create_category(conn, user_id, category_name, "expense")
    
    budget_id = save_budget(user_id, category_id, amount, month)
    
    return {
        "status": "success",
        "message": f"Budget set for {category_name}: ₹{amount:,.2f} for {month}",
        "budget_id": budget_id,
        "category": category_name,
        "amount": amount,
        "month": month
    }


@tool
def remove_budget(user_id: Union[int, str], category_name: str, month: str = None) -> dict:
    """
    Remove/delete a budget for a specific category.
    
    Args:
        user_id: The user's ID
        category_name: Name of the category to remove budget for
        month: Month in YYYY-MM format (defaults to current month)
    
    Returns:
        Dict with status message
    """
    user_id = int(user_id)
    
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    with get_db_connection() as conn:
        category_id = get_or_create_category(conn, user_id, category_name, "expense")
    
    success = delete_budget(user_id, category_id, month)
    
    if success:
        return {
            "status": "success",
            "message": f"Budget removed for {category_name} ({month})"
        }
    else:
        return {
            "status": "not_found",
            "message": f"No budget found for {category_name} in {month}"
        }


@tool
def check_budget_status(user_id: Union[int, str], month: str = None) -> dict:
    """
    Check the status of all budgets for a month - shows spent vs limit.
    
    Args:
        user_id: The user's ID
        month: Month in YYYY-MM format (defaults to current month)
    
    Returns:
        Dict with budget analysis for each category
    """
    user_id = int(user_id)
    
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    budgets = get_user_budgets(user_id, month)
    
    if not budgets:
        return {
            "status": "no_budgets",
            "month": month,
            "message": "No budgets set for this month.",
            "categories": []
        }
    
    analysis = []
    total_budget = 0
    total_spent = 0
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for budget in budgets:
            cat_id = budget['category_id']
            limit = budget['amount_limit']
            cat_name = budget['category_name']
            cat_color = budget.get('category_color', '#888888')
            
            # Get spending for this category in this month
            cursor.execute("""
                SELECT SUM(amount) as total 
                FROM transactions 
                WHERE user_id = ? AND category_id = ? 
                AND strftime('%Y-%m', transaction_date) = ? 
                AND type IN ('DEBIT', 'expense')
            """, (user_id, cat_id, month))
            
            row = cursor.fetchone()
            spent = row['total'] if row['total'] else 0
            
            # Determine status
            percent_used = (spent / limit * 100) if limit > 0 else 0
            if spent > limit:
                status = "over_budget"
            elif percent_used > 90:
                status = "warning"
            elif percent_used > 75:
                status = "caution"
            else:
                status = "on_track"
            
            analysis.append({
                "category": cat_name,
                "color": cat_color,
                "limit": limit,
                "spent": round(spent, 2),
                "remaining": round(limit - spent, 2),
                "percent_used": round(percent_used, 1),
                "status": status
            })
            
            total_budget += limit
            total_spent += spent
    
    # Sort by percent used (highest first)
    analysis.sort(key=lambda x: x['percent_used'], reverse=True)
    
    return {
        "status": "success",
        "month": month,
        "total_budget": round(total_budget, 2),
        "total_spent": round(total_spent, 2),
        "total_remaining": round(total_budget - total_spent, 2),
        "overall_status": "over_budget" if total_spent > total_budget else "on_track",
        "categories": analysis
    }


# ==================== GOAL TOOLS ====================

@tool
def create_savings_goal(user_id: Union[int, str], name: str, target_amount: Union[int, float, str], target_date: str = None) -> dict:
    """
    Create a new savings goal.
    
    Args:
        user_id: The user's ID
        name: Name of the goal (e.g., "MacBook Pro", "Vacation Fund")
        target_amount: Target amount to save in INR
        target_date: Optional deadline in YYYY-MM-DD format
    
    Returns:
        Dict with status and goal details
    """
    user_id = int(user_id)
    target_amount = float(target_amount)
    
    goal_id = save_goal(user_id, name, target_amount, target_date)
    
    return {
        "status": "success",
        "message": f"Goal '{name}' created with target ₹{target_amount:,.2f}",
        "goal_id": goal_id,
        "name": name,
        "target_amount": target_amount,
        "target_date": target_date
    }


@tool
def add_to_goal(user_id: Union[int, str], goal_id: Union[int, str], amount: Union[int, float, str]) -> dict:
    """
    Add funds/progress to an existing savings goal.
    
    Args:
        user_id: The user's ID
        goal_id: The ID of the goal to update
        amount: Amount to add to the goal in INR
    
    Returns:
        Dict with updated goal status
    """
    user_id = int(user_id)
    goal_id = int(goal_id)
    amount = float(amount)
    
    goals = get_user_goals(user_id)
    target_goal = next((g for g in goals if g['id'] == goal_id), None)
    
    if not target_goal:
        return {
            "status": "error",
            "message": f"Goal with ID {goal_id} not found"
        }
    
    # Use incremental update
    success = update_goal_progress(user_id, goal_id, amount)
    
    if not success:
        return {"status": "error", "message": "Failed to update goal"}
    
    new_amount = target_goal['current_amount'] + amount
    percent = round(new_amount / target_goal['target_amount'] * 100, 1)
    
    return {
        "status": "success",
        "message": f"Added ₹{amount:,.2f} to '{target_goal['name']}'",
        "goal_name": target_goal['name'],
        "previous_amount": target_goal['current_amount'],
        "added": amount,
        "new_amount": new_amount,
        "target": target_goal['target_amount'],
        "percent_complete": percent
    }


@tool
def remove_goal(user_id: Union[int, str], goal_id: Union[int, str]) -> dict:
    """
    Delete a savings goal.
    
    Args:
        user_id: The user's ID
        goal_id: The ID of the goal to delete
    
    Returns:
        Dict with status message
    """
    user_id = int(user_id)
    goal_id = int(goal_id)
    
    success = delete_goal(user_id, goal_id)
    
    if success:
        return {
            "status": "success",
            "message": "Goal deleted successfully"
        }
    else:
        return {
            "status": "error",
            "message": f"Goal with ID {goal_id} not found"
        }


@tool
def get_goals_status(user_id: Union[int, str]) -> dict:
    """
    Get the status of all savings goals.
    
    Args:
        user_id: The user's ID
    
    Returns:
        Dict with all goals and their progress
    """
    user_id = int(user_id)
    
    goals = get_user_goals(user_id)
    
    if not goals:
        return {
            "status": "no_goals",
            "message": "No savings goals found. Create one to start tracking!",
            "goals": []
        }
    
    result = []
    total_target = 0
    total_saved = 0
    
    for goal in goals:
        target = goal['target_amount']
        saved = goal['current_amount']
        percent = round((saved / target * 100), 1) if target > 0 else 0
        
        # Determine status
        if percent >= 100:
            status = "completed"
        elif percent >= 75:
            status = "almost_there"
        elif percent >= 50:
            status = "halfway"
        elif percent >= 25:
            status = "in_progress"
        else:
            status = "just_started"
        
        result.append({
            "id": goal['id'],
            "name": goal['name'],
            "target": target,
            "saved": saved,
            "remaining": round(target - saved, 2),
            "percent": percent,
            "deadline": goal.get('target_date'),
            "status": status
        })
        
        total_target += target
        total_saved += saved
    
    return {
        "status": "success",
        "total_goals": len(result),
        "total_target": round(total_target, 2),
        "total_saved": round(total_saved, 2),
        "overall_percent": round((total_saved / total_target * 100), 1) if total_target > 0 else 0,
        "goals": result
    }


# Export all planner tools
PLANNER_TOOLS = [
    set_budget,
    remove_budget,
    check_budget_status,
    create_savings_goal,
    add_to_goal,
    remove_goal,
    get_goals_status
]
