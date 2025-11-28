"""
Stress Tests & Complex Query Tests for LangGraph Multi-Agent System
Separated from main E2E tests to avoid rate limiting.

Run with: python -m app.langgraph_agents.tests.test_stress
"""

import asyncio
import os
import sys
import time

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from dotenv import load_dotenv
load_dotenv()


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_subheader(title: str):
    print(f"\n  --- {title} ---")


def print_result(name: str, success: bool, details: str = ""):
    symbol = "[OK]" if success else "[X]"
    print(f"  {symbol} {name}")
    if details:
        if len(details) > 150:
            details = details[:150] + "..."
        print(f"      -> {details}")


async def test_complex_queries():
    """Test complex, nuanced natural language queries"""
    print_header("TEST: Complex Natural Language Queries")
    
    results = []
    
    try:
        from app.langgraph_agents.supervisor import process_query
        
        complex_queries = [
            # Ambiguous intent
            ("I think I spent too much this month, should I be worried?", ['analyst']),
            
            # Multi-part question
            ("How much did I spend on food and what's my budget for it?", ['analyst']),
            
            # Informal language
            ("yo whats my cash situation looking like", ['analyst']),
            
            # Time-relative query
            ("compare my spending this week vs last week", ['analyst']),
            
            # Goal + expense combined
            ("I want to save 500 rupees by cutting my coffee budget", ['planner']),
        ]
        
        for query, expected_agents in complex_queries:
            result = await process_query(1, query)
            agents = result.get('agents_used', [])
            has_response = result.get('response') and len(result.get('response', '')) > 20
            agent_match = any(ea in agents for ea in expected_agents)
            success = has_response and agent_match
            print_result(f"'{query[:40]}...'", success, f"Agents: {agents}")
            results.append(success)
            
            # Rate limit protection
            await asyncio.sleep(1)
            
    except Exception as e:
        print_result("Complex queries", False, str(e))
        results.append(False)
    
    return results


async def test_edge_cases():
    """Test edge cases and error handling"""
    print_header("TEST: Edge Cases & Error Handling")
    
    results = []
    
    try:
        from app.langgraph_agents.supervisor import process_query
        
        # Test with non-existent user
        print_subheader("Non-existent User")
        result = await process_query(99999, "What's my balance?")
        success = result.get('response') is not None
        print_result("Handles missing user", success, result.get('response', '')[:80])
        results.append(success)
        await asyncio.sleep(1)
        
        # Test empty query
        print_subheader("Empty/Minimal Query")
        result = await process_query(1, "hi")
        success = result.get('response') is not None
        print_result("Handles minimal input", success, result.get('response', '')[:80])
        results.append(success)
        await asyncio.sleep(1)
        
        # Test query with special characters
        print_subheader("Special Characters")
        result = await process_query(1, "How much did I spend on 'food & drinks' (including snacks)?")
        success = result.get('response') is not None
        print_result("Handles special chars", success, result.get('response', '')[:80])
        results.append(success)
        await asyncio.sleep(1)
        
        # Test very long query
        print_subheader("Long Query")
        long_query = "I want to know about my spending " * 10 + "please help"
        result = await process_query(1, long_query)
        success = result.get('response') is not None
        print_result("Handles long input", success, result.get('response', '')[:80])
        results.append(success)
        await asyncio.sleep(1)
        
        # Test numeric-heavy query
        print_subheader("Numeric Query")
        result = await process_query(1, "I spent 1234.56 rupees on item costing 100, 200, 300, 400, 234.56")
        success = result.get('response') is not None
        print_result("Handles numbers", success, result.get('response', '')[:80])
        results.append(success)
        
    except Exception as e:
        print_result("Edge cases", False, str(e))
        results.append(False)
    
    return results


async def test_concurrent_requests():
    """Test handling of concurrent requests"""
    print_header("TEST: Concurrent Request Handling")
    
    results = []
    
    try:
        from app.langgraph_agents.supervisor import process_query
        
        queries = [
            (1, "What's my total spending?"),
            (1, "Show my goals"),
            (1, "What's my budget status?"),
        ]
        
        print("  Running 3 concurrent queries...")
        start_time = time.time()
        
        tasks = [process_query(uid, q) for uid, q in queries]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        elapsed = time.time() - start_time
        
        success_count = sum(1 for r in results_list if isinstance(r, dict) and r.get('response'))
        all_success = success_count == len(queries)
        
        print_result(f"All {len(queries)} requests completed", all_success, f"{success_count}/{len(queries)} succeeded in {elapsed:.2f}s")
        results.append(all_success)
        
        for i, (uid, q) in enumerate(queries):
            r = results_list[i]
            if isinstance(r, dict):
                print_result(f"  Query {i+1}", r.get('response') is not None, r.get('response', '')[:50])
            else:
                print_result(f"  Query {i+1}", False, str(r))
        
    except Exception as e:
        print_result("Concurrent handling", False, str(e))
        results.append(False)
    
    return results


async def test_multi_turn_conversation():
    """Test conversation context (simulated multi-turn)"""
    print_header("TEST: Multi-Turn Conversation Simulation")
    
    results = []
    
    try:
        from app.langgraph_agents.supervisor import process_query
        
        conversation = [
            "Create a goal called New Phone for 25000 rupees",
            "Add 5000 to my New Phone goal",
            "What's the status of my New Phone goal?",
        ]
        
        for i, query in enumerate(conversation):
            result = await process_query(1, query)
            success = result.get('response') is not None
            print_result(f"Turn {i+1}: '{query[:35]}...'", success, result.get('response', '')[:80])
            results.append(success)
            await asyncio.sleep(1)
            
    except Exception as e:
        print_result("Multi-turn conversation", False, str(e))
        results.append(False)
    
    return results


async def test_realistic_scenarios():
    """Test realistic user scenarios"""
    print_header("TEST: Realistic User Scenarios")
    
    results = []
    
    try:
        from app.langgraph_agents.supervisor import process_query
        
        scenarios = [
            {"name": "Budget Awareness", "query": "I'm trying to stick to my budget, am I overspending on anything?"},
            {"name": "Goal Progress Check", "query": "How close am I to reaching my savings goals?"},
            {"name": "Quick Expense Entry", "query": "Just paid 850 for uber rides this week"},
            {"name": "Financial Education", "query": "What's the difference between SIP and lump sum investment?"},
            {"name": "Monthly Review", "query": "Give me a summary of where my money went this month"},
        ]
        
        for scenario in scenarios:
            result = await process_query(1, scenario['query'])
            agents = result.get('agents_used', [])
            has_response = result.get('response') and len(result.get('response', '')) > 20
            print_result(f"{scenario['name']}", has_response, f"Agents: {agents}")
            results.append(has_response)
            await asyncio.sleep(1)
            
    except Exception as e:
        print_result("Realistic scenarios", False, str(e))
        results.append(False)
    
    return results


async def test_dual_action_advanced():
    """Advanced dual-action tests"""
    print_header("TEST: Advanced Dual-Action Scenarios")
    
    results = []
    
    try:
        from app.langgraph_agents.supervisor import process_query
        from app.core import database as db
        
        # Setup test goal
        goal_id = db.save_goal(1, "Stress Test Fund", 100000.0, None)
        db.update_goal_progress(1, goal_id, 50000.0)
        
        scenarios = [
            "I withdrew 2000 from my Stress Test Fund for emergency groceries",
            "Bought a book for 500 rupees, deduct from my savings goals",
            "Paid rent 15000 - this affects my monthly budget significantly",
        ]
        
        for query in scenarios:
            result = await process_query(1, query)
            agents = result.get('agents_used', [])
            has_response = result.get('response') is not None
            print_result(f"'{query[:45]}...'", has_response, f"Agents: {agents}")
            results.append(has_response)
            await asyncio.sleep(1)
            
    except Exception as e:
        print_result("Advanced dual-action", False, str(e))
        results.append(False)
    
    return results


async def main():
    """Run stress tests"""
    print("\n" + "="*60)
    print("  STRESS TEST SUITE - Complex & Edge Cases")
    print("  (Rate-limited to avoid API throttling)")
    print("="*60)
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("\n[ERROR] GROQ_API_KEY not found.")
        return
    print(f"\n[OK] GROQ_API_KEY found (length: {len(api_key)})")
    
    all_results = {}
    
    all_results['complex_queries'] = await test_complex_queries()
    all_results['edge_cases'] = await test_edge_cases()
    all_results['concurrent'] = await test_concurrent_requests()
    all_results['multi_turn'] = await test_multi_turn_conversation()
    all_results['realistic'] = await test_realistic_scenarios()
    all_results['dual_action_adv'] = await test_dual_action_advanced()
    
    # Summary
    print_header("STRESS TEST SUMMARY")
    
    total_pass = 0
    total_fail = 0
    
    for test_name, test_results in all_results.items():
        passed = sum(test_results)
        failed = len(test_results) - passed
        total_pass += passed
        total_fail += failed
        status = "PASS" if failed == 0 else "PARTIAL" if passed > 0 else "FAIL"
        print(f"  {test_name.upper():20} {status:8} ({passed}/{len(test_results)})")
    
    print(f"\n  {'='*40}")
    print(f"  TOTAL: {total_pass} passed, {total_fail} failed")
    print(f"  SUCCESS RATE: {total_pass/(total_pass+total_fail)*100:.1f}%")
    print()


if __name__ == "__main__":
    asyncio.run(main())
