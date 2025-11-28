"""
Pinecone Service for RAG
Ported from financial-guardian-backend/app/core/pinecone_service.py
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Try to import Pinecone (handle both old and new package names)
PINECONE_AVAILABLE = False
Pinecone = None

try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    pass
except Exception:
    # Handle the case where pinecone-client is installed but deprecated
    pass

if not PINECONE_AVAILABLE:
    print("⚠️  Pinecone not available. RAG features will be limited.")


class PineconeService:
    """Service for interacting with Pinecone vector database"""
    
    def __init__(self):
        self.client = None
        self.index = None
        self.index_name = os.environ.get("PINECONE_INDEX_NAME", "financial-knowledge")
        
        if not PINECONE_AVAILABLE:
            print("⚠️  Pinecone not available")
            return
            
        api_key = os.environ.get("PINECONE_API_KEY")
        if not api_key:
            print("⚠️  PINECONE_API_KEY not found")
            return
            
        try:
            self.client = Pinecone(api_key=api_key)
            self.index = self.client.Index(self.index_name)
            print(f"✅ Connected to Pinecone index: {self.index_name}")
        except Exception as e:
            print(f"⚠️  Pinecone connection failed: {e}")
    
    def is_available(self) -> bool:
        return self.index is not None
    
    def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Query the vector database"""
        if not self.is_available():
            return []
            
        try:
            # For now, return empty - need embeddings to query
            # In production, you'd embed the query and search
            return []
        except Exception as e:
            print(f"❌ Pinecone query error: {e}")
            return []


# Global instance
pinecone_service = PineconeService()
