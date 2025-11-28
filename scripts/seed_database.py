"""
Database Seeding Script for Agentic Backend
Populates the database with realistic financial data for testing.

Run: python -m scripts.seed_database
"""
import sys
import os
import random
from datetime import datetime, timedelta

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core import database as db


def seed_data():
    print("🌱 Starting Database Seeding...")
    
    # 1. Reset Database
    if os.path.exists(db.DB_PATH):
        try:
            os.remove(db.DB_PATH)
            print("🗑️  Deleted old database")
        except Exception as e:
            print(f"⚠️  Could not delete old database: {e}")
    
    db.init_database()
    
    # 2. Create User
    phone = "9876543210"
    user_id = db.create_user(phone)
    print(f"✅ User Created: ID {user_id} ({phone})")
    
    # 3. Create Categories with colors/icons
    categories = {
        "Salary": {"type": "income", "color": "#10B981", "icon": "💰"},
        "Freelance": {"type": "income", "color": "#34D399", "icon": "💻"},
        "Food & Dining": {"type": "expense", "color": "#EF4444", "icon": "🍔"},
        "Groceries": {"type": "expense", "color": "#F87171", "icon": "🛒"},
        "Travel": {"type": "expense", "color": "#3B82F6", "icon": "✈️"},
        "Commute": {"type": "expense", "color": "#60A5FA", "icon": "🚕"},
        "Rent": {"type": "expense", "color": "#8B5CF6", "icon": "🏠"},
        "Utilities": {"type": "expense", "color": "#A78BFA", "icon": "💡"},
        "Shopping": {"type": "expense", "color": "#EC4899", "icon": "🛍️"},
        "Entertainment": {"type": "expense", "color": "#F472B6", "icon": "🎬"},
        "Health": {"type": "expense", "color": "#14B8A6", "icon": "🏥"},
    }
    
    cat_ids = {}
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        for name, meta in categories.items():
            cursor.execute(
                'INSERT INTO categories (user_id, name, type, color, icon) VALUES (?, ?, ?, ?, ?)',
                (user_id, name, meta['type'], meta['color'], meta['icon'])
            )
            cat_ids[name] = cursor.lastrowid
    print(f"✅ Categories Created: {len(cat_ids)}")

    # 4. Generate Transactions (Last 3 Months)
    transactions = []
    start_date = datetime.now() - timedelta(days=90)
    
    # Recurring Monthly Items
    for i in range(3):
        month_date = start_date + timedelta(days=i*30)
        
        # Salary (income)
        transactions.append({
            "date": month_date.replace(day=1).strftime("%Y-%m-%d"),
            "amount": 85000,
            "type": "income",
            "category": "Salary",
            "narration": "Monthly Salary - TechCorp",
            "mode": "NEFT"
        })
        
        # Freelance income (occasional)
        if i % 2 == 0:
            transactions.append({
                "date": month_date.replace(day=15).strftime("%Y-%m-%d"),
                "amount": random.randint(10000, 25000),
                "type": "income",
                "category": "Freelance",
                "narration": "Freelance Project Payment",
                "mode": "UPI"
            })
        
        # Rent
        transactions.append({
            "date": month_date.replace(day=5).strftime("%Y-%m-%d"),
            "amount": 25000,
            "type": "expense",
            "category": "Rent",
            "narration": "Apartment Rent - June 2024",
            "mode": "UPI"
        })
        
        # Utilities
        transactions.append({
            "date": month_date.replace(day=10).strftime("%Y-%m-%d"),
            "amount": random.randint(1500, 3000),
            "type": "expense",
            "category": "Utilities",
            "narration": "Electricity & WiFi Bill",
            "mode": "UPI"
        })

    # Random Daily Expenses (60 transactions)
    expense_categories = ["Food & Dining", "Groceries", "Commute", "Shopping", "Entertainment", "Health"]
    narrations = {
        "Food & Dining": ["Zomato Order", "Starbucks Coffee", "Lunch at Office Cafe", "Dinner with Friends", "Swiggy Delivery"],
        "Groceries": ["BigBasket Order", "DMart Shopping", "Zepto Quick Commerce", "Nature's Basket"],
        "Commute": ["Uber Ride", "Ola Auto", "Metro Card Recharge", "Rapido Bike"],
        "Shopping": ["Amazon Purchase", "Flipkart Order", "Myntra Fashion", "Croma Electronics"],
        "Entertainment": ["Netflix Subscription", "Movie Tickets - PVR", "Spotify Premium", "Gaming Purchase"],
        "Health": ["Apollo Pharmacy", "Doctor Consultation", "Gym Membership", "Health Checkup"]
    }
    
    amounts = {
        "Food & Dining": (150, 1500),
        "Groceries": (500, 4000),
        "Commute": (50, 500),
        "Shopping": (500, 8000),
        "Entertainment": (200, 1500),
        "Health": (200, 3000)
    }
    
    for _ in range(80):
        day_offset = random.randint(0, 90)
        txn_date = (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        
        cat_name = random.choice(expense_categories)
        amount_range = amounts[cat_name]
        
        transactions.append({
            "date": txn_date,
            "amount": random.randint(amount_range[0], amount_range[1]),
            "type": "expense",
            "category": cat_name,
            "narration": random.choice(narrations[cat_name]),
            "mode": random.choice(["UPI", "Card", "UPI"])
        })
    
    # Add a few anomalies (unusually high transactions)
    anomaly_dates = [
        (start_date + timedelta(days=20)).strftime("%Y-%m-%d"),
        (start_date + timedelta(days=50)).strftime("%Y-%m-%d"),
        (start_date + timedelta(days=75)).strftime("%Y-%m-%d"),
    ]
    
    transactions.append({
        "date": anomaly_dates[0],
        "amount": 45000,
        "type": "expense",
        "category": "Shopping",
        "narration": "iPhone Purchase - Apple Store",
        "mode": "Card"
    })
    
    transactions.append({
        "date": anomaly_dates[1],
        "amount": 35000,
        "type": "expense",
        "category": "Travel",
        "narration": "Flight Tickets - Goa Trip",
        "mode": "Card"
    })
    
    transactions.append({
        "date": anomaly_dates[2],
        "amount": 12000,
        "type": "expense",
        "category": "Health",
        "narration": "Annual Health Checkup Package",
        "mode": "Card"
    })
    
    # Sort by date
    transactions.sort(key=lambda x: x['date'])
    
    # Store transactions
    count = db.store_transactions(user_id, transactions)
    print(f"✅ Transactions Created: {count}")

    # 5. Set Budgets (Current Month)
    current_month = datetime.now().strftime("%Y-%m")
    db.save_budget(user_id, cat_ids["Food & Dining"], 8000, current_month)
    db.save_budget(user_id, cat_ids["Shopping"], 5000, current_month)
    db.save_budget(user_id, cat_ids["Entertainment"], 3000, current_month)
    db.save_budget(user_id, cat_ids["Commute"], 2000, current_month)
    print("✅ Budgets Set for current month")

    # 6. Create Goals
    goal1_id = db.save_goal(user_id, "MacBook Pro", 200000, (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d"))
    db.update_goal_progress(user_id, goal1_id, 45000)
    
    goal2_id = db.save_goal(user_id, "Bali Trip", 100000, (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"))
    db.update_goal_progress(user_id, goal2_id, 15000)
    
    goal3_id = db.save_goal(user_id, "Emergency Fund", 500000, None)
    db.update_goal_progress(user_id, goal3_id, 125000)
    print("✅ Goals Created: 3")

    # 7. Create Liabilities
    db.create_loan(user_id, "HDFC Home Loan", 4500000, 35000, (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d"))
    db.create_credit_card(user_id, "Amex Platinum", 500000, 28000, (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"))
    db.create_credit_card(user_id, "HDFC Regalia", 300000, 12000, (datetime.now() + timedelta(days=12)).strftime("%Y-%m-%d"))
    print("✅ Liabilities Added: 1 Loan, 2 Credit Cards")
    
    # Summary
    print("\n" + "=" * 50)
    print("🎉 DATABASE SEEDED SUCCESSFULLY!")
    print("=" * 50)
    print(f"   User ID: {user_id}")
    print(f"   Phone: {phone}")
    print(f"   Transactions: {count}")
    print(f"   Database: {db.DB_PATH}")
    print("=" * 50)


if __name__ == "__main__":
    seed_data()
