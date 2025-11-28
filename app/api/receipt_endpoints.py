"""
Receipt Endpoints
Scan receipts using Vision LLM and extract transaction data.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import base64
import json
import io

from app.core.llm import llm_client
from app.core import database as db

router = APIRouter(prefix="/api/receipt", tags=["Receipt Scanning"])


# ==================== Request Models ====================

class TransactionData(BaseModel):
    merchant: str
    date: str
    amount: float
    category: str
    narration: Optional[str] = None


class SaveTransactionRequest(BaseModel):
    user_id: int
    merchant: str
    date: str
    amount: float
    category: str
    narration: Optional[str] = None


# ==================== Endpoints ====================

@router.post("/scan")
async def scan_receipt(file: UploadFile = File(...)):
    """
    Scan a receipt image and extract transaction details using GPT-4o Vision.
    
    Accepts: JPEG, PNG, WebP images
    Returns: Extracted transaction data (merchant, date, amount, category)
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # 1. Read and Process Image
        contents = await file.read()
        
        # Import PIL here to handle optional dependency gracefully
        try:
            from PIL import Image
        except ImportError:
            raise HTTPException(
                status_code=500, 
                detail="PIL (Pillow) not installed. Receipt scanning requires Pillow."
            )
        
        # Process image
        image = Image.open(io.BytesIO(contents))
        
        # Convert to RGB if RGBA (to save as JPEG)
        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')
            
        # Resize if too large (max 1024x1024 for faster processing)
        max_size = 1024
        if max(image.size) > max_size:
            image.thumbnail((max_size, max_size))
            
        # Save to buffer as JPEG
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # 2. Construct Prompt
        prompt = """
        Analyze this receipt image and extract the following details in JSON format:
        - merchant: The name of the store or merchant.
        - date: The date of transaction in YYYY-MM-DD format. If unclear, use today's date.
        - amount: The total amount paid (numeric only, no currency symbols).
        - category: Infer the category from these options: 
          Food & Dining, Groceries, Shopping, Travel, Health, Utilities, Entertainment, Electronics, Other
        - narration: A brief description (e.g., "Starbucks Coffee", "Uber Ride", "Amazon Purchase").
        
        Return ONLY the JSON object. No markdown, no explanations, no code blocks.
        Example:
        {"merchant": "Starbucks", "date": "2024-11-29", "amount": 450.00, "category": "Food & Dining", "narration": "Starbucks Coffee"}
        """
        
        # 3. Call Vision LLM
        response = llm_client.generate_vision_response(prompt, base64_image)
        
        # 4. Parse JSON
        # Clean up potential markdown code blocks
        cleaned_response = response.strip()
        if cleaned_response.startswith("```"):
            # Remove markdown code blocks
            cleaned_response = cleaned_response.replace("```json", "").replace("```", "").strip()
        
        data = json.loads(cleaned_response)
        
        # Validate required fields
        required_fields = ["merchant", "date", "amount", "category"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Ensure amount is a number
        data["amount"] = float(data["amount"])
        
        return {
            "status": "success",
            "data": data
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON Parse Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to parse LLM response: {str(e)}")
    except Exception as e:
        print(f"❌ Scan Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save")
async def save_scanned_transaction(data: SaveTransactionRequest):
    """
    Save the scanned transaction to the database.
    Call this after /scan to persist the extracted data.
    """
    try:
        # Wrap in list for store_transactions
        transactions = [{
            "date": data.date,
            "amount": data.amount,
            "type": "expense",  # Receipts are almost always expenses
            "category": data.category,
            "narration": data.narration or f"Payment to {data.merchant}",
            "mode": "Card"  # Default assumption
        }]
        
        count = db.store_transactions(data.user_id, transactions)
        
        return {
            "status": "success",
            "message": f"Transaction saved successfully",
            "transaction": {
                "merchant": data.merchant,
                "amount": data.amount,
                "category": data.category,
                "date": data.date
            }
        }
        
    except Exception as e:
        print(f"❌ Save Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan-and-save")
async def scan_and_save_receipt(
    file: UploadFile = File(...),
    user_id: int = Query(..., description="User ID to save the transaction for")
):
    """
    Convenience endpoint: Scan a receipt AND save it in one call.
    Combines /scan and /save into a single operation.
    """
    # First scan
    scan_result = await scan_receipt(file)
    
    if scan_result["status"] != "success":
        return scan_result
    
    data = scan_result["data"]
    
    # Then save
    save_request = SaveTransactionRequest(
        user_id=user_id,
        merchant=data["merchant"],
        date=data["date"],
        amount=data["amount"],
        category=data["category"],
        narration=data.get("narration")
    )
    
    save_result = await save_scanned_transaction(save_request)
    
    return {
        "status": "success",
        "message": "Receipt scanned and transaction saved",
        "extracted_data": data,
        "saved": True
    }
