"""
Pinecone Service for RAG
Uses Pinecone's Inference API for server-side embeddings (no local models).
"""

import os
import time
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Try to import Pinecone
PINECONE_AVAILABLE = False
Pinecone = None
ServerlessSpec = None

try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    print("⚠️  Pinecone package not installed. Run: pip install pinecone")
except Exception as e:
    print(f"⚠️  Pinecone import error: {e}")


class PineconeService:
    """Service for interacting with Pinecone vector database"""
    
    def __init__(self):
        self.pc = None
        self.index = None
        self.index_name = os.environ.get("PINECONE_INDEX_NAME", "financial-guardian-rag")
        self.namespace = os.environ.get("PINECONE_NAMESPACE", "financial-guardian-main")
        
        if not PINECONE_AVAILABLE:
            print("⚠️  Pinecone not available")
            return
            
        api_key = os.environ.get("PINECONE_API_KEY")
        if not api_key:
            print("⚠️  PINECONE_API_KEY not found")
            return
            
        try:
            self.pc = Pinecone(api_key=api_key)
            self._ensure_index_exists()
            self.index = self.pc.Index(self.index_name)
            print(f"✅ Connected to Pinecone index: {self.index_name}")
        except Exception as e:
            print(f"⚠️  Pinecone connection failed: {e}")
    
    def _ensure_index_exists(self):
        """Check if index exists, create if not"""
        if not self.pc:
            return

        existing_indexes = [i.name for i in self.pc.list_indexes()]
        if self.index_name not in existing_indexes:
            print(f"⚠️  Index '{self.index_name}' not found. Creating...")
            try:
                self.pc.create_index(
                    name=self.index_name,
                    dimension=1024,  # Multilingual-e5-large uses 1024
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                print(f"✅ Created new index: {self.index_name}")
                time.sleep(10)
            except Exception as e:
                print(f"❌ Failed to create index: {str(e)}")
    
    def is_available(self) -> bool:
        return self.index is not None and self.pc is not None
    
    def generate_embeddings(self, texts: List[str], input_type: str = "passage") -> List[List[float]]:
        """Generate embeddings using Pinecone Inference API"""
        if not self.pc:
            raise RuntimeError("Pinecone client not initialized")
            
        try:
            embeddings = self.pc.inference.embed(
                model="multilingual-e5-large",
                inputs=texts,
                parameters={"input_type": input_type, "truncate": "END"}
            )
            return [e['values'] for e in embeddings]
        except Exception as e:
            print(f"❌ Pinecone Inference Error: {str(e)}")
            raise e
    
    def query(self, query_text: str, top_k: int = 3, filter: Optional[Dict] = None) -> List[Dict]:
        """
        Query Pinecone for similar documents.
        """
        if not self.is_available():
            print("❌ Pinecone index not initialized")
            return []

        try:
            # Generate query embedding via Pinecone Inference API
            embeddings = self.pc.inference.embed(
                model="multilingual-e5-large",
                inputs=[query_text],
                parameters={"input_type": "query"}
            )
            query_vector = embeddings[0]['values']
            
            # Query Pinecone
            results = self.index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True,
                filter=filter,
                namespace=self.namespace
            )
            
            # Format results
            formatted_results = []
            for match in results['matches']:
                formatted_results.append({
                    'id': match['id'],
                    'score': match['score'],
                    'text': match['metadata'].get('text', ''),
                    'metadata': {k:v for k,v in match['metadata'].items() if k != 'text'}
                })
                
            return formatted_results
            
        except Exception as e:
            print(f"❌ Query failed: {str(e)}")
            return []
    
    def upsert_documents(self, documents: List[Dict[str, Any]], batch_size: int = 50) -> int:
        """
        Upsert documents to Pinecone.
        documents: List of dicts containing 'id', 'text', 'metadata'
        """
        if not self.is_available():
            print("❌ Pinecone index not initialized")
            return 0

        total_docs = len(documents)
        print(f"📤 Upserting {total_docs} documents to Pinecone...")
        
        for i in range(0, total_docs, batch_size):
            batch = documents[i:i+batch_size]
            texts = [doc['text'] for doc in batch]
            
            try:
                embeddings = self.generate_embeddings(texts)
            except Exception as e:
                print(f"❌ Embedding generation failed for batch {i}: {str(e)}")
                continue
            
            vectors = []
            for j, doc in enumerate(batch):
                metadata = doc.get('metadata', {}).copy()
                metadata['text'] = doc['text']
                
                vectors.append({
                    "id": str(doc['id']),
                    "values": embeddings[j],
                    "metadata": metadata
                })
            
            try:
                self.index.upsert(vectors=vectors, namespace=self.namespace)
                print(f"   ✅ Upserted batch {i//batch_size + 1} ({len(batch)} docs)")
            except Exception as e:
                print(f"❌ Upsert failed for batch {i}: {str(e)}")
        
        print("✅ Upload complete")
        return total_docs

    def delete_all(self):
        """Delete all vectors in the index"""
        if not self.is_available():
            return
        try:
            self.index.delete(delete_all=True, namespace=self.namespace)
            print("🗑️  Deleted all vectors from index")
        except Exception as e:
            print(f"❌ Delete failed: {str(e)}")


# Global instance
pinecone_service = PineconeService()
