"""
Step 1 Test: Verify state definitions and analyst tools work
Run from agentic-backend directory:
    python -m app.langgraph_agents.tests.test_step1_tools
"""

import sys
import os

# Ensure the parent directory is in path
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _root not in sys.path:
    sys.path.insert(0, _root)


def test_state_imports():
    """Test that state definitions import correctly"""
    print("=" * 50)
    print("TEST 1: State Definitions Import")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.state import (
            AgentState, 
            RouterDecision, 
            AgentResponse,
            create_initial_state,
            AGENT_DESCRIPTIONS
        )
        print("✅ All state classes imported successfully")
        
        # Test creating initial state
        state = create_initial_state(user_id=1, query="How much did I spend?")
        print(f"✅ Created initial state: user_id={state['user_id']}, query='{state['raw_query']}'")
        
        # Test RouterDecision
        decision = RouterDecision(
            agents_to_call=["analyst"],
            reasoning="User asking about spending"
        )
        print(f"✅ RouterDecision works: {decision.agents_to_call}")
        
        # Test AgentResponse
        response = AgentResponse(
            status="success",
            summary="Test summary",
            data={"test": 123}
        )
        print(f"✅ AgentResponse works: status={response.status}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_langchain_imports():
    """Test that LangChain packages are installed correctly"""
    print("\n" + "=" * 50)
    print("TEST 2: LangChain Package Imports")
    print("=" * 50)
    
    try:
        import langchain_core
        print(f"✅ langchain-core: {langchain_core.__version__}")
    except ImportError as e:
        print(f"❌ langchain-core not installed: {e}")
        return False
        
    try:
        import langgraph
        #print(f"✅ langgraph: {langgraph.__version__}")
    except ImportError as e:
        print(f"❌ langgraph not installed: {e}")
        return False
        
    try:
        from langchain_groq import ChatGroq
        print(f"✅ langchain-groq: ChatGroq available")
    except ImportError as e:
        print(f"❌ langchain-groq not installed: {e}")
        return False
    
    try:
        from langgraph.graph import StateGraph
        from langgraph.prebuilt import create_react_agent
        print(f"✅ langgraph.graph: StateGraph available")
        print(f"✅ langgraph.prebuilt: create_react_agent available")
    except ImportError as e:
        print(f"❌ langgraph imports failed: {e}")
        return False
    
    return True


def test_core_modules():
    """Test that core modules work"""
    print("\n" + "=" * 50)
    print("TEST 3: Core Modules (Database, LLM)")
    print("=" * 50)
    
    try:
        from app.core import DB_PATH, llm_client
        print(f"✅ Database path: {DB_PATH}")
        print(f"✅ LLM Client available: {llm_client.is_available()}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_analyst_tools():
    """Test analyst tools work"""
    print("\n" + "=" * 50)
    print("TEST 4: Analyst Tools")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.tools.analyst_tools import (
            get_spending_breakdown,
            detect_spending_anomalies,
            forecast_balance
        )
        print("✅ Tools imported successfully")
        
        # Tool metadata check
        print(f"\n📌 Tool: get_spending_breakdown")
        print(f"   Description: {get_spending_breakdown.description[:80]}...")
        
        print(f"\n📌 Tool: detect_spending_anomalies")
        print(f"   Description: {detect_spending_anomalies.description[:80]}...")
        
        print(f"\n📌 Tool: forecast_balance")
        print(f"   Description: {forecast_balance.description[:80]}...")
        
        # Try invoking with test user (will work if DB has data)
        print("\n🔄 Attempting to invoke tools (requires data in DB)...")
        
        try:
            result = get_spending_breakdown.invoke({"user_id": 1, "days": 30})
            print(f"✅ get_spending_breakdown: status={result.get('status')}, total={result.get('total_spent', 'N/A')}")
        except Exception as e:
            print(f"⚠️  get_spending_breakdown: {str(e)[:80]}")
        
        try:
            result = detect_spending_anomalies.invoke({"user_id": 1, "days": 30})
            print(f"✅ detect_spending_anomalies: status={result.get('status')}")
        except Exception as e:
            print(f"⚠️  detect_spending_anomalies: {str(e)[:80]}")
            
        try:
            result = forecast_balance.invoke({"user_id": 1, "days": 30})
            print(f"✅ forecast_balance: status={result.get('status')}")
        except Exception as e:
            print(f"⚠️  forecast_balance: {str(e)[:80]}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n🚀 STEP 1 VERIFICATION: Agentic Backend Setup\n")
    
    results = []
    
    # Run tests
    results.append(("State Definitions", test_state_imports()))
    results.append(("LangChain Imports", test_langchain_imports()))
    results.append(("Core Modules", test_core_modules()))
    results.append(("Analyst Tools", test_analyst_tools()))
    
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
    
    print("\n" + ("🎉 Step 1 Complete! Ready for Step 2 (Analyst Agent)." if all_passed else "⚠️ Fix errors before proceeding."))
    return all_passed


if __name__ == "__main__":
    main()
