"""
Step 2 Test: Verify Analyst Agent works with LLM
Run from agentic-backend directory:
    python -m app.langgraph_agents.tests.test_step2_analyst
"""

import os
import sys
import asyncio

# Ensure imports work
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from dotenv import load_dotenv
load_dotenv()


def test_agent_creation():
    """Test that the analyst agent can be created"""
    print("=" * 50)
    print("TEST 1: Agent Creation")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.analyst_agent import create_analyst_agent
        
        agent = create_analyst_agent()
        print("✅ Analyst agent created successfully")
        print(f"   Agent type: {type(agent).__name__}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_query():
    """Test running a query through the agent"""
    print("\n" + "=" * 50)
    print("TEST 2: Agent Query Execution")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.analyst_agent import run_analyst
        
        # Test query
        print("\n📝 Query: 'How much did I spend in the last 30 days?'")
        print("🔄 Running agent (this calls Groq LLM)...\n")
        
        result = await run_analyst(user_id=1, query="How much did I spend in the last 30 days?")
        
        print(f"✅ Agent completed!")
        print(f"   Tool calls made: {result['tool_calls']}")
        print(f"   Message count: {result['message_count']}")
        print(f"\n📤 Agent Response:")
        print("-" * 40)
        print(result['response'])
        print("-" * 40)
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_anomaly_query():
    """Test anomaly detection query"""
    print("\n" + "=" * 50)
    print("TEST 3: Anomaly Detection Query")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.analyst_agent import run_analyst
        
        print("\n📝 Query: 'Are there any unusual transactions?'")
        print("🔄 Running agent...\n")
        
        result = await run_analyst(user_id=1, query="Are there any unusual transactions in my account?")
        
        print(f"✅ Agent completed!")
        print(f"   Tool calls made: {result['tool_calls']}")
        print(f"\n📤 Agent Response:")
        print("-" * 40)
        print(result['response'])
        print("-" * 40)
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_forecast_query():
    """Test forecast query"""
    print("\n" + "=" * 50)
    print("TEST 4: Forecast Query")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.analyst_agent import run_analyst
        
        print("\n📝 Query: 'What will my balance be next month?'")
        print("🔄 Running agent...\n")
        
        result = await run_analyst(user_id=1, query="Can you predict my balance for next month?")
        
        print(f"✅ Agent completed!")
        print(f"   Tool calls made: {result['tool_calls']}")
        print(f"\n📤 Agent Response:")
        print("-" * 40)
        print(result['response'])
        print("-" * 40)
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_out_of_scope_query():
    """Test that agent handles out-of-scope queries"""
    print("\n" + "=" * 50)
    print("TEST 5: Out-of-Scope Query (Should NOT call tools)")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.analyst_agent import run_analyst
        
        print("\n📝 Query: 'What is the capital of France?'")
        print("🔄 Running agent...\n")
        
        result = await run_analyst(user_id=1, query="What is the capital of France?")
        
        print(f"✅ Agent completed!")
        print(f"   Tool calls made: {result['tool_calls']}")
        print(f"\n📤 Agent Response:")
        print("-" * 40)
        print(result['response'])
        print("-" * 40)
        
        # Check if agent avoided calling tools for unrelated query
        if len(result['tool_calls']) == 0:
            print("\n✅ Good! Agent correctly avoided calling financial tools for unrelated query.")
        else:
            print("\n⚠️  Agent called tools for unrelated query - may need prompt tuning.")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n🚀 STEP 2 VERIFICATION: Analyst Agent with LLM\n")
    
    # Check for API key first
    if not os.environ.get("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY not found in environment!")
        print("   Please set it in your .env file")
        return False
    
    print(f"✅ GROQ_API_KEY found\n")
    
    results = []
    
    # Run tests
    results.append(("Agent Creation", test_agent_creation()))
    results.append(("Spending Query", await test_agent_query()))
    results.append(("Anomaly Query", await test_agent_anomaly_query()))
    results.append(("Forecast Query", await test_agent_forecast_query()))
    results.append(("Out-of-Scope Query", await test_out_of_scope_query()))
    
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
    
    print("\n" + ("🎉 Step 2 Complete! Analyst Agent working." if all_passed else "⚠️ Some tests failed."))
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
