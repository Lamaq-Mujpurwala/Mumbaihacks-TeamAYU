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
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_phone ON users(phone_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transaction_user_date ON transactions(user_id, transaction_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_insights_user_type ON insights_cache(user_id, insight_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_session ON conversations(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)')
        
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
        return cursor.lastrowid


# ==================== CATEGORY OPERATIONS ====================

def get_or_create_category(conn, user_id: int, name: str, cat_type: str) -> int:
    """Get or create a category, returns category_id"""
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM categories WHERE user_id = ? AND name = ? AND type = ?', 
                   (user_id, name, cat_type))
    row = cursor.fetchone()
    if row:
        return row['id']
    
    # Create new category
    cursor.execute('INSERT INTO categories (user_id, name, type) VALUES (?, ?, ?)',
                   (user_id, name, cat_type))
    return cursor.lastrowid


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


def update_goal_progress(goal_id: int, new_amount: float):
    """Update goal progress"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE goals SET current_amount = ? WHERE id = ?', (new_amount, goal_id))


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


# Initialize database on module load
init_database()
