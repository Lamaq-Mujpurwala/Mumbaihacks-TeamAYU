"""
End-to-End Test Suite - Core Agent Tests
Tests all agents and FastAPI structure.

Run with: python -m app.langgraph_agents.tests.test_end_to_end
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from dotenv import load_dotenv
load_dotenv()


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(name: str, success: bool, details: str = ""):
    symbol = "[OK]" if success else "[X]"
    print(f"  {symbol} {name}")
    if details:
        print(f"      -> {details[:120]}{'...' if len(details) > 120 else ''}")


async def test_database():
    """Test database CRUD operations"""
    print_header("TEST 1: Database Operations")
    
    from app.core import database as db, init_database
    
    results = []
    init_database()
    print_result("Database init", True)
    results.append(True)
    
    user_id = db.get_or_create_user("test_e2e_user")
    print_result("User CRUD", True, f"user_id={user_id}")
    results.append(True)
    
    goal_id = db.save_goal(user_id, "Test Goal", 50000.0, None)
    success = db.update_goal_progress(user_id, goal_id, 5000.0)
    print_result("Goal CRUD + Progress", success)
    results.append(success)
    
    from datetime import datetime
    with db.get_db_connection() as conn:
        cat_id = db.get_or_create_category(conn, user_id, "TestCat", "expense")
    budget_id = db.save_budget(user_id, cat_id, 10000.0, datetime.now().strftime("%Y-%m"))
    print_result("Budget CRUD", True)
    results.append(True)
    
    txn_id = db.add_manual_transaction(user_id, 500.0, "Food", "2025-11-29", "Test expense")
    print_result("Transaction CRUD", True)
    results.append(True)
    
    return results


async def test_analyst():
    """Test Analyst Agent"""
    print_header("TEST 2: Analyst Agent")
    from app.langgraph_agents.analyst_agent import run_analyst
    
    result = await run_analyst(1, "What are my spending patterns?")
    success = result.get('response') and len(result.get('response', '')) > 20
    print_result("Spending analysis", success, result.get('response', '')[:100])
    return [success]


async def test_planner():
    """Test Planner Agent"""
    print_header("TEST 3: Planner Agent")
    from app.langgraph_agents.planner_agent import run_planner
    
    result = await run_planner(1, "Create a goal called Quick Test for 10000 rupees")
    success = result.get('response') is not None
    print_result("Goal creation", success, result.get('response', '')[:100])
    return [success]


async def test_transaction():
    """Test Transaction Agent"""
    print_header("TEST 4: Transaction Agent")
    from app.langgraph_agents.transaction_agent import run_transaction
    
    result = await run_transaction(1, "I spent 250 rupees on lunch")
    success = result.get('response') is not None
    print_result("Expense recording", success, result.get('response', '')[:100])
    return [success]


async def test_knowledge():
    """Test Knowledge Agent"""
    print_header("TEST 5: Knowledge Agent")
    from app.core.pinecone_service import pinecone_service
    
    if not pinecone_service.is_available():
        print_result("Pinecone", False, "Not available")
        return [False]
    
    from app.langgraph_agents.knowledge_agent import run_knowledge
    result = await run_knowledge(1, "What is SIP?")
    success = result.get('response') and len(result.get('response', '')) > 20
    print_result("RAG query", success, result.get('response', '')[:100])
    return [success]


async def test_supervisor():
    """Test Supervisor routing"""
    print_header("TEST 6: Supervisor Routing")
    from app.langgraph_agents.supervisor import process_query
    
    results = []
    
    result = await process_query(1, "Analyze my spending")
    success = 'analyst' in result.get('agents_used', [])
    print_result("Routes to Analyst", success, f"Agents: {result.get('agents_used')}")
    results.append(success)
    
    result = await process_query(1, "Set budget 5000 for food")
    success = 'planner' in result.get('agents_used', [])
    print_result("Routes to Planner", success, f"Agents: {result.get('agents_used')}")
    results.append(success)
    
    result = await process_query(1, "Add expense 100 for tea")
    success = 'transaction' in result.get('agents_used', [])
    print_result("Routes to Transaction", success, f"Agents: {result.get('agents_used')}")
    results.append(success)
    
    return results


async def test_dual_action():
    """Test dual-action (expense + goal update)"""
    print_header("TEST 7: Dual-Action")
    from app.langgraph_agents.supervisor import process_query
    from app.core import database as db
    
    goal_id = db.save_goal(1, "Dual Test Fund", 50000.0, None)
    db.update_goal_progress(1, goal_id, 10000.0)
    
    result = await process_query(1, "I bought a charger for 500 from my Dual Test Fund")
    agents = result.get('agents_used', [])
    has_both = 'transaction' in agents and 'planner' in agents
    print_result("Both agents called", has_both, f"Agents: {agents}")
    return [has_both]


async def test_fastapi():
    """Test FastAPI endpoints exist"""
    print_header("TEST 8: FastAPI Endpoints")
    from app.main import app
    
    routes = [r.path for r in app.routes if hasattr(r, 'path')]
    expected = ["/api/chat/message", "/api/budgets", "/api/goals", 
                "/api/transactions", "/api/snapshot", "/api/liabilities", "/health"]
    
    results = []
    for ep in expected:
        found = any(ep in r for r in routes)
        print_result(f"Endpoint {ep}", found)
        results.append(found)
    return results


async def main():
    print("\n" + "="*60)
    print("  CORE END-TO-END TESTS")
    print("="*60)
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("\n[ERROR] GROQ_API_KEY not found.")
        return
    print(f"\n[OK] GROQ_API_KEY found")
    
    all_results = {}
    
    all_results['database'] = await test_database()
    
    try: all_results['analyst'] = await test_analyst()
    except Exception as e: print_result("Analyst", False, str(e)); all_results['analyst'] = [False]
    
    try: all_results['planner'] = await test_planner()
    except Exception as e: print_result("Planner", False, str(e)); all_results['planner'] = [False]
    
    try: all_results['transaction'] = await test_transaction()
    except Exception as e: print_result("Transaction", False, str(e)); all_results['transaction'] = [False]
    
    try: all_results['knowledge'] = await test_knowledge()
    except Exception as e: print_result("Knowledge", False, str(e)); all_results['knowledge'] = [False]
    
    try: all_results['supervisor'] = await test_supervisor()
    except Exception as e: print_result("Supervisor", False, str(e)); all_results['supervisor'] = [False]
    
    try: all_results['dual_action'] = await test_dual_action()
    except Exception as e: print_result("Dual-Action", False, str(e)); all_results['dual_action'] = [False]
    
    all_results['fastapi'] = await test_fastapi()
    
    # Summary
    print_header("SUMMARY")
    total_pass, total_fail = 0, 0
    for name, res in all_results.items():
        p, f = sum(res), len(res) - sum(res)
        total_pass += p; total_fail += f
        status = "PASS" if f == 0 else "PARTIAL" if p > 0 else "FAIL"
        print(f"  {name.upper():15} {status:8} ({p}/{len(res)})")
    
    print(f"\n  TOTAL: {total_pass}/{total_pass+total_fail} ({total_pass/(total_pass+total_fail)*100:.0f}%)")


if __name__ == "__main__":
    asyncio.run(main())
