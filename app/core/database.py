"""
Database models and operations for Financial Guardian
SQLite database with all necessary tables for user data, transactions, insights, and conversations
Ported from financial-guardian-backend/app/core/database.py
"""

import sqlite3
import json
from datetime import datetime, timedelta
from contextlib import contextmanager
import os

# Database file path - in agentic-backend/data/
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'financial_guardian.db')

# Ensure data directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_database():
    """Initialize database with all required tables"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Financial data table (stores raw Setu responses)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS financial_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                raw_data_json TEXT NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                color TEXT,
                icon TEXT,
                UNIQUE(user_id, name, type),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category_id INTEGER,
                transaction_date DATE NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT,
                narration TEXT,
                balance REAL,
                mode TEXT,
                reference TEXT,
                setu_txn_id TEXT,
                source TEXT DEFAULT 'SETU',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')
        
        # Budgets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                amount_limit REAL NOT NULL,
                month TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')

        # Goals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0,
                target_date DATE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # Loans table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                principal_amount REAL NOT NULL,
                emi_amount REAL NOT NULL,
                next_due_date DATE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # Credit Cards table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credit_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                card_name TEXT NOT NULL,
                limit_amount REAL NOT NULL,
                outstanding_amount REAL DEFAULT 0,
                due_date DATE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Insights cache table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS insights_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                insight_type TEXT NOT NULL,
                data_json TEXT NOT NULL,
                computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        ''')
        
        # User Balance table - stores current balance per user
        # This table is automatically updated when transactions are added
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_balance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                current_balance REAL DEFAULT 0,
                total_income REAL DEFAULT 0,
                total_expenses REAL DEFAULT 0,
                last_transaction_date DATE,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_phone ON users(phone_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transaction_user_date ON transactions(user_id, transaction_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_insights_user_type ON insights_cache(user_id, insight_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_session ON conversations(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_balance ON user_balance(user_id)')
        
        conn.commit()
        print(f"✅ Database initialized at: {DB_PATH}")


# ==================== USER OPERATIONS ====================

def get_user_id(phone_number: str) -> int:
    """Get user ID by phone number, returns None if not found"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE phone_number = ?', (phone_number,))
        row = cursor.fetchone()
        return row['id'] if row else None


def create_user(phone_number: str) -> int:
    """Create a new user and return their ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (phone_number) VALUES (?)', (phone_number,))
        return cursor.lastrowid


def get_or_create_user(phone_number: str) -> int:
    """Get existing user or create new one"""
    user_id = get_user_id(phone_number)
    if not user_id:
        user_id = create_user(phone_number)
    return user_id


# ==================== TRANSACTION OPERATIONS ====================

def get_user_transactions(user_id: int, start_date: str = None, end_date: str = None, limit: int = None):
    """Get user transactions with optional date filtering"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = 'SELECT * FROM transactions WHERE user_id = ?'
        params = [user_id]
        
        if start_date:
            query += ' AND transaction_date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND transaction_date <= ?'
            params.append(end_date)
            
        query += ' ORDER BY transaction_date DESC'
        
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
            
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def add_manual_transaction(user_id: int, amount: float, category_name: str, date: str, narration: str) -> int:
    """Add a manual transaction"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        category_id = get_or_create_category(conn, user_id, category_name, "expense")
        cursor.execute('''
            INSERT INTO transactions (user_id, category_id, transaction_date, type, amount, category, narration, source)
            VALUES (?, ?, ?, 'DEBIT', ?, ?, ?, 'MANUAL')
        ''', (user_id, category_id, date, amount, category_name, narration))
        txn_id = cursor.lastrowid
    
    # Update user balance (DEBIT = expense)
    update_user_balance(user_id, amount, 'DEBIT', date)
    
    return txn_id


# ==================== CATEGORY OPERATIONS ====================

def find_matching_category(conn, user_id: int, name: str, cat_type: str) -> int:
    """
    Find a matching category using fuzzy matching.
    Handles cases like "Commute" vs "Commuting", "Food" vs "Food & Dining".
    Returns category_id if found, None otherwise.
    """
    cursor = conn.cursor()
    name_lower = name.lower().strip()
    
    # First try exact match (case-insensitive)
    cursor.execute('''
        SELECT id, name FROM categories 
        WHERE user_id = ? AND LOWER(name) = ? AND type = ?
    ''', (user_id, name_lower, cat_type))
    row = cursor.fetchone()
    if row:
        return row['id']
    
    # Get all categories of this type for the user
    cursor.execute('''
        SELECT id, name FROM categories 
        WHERE user_id = ? AND type = ?
    ''', (user_id, cat_type))
    categories = cursor.fetchall()
    
    # Define common category aliases/variations
    category_aliases = {
        'commute': ['commuting', 'transport', 'transportation', 'travel', 'cab', 'uber', 'ola', 'auto', 'metro', 'bus'],
        'commuting': ['commute', 'transport', 'transportation', 'travel'],
        'food': ['food & dining', 'food and dining', 'dining', 'restaurant', 'eating out', 'meals'],
        'food & dining': ['food', 'dining', 'restaurant', 'eating out', 'meals', 'food and dining'],
        'shopping': ['shop', 'purchase', 'buy', 'retail'],
        'groceries': ['grocery', 'supermarket', 'vegetables', 'fruits', 'provisions'],
        'entertainment': ['movies', 'netflix', 'gaming', 'games', 'fun'],
        'health': ['healthcare', 'medical', 'medicine', 'doctor', 'hospital', 'pharmacy'],
        'utilities': ['utility', 'bills', 'electricity', 'water', 'gas', 'internet', 'wifi'],
        'rent': ['housing', 'apartment', 'flat'],
        'travel': ['trip', 'vacation', 'holiday', 'flight', 'hotel'],
    }
    
    for cat in categories:
        cat_name_lower = cat['name'].lower()
        
        # Check if input name starts with or contains the category name
        if name_lower.startswith(cat_name_lower) or cat_name_lower.startswith(name_lower):
            return cat['id']
        
        # Check if one contains the other
        if name_lower in cat_name_lower or cat_name_lower in name_lower:
            return cat['id']
        
        # Check aliases
        if cat_name_lower in category_aliases:
            if name_lower in category_aliases[cat_name_lower]:
                return cat['id']
        
        # Reverse check - if input has known aliases that match existing category
        if name_lower in category_aliases:
            if cat_name_lower in category_aliases[name_lower]:
                return cat['id']
    
    return None


def get_or_create_category(conn, user_id: int, name: str, cat_type: str) -> int:
    """Get or create a category, returns category_id. Uses fuzzy matching to find similar categories."""
    cursor = conn.cursor()
    
    # First try exact match
    cursor.execute('SELECT id FROM categories WHERE user_id = ? AND name = ? AND type = ?', 
                   (user_id, name, cat_type))
    row = cursor.fetchone()
    if row:
        return row['id']
    
    # Try fuzzy matching to find similar existing category
    matched_id = find_matching_category(conn, user_id, name, cat_type)
    if matched_id:
        return matched_id
    
    # Create new category if no match found
    cursor.execute('INSERT INTO categories (user_id, name, type) VALUES (?, ?, ?)',
                   (user_id, name, cat_type))
    return cursor.lastrowid


def get_user_categories(user_id: int, cat_type: str = None) -> list:
    """Get all categories for a user, optionally filtered by type."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if cat_type:
            cursor.execute('SELECT * FROM categories WHERE user_id = ? AND type = ?', (user_id, cat_type))
        else:
            cursor.execute('SELECT * FROM categories WHERE user_id = ?', (user_id,))
        return [dict(row) for row in cursor.fetchall()]


# ==================== BUDGET OPERATIONS ====================

def get_user_budgets(user_id: int, month: str = None):
    """Get user budgets for a specific month"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if month:
            cursor.execute('''
                SELECT b.*, c.name as category_name, c.color as category_color 
                FROM budgets b 
                JOIN categories c ON b.category_id = c.id 
                WHERE b.user_id = ? AND b.month = ?
            ''', (user_id, month))
        else:
            cursor.execute('''
                SELECT b.*, c.name as category_name, c.color as category_color 
                FROM budgets b 
                JOIN categories c ON b.category_id = c.id 
                WHERE b.user_id = ?
            ''', (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def save_budget(user_id: int, category_id: int, amount: float, month: str) -> int:
    """Save or update a budget"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Check if exists
        cursor.execute('SELECT id FROM budgets WHERE user_id = ? AND category_id = ? AND month = ?',
                       (user_id, category_id, month))
        row = cursor.fetchone()
        if row:
            cursor.execute('UPDATE budgets SET amount_limit = ? WHERE id = ?', (amount, row['id']))
            return row['id']
        else:
            cursor.execute('INSERT INTO budgets (user_id, category_id, amount_limit, month) VALUES (?, ?, ?, ?)',
                           (user_id, category_id, amount, month))
            return cursor.lastrowid


def delete_budget(user_id: int, category_id: int, month: str) -> bool:
    """Delete a budget"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM budgets WHERE user_id = ? AND category_id = ? AND month = ?',
                       (user_id, category_id, month))
        return cursor.rowcount > 0


# ==================== GOAL OPERATIONS ====================

def get_user_goals(user_id: int):
    """Get all user goals"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM goals WHERE user_id = ?', (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def save_goal(user_id: int, name: str, target_amount: float, target_date: str = None) -> int:
    """Create a new goal"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO goals (user_id, name, target_amount, target_date) VALUES (?, ?, ?, ?)',
                       (user_id, name, target_amount, target_date))
        return cursor.lastrowid


def update_goal_progress(user_id: int, goal_id: int, amount_to_add: float) -> bool:
    """Add amount to goal progress (incremental update)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Get current amount first
        cursor.execute('SELECT current_amount FROM goals WHERE id = ? AND user_id = ?', (goal_id, user_id))
        row = cursor.fetchone()
        if not row:
            return False
        new_amount = row['current_amount'] + amount_to_add
        cursor.execute('UPDATE goals SET current_amount = ? WHERE id = ? AND user_id = ?', (new_amount, goal_id, user_id))
        return cursor.rowcount > 0


def delete_goal(user_id: int, goal_id: int) -> bool:
    """Delete a goal"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM goals WHERE id = ? AND user_id = ?', (goal_id, user_id))
        return cursor.rowcount > 0


# ==================== LOAN & CREDIT CARD OPERATIONS ====================

def get_user_loans(user_id: int):
    """Get all user loans"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM loans WHERE user_id = ?', (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def create_loan(user_id: int, name: str, principal: float, emi: float, next_due: str = None) -> int:
    """Create a new loan"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO loans (user_id, name, principal_amount, emi_amount, next_due_date) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, name, principal, emi, next_due))
        return cursor.lastrowid


def get_user_credit_cards(user_id: int):
    """Get all user credit cards"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM credit_cards WHERE user_id = ?', (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def create_credit_card(user_id: int, card_name: str, limit_amount: float, outstanding: float = 0, due_date: str = None) -> int:
    """Create a new credit card entry"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO credit_cards (user_id, card_name, limit_amount, outstanding_amount, due_date) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, card_name, limit_amount, outstanding, due_date))
        return cursor.lastrowid


# ==================== BULK TRANSACTION STORAGE ====================

def store_transactions(user_id: int, transactions: list) -> int:
    """Store multiple transactions at once"""
    count = 0
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for txn in transactions:
            cat_type = "income" if txn.get('type') == 'income' else 'expense'
            category_id = get_or_create_category(conn, user_id, txn['category'], cat_type)
            
            # Map type to CREDIT/DEBIT
            txn_type = 'CREDIT' if txn.get('type') == 'income' else 'DEBIT'
            
            cursor.execute('''
                INSERT INTO transactions (user_id, category_id, transaction_date, type, amount, category, narration, mode, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'SETU')
            ''', (
                user_id, 
                category_id,
                txn['date'],
                txn_type,
                txn['amount'],
                txn['category'],
                txn.get('narration', ''),
                txn.get('mode', 'UPI')
            ))
            count += 1
    
    # Recalculate balance after bulk insert for accuracy
    recalculate_user_balance(user_id)
    
    return count


# ==================== INSIGHTS CACHE ====================

def get_cached_insight(user_id: int, insight_type: str):
    """Get cached insight if not expired"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT data_json FROM insights_cache 
            WHERE user_id = ? AND insight_type = ? AND expires_at > datetime('now')
            ORDER BY computed_at DESC LIMIT 1
        ''', (user_id, insight_type))
        row = cursor.fetchone()
        return json.loads(row['data_json']) if row else None


def save_insight(user_id: int, insight_type: str, data: dict, ttl_hours: int = 24):
    """Cache an insight"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        expires_at = (datetime.now() + timedelta(hours=ttl_hours)).isoformat()
        cursor.execute('''
            INSERT INTO insights_cache (user_id, insight_type, data_json, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, insight_type, json.dumps(data), expires_at))


# ==================== FINANCIAL DATA ====================

def get_latest_financial_data(user_id: int):
    """Get latest raw financial data"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM financial_data WHERE user_id = ? ORDER BY fetched_at DESC LIMIT 1
        ''', (user_id,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            result['raw_data'] = json.loads(result['raw_data_json'])
            return result
        return None


# ==================== USER BALANCE OPERATIONS ====================

def get_user_balance(user_id: int) -> dict:
    """
    Get the current balance for a user from the user_balance table.
    Returns a dict with current_balance, total_income, total_expenses, etc.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM user_balance WHERE user_id = ?
        ''', (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def initialize_user_balance(user_id: int, initial_balance: float = 0) -> int:
    """
    Initialize balance record for a new user.
    Creates an entry in user_balance table if it doesn't exist.
    Returns the record id.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Check if already exists
        cursor.execute('SELECT id FROM user_balance WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            return row['id']
        
        # Create new balance record
        cursor.execute('''
            INSERT INTO user_balance (user_id, current_balance, total_income, total_expenses, last_updated)
            VALUES (?, ?, 0, 0, datetime('now'))
        ''', (user_id, initial_balance))
        return cursor.lastrowid


def update_user_balance(user_id: int, amount: float, transaction_type: str, transaction_date: str = None):
    """
    Update user balance when a transaction is added.
    
    Args:
        user_id: The user's ID
        amount: Transaction amount (always positive)
        transaction_type: 'CREDIT' for income, 'DEBIT' for expense
        transaction_date: Optional date of transaction
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Ensure balance record exists
        cursor.execute('SELECT id, current_balance, total_income, total_expenses FROM user_balance WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if not row:
            # Initialize if doesn't exist
            cursor.execute('''
                INSERT INTO user_balance (user_id, current_balance, total_income, total_expenses, last_updated)
                VALUES (?, 0, 0, 0, datetime('now'))
            ''', (user_id,))
            current_balance = 0
            total_income = 0
            total_expenses = 0
        else:
            current_balance = row['current_balance']
            total_income = row['total_income']
            total_expenses = row['total_expenses']
        
        # Update based on transaction type
        if transaction_type in ('CREDIT', 'credit', 'income'):
            current_balance += amount
            total_income += amount
        else:  # DEBIT, debit, expense
            current_balance -= amount
            total_expenses += amount
        
        # Update the balance record
        cursor.execute('''
            UPDATE user_balance 
            SET current_balance = ?, 
                total_income = ?, 
                total_expenses = ?,
                last_transaction_date = ?,
                last_updated = datetime('now')
            WHERE user_id = ?
        ''', (current_balance, total_income, total_expenses, transaction_date or datetime.now().strftime("%Y-%m-%d"), user_id))


def recalculate_user_balance(user_id: int) -> dict:
    """
    Recalculate user balance from all transactions.
    Useful for fixing inconsistencies or after bulk operations.
    Returns the updated balance info.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Calculate totals from all transactions
        cursor.execute('''
            SELECT 
                COALESCE(SUM(CASE WHEN type IN ('CREDIT', 'credit', 'income') THEN amount ELSE 0 END), 0) as total_income,
                COALESCE(SUM(CASE WHEN type IN ('DEBIT', 'debit', 'expense') THEN amount ELSE 0 END), 0) as total_expenses,
                MAX(transaction_date) as last_date
            FROM transactions 
            WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        total_income = row['total_income'] or 0
        total_expenses = row['total_expenses'] or 0
        last_date = row['last_date']
        current_balance = total_income - total_expenses
        
        # Update or insert balance record
        cursor.execute('SELECT id FROM user_balance WHERE user_id = ?', (user_id,))
        exists = cursor.fetchone()
        
        if exists:
            cursor.execute('''
                UPDATE user_balance 
                SET current_balance = ?, 
                    total_income = ?, 
                    total_expenses = ?,
                    last_transaction_date = ?,
                    last_updated = datetime('now')
                WHERE user_id = ?
            ''', (current_balance, total_income, total_expenses, last_date, user_id))
        else:
            cursor.execute('''
                INSERT INTO user_balance (user_id, current_balance, total_income, total_expenses, last_transaction_date, last_updated)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            ''', (user_id, current_balance, total_income, total_expenses, last_date))
        
        return {
            'user_id': user_id,
            'current_balance': current_balance,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'last_transaction_date': last_date
        }


# Initialize database on module load
init_database()
