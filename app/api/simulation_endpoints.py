"""
Simulation Endpoints
Simulates Setu Account Aggregator flow for testing.
Includes OTP generation, verification, FIP discovery, and consent approval.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import time
import random
from datetime import datetime, timedelta

from app.core import database as db

router = APIRouter(prefix="/api/simulation", tags=["Simulation"])


# ==================== Request Models ====================

class OTPRequest(BaseModel):
    mobile_number: str


class OTPVerifyRequest(BaseModel):
    mobile_number: str
    otp: str


class ConsentApproveRequest(BaseModel):
    mobile_number: str
    selected_banks: List[str]


# ==================== Endpoints ====================

@router.post("/otp/generate")
async def generate_otp(req: OTPRequest):
    """
    Simulate generating an OTP for Setu AA flow.
    In production, this would send an actual SMS.
    """
    time.sleep(0.5)  # Simulate network delay
    return {
        "status": "SUCCESS", 
        "message": f"OTP sent to {req.mobile_number}",
        "mock_otp": "123456"  # For dev convenience
    }


@router.post("/otp/verify")
async def verify_otp(req: OTPVerifyRequest):
    """Simulate verifying an OTP"""
    time.sleep(0.3)
    if req.otp == "123456":
        return {"status": "SUCCESS", "message": "OTP Verified"}
    else:
        raise HTTPException(status_code=400, detail="Invalid OTP")


@router.get("/fips")
async def get_mock_fips():
    """Return list of mock FIPs (Financial Information Providers / Banks)"""
    return {
        "fips": [
            {"id": "HDFC", "name": "HDFC Bank", "logo": "https://logo.clearbit.com/hdfcbank.com"},
            {"id": "ICICI", "name": "ICICI Bank", "logo": "https://logo.clearbit.com/icicibank.com"},
            {"id": "SBI", "name": "State Bank of India", "logo": "https://logo.clearbit.com/sbi.co.in"},
            {"id": "AXIS", "name": "Axis Bank", "logo": "https://logo.clearbit.com/axisbank.com"},
            {"id": "KOTAK", "name": "Kotak Mahindra Bank", "logo": "https://logo.clearbit.com/kotak.com"}
        ]
    }


@router.post("/consent/approve")
async def approve_consent(req: ConsentApproveRequest):
    """
    Simulate the consent approval and data fetch from Setu.
    Generates mock transaction data and stores it in the database.
    """
    try:
        print(f"🚀 Simulation: Approving consent for {req.mobile_number}")
        
        # 1. Get or create user
        user_id = db.get_user_id(req.mobile_number)
        if not user_id:
            user_id = db.create_user(req.mobile_number)
        
        # 2. Generate mock transactions
        transactions_to_store = generate_mock_transactions(
            num_banks=len(req.selected_banks) if req.selected_banks else 2,
            num_transactions=50
        )
        
        # 3. Store in database
        count = db.store_transactions(user_id, transactions_to_store)
        
        return {
            "status": "SUCCESS",
            "message": "Data fetched and stored successfully",
            "user_id": user_id,
            "accounts_linked": len(req.selected_banks) if req.selected_banks else 2,
            "transactions_fetched": count
        }
        
    except Exception as e:
        print(f"❌ Simulation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def generate_mock_transactions(num_banks: int = 2, num_transactions: int = 50) -> List[dict]:
    """Generate realistic mock transaction data"""
    
    # Categories with realistic merchants/narrations
    expense_templates = {
        "Food & Dining": [
            ("Swiggy Order", 150, 800),
            ("Zomato Delivery", 200, 1000),
            ("Starbucks Coffee", 250, 600),
            ("McDonald's", 150, 500),
            ("Domino's Pizza", 300, 800),
            ("Restaurant Bill", 500, 2500),
        ],
        "Shopping": [
            ("Amazon Purchase", 500, 5000),
            ("Flipkart Order", 400, 4000),
            ("Myntra Fashion", 800, 3000),
            ("BigBasket Groceries", 500, 3000),
            ("DMart Shopping", 1000, 5000),
        ],
        "Travel": [
            ("Uber Ride", 100, 500),
            ("Ola Auto", 50, 300),
            ("Metro Recharge", 200, 500),
            ("Rapido Bike", 50, 200),
            ("MakeMyTrip Booking", 2000, 15000),
        ],
        "Utilities": [
            ("Electricity Bill", 500, 3000),
            ("WiFi Bill", 500, 1500),
            ("Mobile Recharge", 200, 1000),
            ("Gas Bill", 300, 1000),
        ],
        "Entertainment": [
            ("Netflix Subscription", 199, 649),
            ("Spotify Premium", 119, 179),
            ("PVR Movie Tickets", 300, 1000),
            ("Disney+ Hotstar", 149, 299),
        ],
        "Health": [
            ("Apollo Pharmacy", 100, 1500),
            ("Doctor Consultation", 500, 2000),
            ("Gym Membership", 1000, 3000),
        ],
    }
    
    income_templates = [
        ("Monthly Salary - TechCorp", 50000, 150000),
        ("Freelance Payment", 5000, 30000),
        ("Interest Credit", 100, 1000),
        ("Cashback Received", 50, 500),
    ]
    
    transactions = []
    start_date = datetime.now() - timedelta(days=90)
    
    # Generate income transactions (monthly salary)
    for month_offset in range(3):
        salary_date = start_date + timedelta(days=month_offset * 30 + 1)
        transactions.append({
            "date": salary_date.strftime("%Y-%m-%d"),
            "amount": random.randint(70000, 100000),
            "type": "income",
            "category": "Salary",
            "narration": "Monthly Salary - TechCorp",
            "mode": "NEFT"
        })
    
    # Generate expense transactions
    for _ in range(num_transactions):
        # Random date in last 90 days
        day_offset = random.randint(0, 90)
        txn_date = (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        
        # Random category
        category = random.choice(list(expense_templates.keys()))
        template = random.choice(expense_templates[category])
        narration, min_amt, max_amt = template
        
        transactions.append({
            "date": txn_date,
            "amount": random.randint(min_amt, max_amt),
            "type": "expense",
            "category": category,
            "narration": narration,
            "mode": random.choice(["UPI", "Card", "NEFT"])
        })
    
    # Sort by date
    transactions.sort(key=lambda x: x['date'])
    
    return transactions
