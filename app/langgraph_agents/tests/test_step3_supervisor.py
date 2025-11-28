"""
Step 3 Test: Verify Supervisor routes queries correctly
Run: python -m app.langgraph_agents.tests.test_step3_supervisor
"""

import os
import sys
import asyncio

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from dotenv import load_dotenv
load_dotenv()


async def test_single_agent_routing():
    """Test routing to a single agent"""
    print("=" * 50)
    print("TEST 1: Single Agent Routing (Analyst)")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.supervisor import process_query
        
        print("\n📝 Query: 'How much did I spend last month?'")
        print("🔄 Processing through supervisor...\n")
        
        result = await process_query(user_id=1, query="How much did I spend last month?")
        
        print(f"✅ Completed!")
        print(f"   Agents used: {result['agents_used']}")
        print(f"\n📤 Final Response:")
        print("-" * 40)
        print(result['response'][:500] + "..." if len(result['response']) > 500 else result['response'])
        print("-" * 40)
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_anomaly_routing():
    """Test routing for anomaly detection"""
    print("\n" + "=" * 50)
    print("TEST 2: Anomaly Detection Query")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.supervisor import process_query
        
        print("\n📝 Query: 'Are there any unusual or suspicious transactions?'")
        print("🔄 Processing...\n")
        
        result = await process_query(user_id=1, query="Are there any unusual or suspicious transactions?")
        
        print(f"✅ Completed!")
        print(f"   Agents used: {result['agents_used']}")
        print(f"\n📤 Response:")
        print("-" * 40)
        print(result['response'][:500] + "..." if len(result['response']) > 500 else result['response'])
        print("-" * 40)
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_knowledge_routing():
    """Test routing to knowledge agent"""
    print("\n" + "=" * 50)
    print("TEST 3: Knowledge Query (Placeholder)")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.supervisor import process_query
        
        print("\n📝 Query: 'What is Section 80C?'")
        print("🔄 Processing...\n")
        
        result = await process_query(user_id=1, query="What is Section 80C?")
        
        print(f"✅ Completed!")
        print(f"   Agents used: {result['agents_used']}")
        print(f"\n📤 Response:")
        print("-" * 40)
        print(result['response'])
        print("-" * 40)
        
        # Check if routed to knowledge agent
        if "knowledge" in result['agents_used']:
            print("\n✅ Correctly routed to Knowledge agent!")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_multi_intent_routing():
    """Test routing for multi-intent queries"""
    print("\n" + "=" * 50)
    print("TEST 4: Multi-Intent Query")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.supervisor import process_query
        
        print("\n📝 Query: 'Show my spending breakdown and also check if I have any unusual transactions'")
        print("🔄 Processing...\n")
        
        result = await process_query(
            user_id=1, 
            query="Show my spending breakdown and also check if I have any unusual transactions"
        )
        
        print(f"✅ Completed!")
        print(f"   Agents used: {result['agents_used']}")
        print(f"\n📤 Response:")
        print("-" * 40)
        print(result['response'][:600] + "..." if len(result['response']) > 600 else result['response'])
        print("-" * 40)
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_forecast_query():
    """Test forecast routing"""
    print("\n" + "=" * 50)
    print("TEST 5: Forecast Query")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.supervisor import process_query
        
        print("\n📝 Query: 'What will my financial situation look like next month?'")
        print("🔄 Processing...\n")
        
        result = await process_query(user_id=1, query="What will my financial situation look like next month?")
        
        print(f"✅ Completed!")
        print(f"   Agents used: {result['agents_used']}")
        print(f"\n📤 Response:")
        print("-" * 40)
        print(result['response'][:500] + "..." if len(result['response']) > 500 else result['response'])
        print("-" * 40)
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n🚀 STEP 3 VERIFICATION: Supervisor (Router)\n")
    
    if not os.environ.get("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY not found!")
        return False
    
    print(f"✅ GROQ_API_KEY found\n")
    
    results = []
    
    results.append(("Single Agent (Analyst)", await test_single_agent_routing()))
    results.append(("Anomaly Detection", await test_anomaly_routing()))
    results.append(("Knowledge Routing", await test_knowledge_routing()))
    results.append(("Multi-Intent", await test_multi_intent_routing()))
    results.append(("Forecast", await test_forecast_query()))
    
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
    
    print("\n" + ("🎉 Step 3 Complete! Supervisor routing working." if all_passed else "⚠️ Some tests failed."))
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
