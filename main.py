# main.py
import asyncio
import json
import sys
from datetime import datetime
from graph.argus_graph import argus_app, ArgusState

sys.stdout.reconfigure(encoding='utf-8')

async def run_argus(user_input: str) -> dict:
    initial_state = ArgusState(
        user_input=user_input,
        agent_0={}, agent_1={}, agent_2={}, agent_4={},
        agent_7={}, agent_5={}, agent_8={},
        status="RUNNING",
        graph_data={}
    )
    result = await argus_app.ainvoke(initial_state)
    return result

def print_result(result: dict):
    status = result.get("status", "UNKNOWN")
    print(f"\n{'='*60}")
    print(f"ARGUS - Status: {status}")
    print(f"{'='*60}")
    a0 = result.get("agent_0", {})
    if a0.get("status") == "REJECT":
        print(f"\n[REJECTED] {a0.get('reason', '')}")
        print(f"   Specificity: {a0.get('specificity_score', 0)}")
        return
    print(f"   Input: {result.get('user_input', '')}")
    print(f"   Corridor: {a0.get('corridor', 'N/A')}")
    print(f"   Commodity: {a0.get('commodity', 'N/A')}")
    print(f"   Economy: {a0.get('economy', 'N/A')}")
    a1 = result.get("agent_1", {})
    print(f"\n[Agent 1] Claims retrieved: {len(a1.get('claims', []))}")
    a2 = result.get("agent_2", {})
    print(f"[Agent 2] Verified: {len(a2.get('verified_claims', []))} | Flagged: {len(a2.get('flagged_claims', []))} | Quarantined: {len(a2.get('quarantined_claims', []))}")
    for c in a2.get("flagged_claims", []):
        print(f"   [FLAGGED] {c.get('reason', '')}")
    a4 = result.get("agent_4", {})
    print(f"\n[Agent 4] Risk Score: {a4.get('risk_score', 'N/A')} ({a4.get('risk_level', 'N/A')})")
    a7 = result.get("agent_7", {})
    print(f"[Agent 7] Status: {a7.get('status', 'N/A')} | Variance: {a7.get('variance', 'N/A')}")
    if a7.get("status") == "HALTED":
        print(f"   [HALTED] SYSTEM HALTED - Human review required")
    a5 = result.get("agent_5", {})
    if a5.get("narrative"):
        print(f"\n[Agent 5] Narrative:")
        for line in a5["narrative"].split("\n"):
            print(f"   {line.strip()}")
    a8 = result.get("agent_8", {})
    if a8.get("answers"):
        print(f"\n[Agent 8] ERASER: {a8.get('eraser_status', 'N/A')}")
        for k, v in a8.get("answers", {}).items():
            print(f"   {k}: {v[:100]}...")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
    else:
        user_input = "Iran-Israel conflict, Strait of Hormuz, crude oil, India"
    print(f"ARGUS — Agentic Resilience Gateway & Unified Scrutiny")
    print(f"Running analysis for: {user_input}")
    result = asyncio.run(run_argus(user_input))
    print_result(result)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"argus_output_{timestamp}.json", "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nFull output saved to argus_output_{timestamp}.json")
