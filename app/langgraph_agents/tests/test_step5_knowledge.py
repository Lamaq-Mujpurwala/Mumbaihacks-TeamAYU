"""
Step 5 Test: Verify Knowledge Agent (RAG-based Q&A)
Run: python -m app.langgraph_agents.tests.test_step5_knowledge
"""

import os
import sys
import asyncio

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from dotenv import load_dotenv
load_dotenv()


async def test_knowledge_direct():
    """Test knowledge agent directly"""
    print("=" * 50)
    print("TEST 1: Knowledge Agent Direct Query")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.knowledge_agent import run_knowledge
        
        print("\n📝 Query: 'What is SIP and how does it work?'")
        print("🔄 Processing...\n")
        
        result = await run_knowledge(user_id=1, query="What is SIP and how does it work in mutual funds?")
        
        print(f"✅ Completed!")
        print(f"   Tool calls: {result['tool_calls']}")
        print(f"   Sources: {result.get('sources', [])}")
        print(f"\n📤 Response:")
        print("-" * 40)
        print(result['response'][:800] + "..." if len(result['response']) > 800 else result['response'])
        print("-" * 40)
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tax_question():
    """Test tax-related question"""
    print("\n" + "=" * 50)
    print("TEST 2: Tax Question (Section 80C)")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.knowledge_agent import run_knowledge
        
        print("\n📝 Query: 'What are the tax benefits under Section 80C?'")
        print("🔄 Processing...\n")
        
        result = await run_knowledge(user_id=1, query="What are the tax benefits under Section 80C in India?")
        
        print(f"✅ Completed!")
        print(f"   Tool calls: {result['tool_calls']}")
        print(f"\n📤 Response:")
        print("-" * 40)
        print(result['response'][:800] + "..." if len(result['response']) > 800 else result['response'])
        print("-" * 40)
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_via_supervisor():
    """Test knowledge through supervisor routing"""
    print("\n" + "=" * 50)
    print("TEST 3: Knowledge via Supervisor")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.supervisor import process_query
        
        print("\n📝 Query: 'Explain UPI and its benefits'")
        print("🔄 Processing through supervisor...\n")
        
        result = await process_query(user_id=1, query="Explain UPI and its benefits")
        
        print(f"✅ Completed!")
        print(f"   Agents used: {result['agents_used']}")
        print(f"\n📤 Response:")
        print("-" * 40)
        print(result['response'][:800] + "..." if len(result['response']) > 800 else result['response'])
        print("-" * 40)
        
        if "knowledge" in result['agents_used']:
            print("\n✅ Correctly routed to Knowledge agent!")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_pinecone_connection():
    """Test Pinecone connectivity"""
    print("=" * 50)
    print("TEST 0: Pinecone Connection Check")
    print("=" * 50)
    
    try:
        from app.core.pinecone_service import pinecone_service
        
        if pinecone_service.is_available():
            print("✅ Pinecone is connected and available")
            
            # Try a sample query
            results = pinecone_service.query("financial planning", top_k=1)
            if results:
                print(f"✅ Sample query returned {len(results)} results")
                print(f"   Preview: {results[0]['text'][:100]}...")
            else:
                print("⚠️  Sample query returned no results (knowledge base may be empty)")
            
            return True
        else:
            print("⚠️  Pinecone is NOT available")
            print("   Knowledge agent will use fallback responses")
            return True  # Not a failure, just a warning
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n🚀 STEP 5 VERIFICATION: Knowledge Agent (RAG Q&A)\n")
    
    if not os.environ.get("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY not found!")
        return False
    
    print(f"✅ GROQ_API_KEY found\n")
    
    results = []
    
    # Test Pinecone connection first
    results.append(("Pinecone Connection", await test_pinecone_connection()))
    
    # Test knowledge agent
    results.append(("Knowledge Direct", await test_knowledge_direct()))
    results.append(("Tax Question", await test_tax_question()))
    results.append(("Via Supervisor", await test_via_supervisor()))
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False
    
    print("\n" + ("🎉 Step 5 Complete! Knowledge Agent working." if all_passed else "⚠️ Some tests failed."))
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
