"""
Step 4 Test: Verify Planner Agent (Budgets & Goals)
Run: python -m app.langgraph_agents.tests.test_step4_planner
"""

import os
import sys
import asyncio

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from dotenv import load_dotenv
load_dotenv()


async def test_check_budgets():
    """Test checking budget status"""
    print("=" * 50)
    print("TEST 1: Check Budget Status")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.planner_agent import run_planner
        
        print("\n📝 Query: 'What are my current budgets?'")
        print("🔄 Processing...\n")
        
        result = await run_planner(user_id=1, query="What are my current budgets? Am I over or under?")
        
        print(f"✅ Completed!")
        print(f"   Tool calls: {result['tool_calls']}")
        print(f"\n📤 Response:")
        print("-" * 40)
        print(result['response'])
        print("-" * 40)
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_set_budget():
    """Test setting a new budget"""
    print("\n" + "=" * 50)
    print("TEST 2: Set a New Budget")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.planner_agent import run_planner
        
        print("\n📝 Query: 'Set a budget of 10000 rupees for Travel this month'")
        print("🔄 Processing...\n")
        
        result = await run_planner(user_id=1, query="Set a budget of 10000 rupees for Travel this month")
        
        print(f"✅ Completed!")
        print(f"   Tool calls: {result['tool_calls']}")
        print(f"\n📤 Response:")
        print("-" * 40)
        print(result['response'])
        print("-" * 40)
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_check_goals():
    """Test checking goals status"""
    print("\n" + "=" * 50)
    print("TEST 3: Check Goals Status")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.planner_agent import run_planner
        
        print("\n📝 Query: 'Show me all my savings goals'")
        print("🔄 Processing...\n")
        
        result = await run_planner(user_id=1, query="Show me all my savings goals and how much I've saved")
        
        print(f"✅ Completed!")
        print(f"   Tool calls: {result['tool_calls']}")
        print(f"\n📤 Response:")
        print("-" * 40)
        print(result['response'])
        print("-" * 40)
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_create_goal():
    """Test creating a new goal"""
    print("\n" + "=" * 50)
    print("TEST 4: Create a New Goal")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.planner_agent import run_planner
        
        print("\n📝 Query: 'I want to save 50000 rupees for a new phone'")
        print("🔄 Processing...\n")
        
        result = await run_planner(user_id=1, query="I want to save 50000 rupees for a new phone by March 2025")
        
        print(f"✅ Completed!")
        print(f"   Tool calls: {result['tool_calls']}")
        print(f"\n📤 Response:")
        print("-" * 40)
        print(result['response'])
        print("-" * 40)
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_add_to_goal():
    """Test adding money to a goal"""
    print("\n" + "=" * 50)
    print("TEST 5: Add Money to Goal (Multi-step)")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.planner_agent import run_planner
        
        print("\n📝 Query: 'Add 5000 rupees to my MacBook Pro goal'")
        print("🔄 Processing (should call get_goals_status first to find goal_id)...\n")
        
        result = await run_planner(user_id=1, query="Add 5000 rupees to my MacBook Pro savings goal")
        
        print(f"✅ Completed!")
        print(f"   Tool calls: {result['tool_calls']}")
        print(f"\n📤 Response:")
        print("-" * 40)
        print(result['response'])
        print("-" * 40)
        
        # Check if it called get_goals_status first
        if "get_goals_status" in result['tool_calls'] and "add_to_goal" in result['tool_calls']:
            print("\n✅ Good! Agent correctly looked up goals first before adding.")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_via_supervisor():
    """Test planner through supervisor routing"""
    print("\n" + "=" * 50)
    print("TEST 6: Planner via Supervisor")
    print("=" * 50)
    
    try:
        from app.langgraph_agents.supervisor import process_query
        
        print("\n📝 Query: 'Check my budget status for this month'")
        print("🔄 Processing through supervisor...\n")
        
        result = await process_query(user_id=1, query="Check my budget status for this month")
        
        print(f"✅ Completed!")
        print(f"   Agents used: {result['agents_used']}")
        print(f"\n📤 Response:")
        print("-" * 40)
        print(result['response'][:500] + "..." if len(result['response']) > 500 else result['response'])
        print("-" * 40)
        
        if "planner" in result['agents_used']:
            print("\n✅ Correctly routed to Planner agent!")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n🚀 STEP 4 VERIFICATION: Planner Agent (Budgets & Goals)\n")
    
    if not os.environ.get("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY not found!")
        return False
    
    print(f"✅ GROQ_API_KEY found\n")
    
    results = []
    
    results.append(("Check Budgets", await test_check_budgets()))
    results.append(("Set Budget", await test_set_budget()))
    results.append(("Check Goals", await test_check_goals()))
    results.append(("Create Goal", await test_create_goal()))
    results.append(("Add to Goal", await test_add_to_goal()))
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
    
    print("\n" + ("🎉 Step 4 Complete! Planner Agent working." if all_passed else "⚠️ Some tests failed."))
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
