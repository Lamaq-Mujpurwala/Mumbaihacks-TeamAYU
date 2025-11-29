"""
Core Module - Database, LLM, and shared services
"""

from .database import (
    get_db_connection,
    init_database,
    get_user_id,
    get_or_create_user,
    get_user_transactions,
    get_user_budgets,
    get_user_goals,
    get_user_loans,
    get_user_credit_cards,
    save_budget,
    delete_budget,
    save_goal,
    update_goal_progress,
    delete_goal,
    add_manual_transaction,
    get_or_create_category,
    find_matching_category,
    get_user_categories,
    get_cached_insight,
    save_insight,
    get_latest_financial_data,
    # User Balance functions
    get_user_balance,
    initialize_user_balance,
    update_user_balance,
    recalculate_user_balance,
    DB_PATH
)

from .llm import llm_client

from .pinecone_service import pinecone_service

__all__ = [
    # Database
    "get_db_connection",
    "init_database", 
    "get_user_id",
    "get_or_create_user",
    "get_user_transactions",
    "get_user_budgets",
    "get_user_goals",
    "get_user_loans",
    "get_user_credit_cards",
    "save_budget",
    "delete_budget",
    "save_goal",
    "update_goal_progress",
    "delete_goal",
    "add_manual_transaction",
    "get_or_create_category",
    "find_matching_category",
    "get_user_categories",
    "get_cached_insight",
    "save_insight",
    "get_latest_financial_data",
    # User Balance
    "get_user_balance",
    "initialize_user_balance",
    "update_user_balance",
    "recalculate_user_balance",
    "DB_PATH",
    # LLM
    "llm_client",
    # Pinecone
    "pinecone_service"
]
