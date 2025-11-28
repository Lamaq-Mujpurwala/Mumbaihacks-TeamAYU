"""
Test: Dual Action Hypothesis
When user buys something for a goal (e.g., gaming PC parts), the system should:
1. Record it as an expense/transaction
2. Also update the goal progress positively

Run: python -m app.langgraph_agents.tests.test_dual_action
"""

import os
import sys
import asyncio

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from dotenv import load_dotenv
load_dotenv()


async def setup_gaming_goal():
    """First, ensure we have a Gaming PC goal"""
    from app.core import get_user_goals, save_goal
    
    goals = get_user_goals(1)
    gaming_goal = next((g for g in goals if "gaming" in g['name'].lower() or "pc" in g['name'].lower()), None)
    
    if not gaming_goal:
        print("📝 Creating 'Gaming PC' goal for testing...")
        goal_id = save_goal(1, "Gaming PC Build", 80000, "2025-06-30")
        print(f"   Created goal ID: {goal_id}")
    else:
        print(f"✅ Found existing goal: '{gaming_goal['name']}' (ID: {gaming_goal['id']})")
        print(f"   Current progress: ₹{gaming_goal['current_amount']:,.2f} / ₹{gaming_goal['target_amount']:,.2f}")
    
    return goals


async def test_supervisor_dual_action():
    """Test if supervisor routes to multiple agents for dual-action query"""
    print("\n" + "=" * 60)
    print("TEST: Dual Action via Supervisor")
    print("=" * 60)
    
    from app.langgraph_agents.supervisor import process_query
    from app.core import get_user_goals, get_user_transactions
    
    # ===== BEFORE STATE =====
    print("\n📊 STATE BEFORE:")
    print("-" * 40)
    
    goals_before = get_user_goals(1)
    gaming_goal_before = next((g for g in goals_before if "gaming" in g['name'].lower() or "pc" in g['name'].lower()), None)
    txns_before = get_user_transactions(1, limit=3)
    
    print("🎯 GOALS:")
    for g in goals_before:
        pct = (g['current_amount'] / g['target_amount'] * 100) if g['target_amount'] > 0 else 0
        marker = " 👈" if "gaming" in g['name'].lower() or "pc" in g['name'].lower() else ""
        print(f"   [{g['id']}] {g['name']}: ₹{g['current_amount']:,.2f} / ₹{g['target_amount']:,.2f} ({pct:.1f}%){marker}")
    
    print("\n💳 RECENT TRANSACTIONS:")
    for t in txns_before:
        desc = t.get('narration') or t.get('description') or t.get('category', 'N/A')
        print(f"   {t['transaction_date'][:10]} | {t['type']} | ₹{t['amount']:,.2f} | {str(desc)[:30]}")
    
    # ===== EXECUTE QUERY =====
    query = "I just spent 15000 rupees on a graphics card for my gaming PC build goal"
    
    print(f"\n📝 Query: '{query}'")
    print("🔄 Processing through supervisor...\n")
    print("   Expected: Should route to BOTH transaction (expense) AND planner (goal update)")
    print()
    
    result = await process_query(user_id=1, query=query)
    
    print(f"📊 Agents used: {result['agents_used']}")
    print(f"\n📤 Response:")
    print("-" * 50)
    print(result['response'])
    print("-" * 50)
    
    # ===== AFTER STATE =====
    print("\n📊 STATE AFTER:")
    print("-" * 40)
    
    goals_after = get_user_goals(1)
    gaming_goal_after = next((g for g in goals_after if "gaming" in g['name'].lower() or "pc" in g['name'].lower()), None)
    txns_after = get_user_transactions(1, limit=3)
    
    print("🎯 GOALS:")
    for g in goals_after:
        pct = (g['current_amount'] / g['target_amount'] * 100) if g['target_amount'] > 0 else 0
        marker = " 👈" if "gaming" in g['name'].lower() or "pc" in g['name'].lower() else ""
        print(f"   [{g['id']}] {g['name']}: ₹{g['current_amount']:,.2f} / ₹{g['target_amount']:,.2f} ({pct:.1f}%){marker}")
    
    print("\n💳 RECENT TRANSACTIONS:")
    for t in txns_after:
        desc = t.get('narration') or t.get('description') or t.get('category', 'N/A')
        print(f"   {t['transaction_date'][:10]} | {t['type']} | ₹{t['amount']:,.2f} | {str(desc)[:30]}")
    
    # ===== COMPARISON =====
    print("\n" + "=" * 60)
    print("📈 CHANGES DETECTED:")
    print("=" * 60)
    
    # Goal change
    if gaming_goal_before and gaming_goal_after:
        goal_diff = gaming_goal_after['current_amount'] - gaming_goal_before['current_amount']
        if goal_diff > 0:
            print(f"✅ GOAL UPDATED: '{gaming_goal_after['name']}'")
            print(f"   Before: ₹{gaming_goal_before['current_amount']:,.2f}")
            print(f"   After:  ₹{gaming_goal_after['current_amount']:,.2f}")
            print(f"   Change: +₹{goal_diff:,.2f}")
        else:
            print(f"❌ GOAL NOT UPDATED: '{gaming_goal_after['name']}' still at ₹{gaming_goal_after['current_amount']:,.2f}")
    
    # Transaction change
    new_txns = [t for t in txns_after if t not in txns_before]
    if len(txns_after) > 0 and txns_after[0]['amount'] == 15000:
        print(f"\n✅ TRANSACTION RECORDED:")
        t = txns_after[0]
        desc = t.get('narration') or t.get('description') or t.get('category', 'N/A')
        print(f"   Date: {t['transaction_date'][:10]}")
        print(f"   Amount: ₹{t['amount']:,.2f}")
        print(f"   Type: {t['type']}")
        print(f"   Description: {desc}")
    else:
        print(f"\n❌ TRANSACTION NOT RECORDED")
    
    # Analyze what happened
    agents = result['agents_used']
    
    print("\n" + "-" * 60)
    if 'transaction' in agents and 'planner' in agents:
        print("🎉 HYPOTHESIS CONFIRMED: Both transaction AND planner agents were called!")
    elif 'planner' in agents:
        print("⚠️ Only Planner was called - goal might be updated but expense not recorded")
    elif 'transaction' in agents:
        print("⚠️ Only Transaction was called - expense recorded but goal not updated")
    elif 'analyst' in agents:
        print("❌ Routed to Analyst instead - neither expense nor goal was handled")
    else:
        print(f"❓ Unexpected routing: {agents}")
    
    return result


async def test_planner_only():
    """Test planner agent directly with the purchase query"""
    print("\n" + "=" * 60)
    print("TEST: Planner Agent Direct (Goal Update Only)")
    print("=" * 60)
    
    from app.langgraph_agents.planner_agent import run_planner
    
    # First check goal status before
    from app.core import get_user_goals
    goals_before = get_user_goals(1)
    gaming_goal = next((g for g in goals_before if "gaming" in g['name'].lower() or "pc" in g['name'].lower()), None)
    
    if gaming_goal:
        print(f"\n📊 Goal BEFORE: '{gaming_goal['name']}'")
        print(f"   Progress: ₹{gaming_goal['current_amount']:,.2f} / ₹{gaming_goal['target_amount']:,.2f}")
    
    query = "I bought a graphics card for 15000 for my gaming PC goal, update my progress"
    print(f"\n📝 Query: '{query}'")
    print("🔄 Processing...\n")
    
    result = await run_planner(user_id=1, query=query)
    
    print(f"Tool calls: {result['tool_calls']}")
    print(f"\n📤 Response:")
    print("-" * 50)
    print(result['response'])
    print("-" * 50)
    
    # Check goal status after
    goals_after = get_user_goals(1)
    gaming_goal_after = next((g for g in goals_after if "gaming" in g['name'].lower() or "pc" in g['name'].lower()), None)
    
    if gaming_goal_after and gaming_goal:
        diff = gaming_goal_after['current_amount'] - gaming_goal['current_amount']
        print(f"\n📊 Goal AFTER: '{gaming_goal_after['name']}'")
        print(f"   Progress: ₹{gaming_goal_after['current_amount']:,.2f} / ₹{gaming_goal_after['target_amount']:,.2f}")
        print(f"   Change: +₹{diff:,.2f}")
        
        if diff > 0:
            print("\n✅ Goal was updated!")
        else:
            print("\n❌ Goal was NOT updated")


async def check_current_state():
    """Show current goals and recent transactions"""
    print("\n" + "=" * 60)
    print("CURRENT STATE CHECK")
    print("=" * 60)
    
    from app.core import get_user_goals, get_user_transactions
    
    print("\n📋 GOALS:")
    goals = get_user_goals(1)
    for g in goals:
        pct = (g['current_amount'] / g['target_amount'] * 100) if g['target_amount'] > 0 else 0
        print(f"   [{g['id']}] {g['name']}: ₹{g['current_amount']:,.2f} / ₹{g['target_amount']:,.2f} ({pct:.1f}%)")
    
    print("\n💳 RECENT TRANSACTIONS (last 5):")
    txns = get_user_transactions(1, limit=5)
    for t in txns:
        print(f"   {t['transaction_date'][:10]} | {t['type']} | ₹{t['amount']:,.2f} | {t.get('description', 'N/A')[:30]}")


async def main():
    print("\n🧪 DUAL ACTION HYPOTHESIS TEST")
    print("Scenario: 'I spent ₹15,000 on a graphics card for my gaming PC'")
    print("Expected: Record expense + Update goal progress")
    print("=" * 60)
    
    # Setup - ensure gaming goal exists
    await setup_gaming_goal()
    
    # Run the dual action test with before/after comparison
    await test_supervisor_dual_action()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
