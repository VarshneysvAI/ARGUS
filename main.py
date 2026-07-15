# main.py
"""ARGUS CLI — Full 8-agent pipeline with per-agent ERASER audit output."""
import asyncio, json, sys, uuid
from typing import Dict
from datetime import datetime
from dotenv import load_dotenv
from graph.argus_graph import argus_app, initial_state

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")

def run_argus(user_input: str) -> dict:
    session_id = str(uuid.uuid4())[:8]
    state = initial_state(user_input, session_id)
    
    print(f"\n🚀 Starting ARGUS Pipeline (Session: {session_id})")
    print("Each agent will log its completion below in real-time. Please wait...\n")
    
    current_state = state
    for event in argus_app.stream(current_state):
        for node_name, node_state in event.items():
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {node_name.upper()} completed.")
            if "eraser" in node_name and isinstance(node_state, dict) and node_name in node_state:
                print(f"    -> ERASER Audit: {node_state[node_name].get('status', 'OK')}")
            
            if isinstance(node_state, dict):
                current_state.update(node_state)
                
    return current_state

def print_divider(char="=", width=70):
    print(char * width)

def print_section(title):
    print_divider()
    print(f"  {title}")
    print_divider("-")

def print_agent_result(aid: int, name: str, output: Dict, eraser: Dict = None):
    print_section(f"Agent {aid}: {name}")
    if output.get("status") == "REJECT":
        print(f"  [REJECTED] {output.get('reason', '')}")
        return
    if aid == 0:
        print(f"  Input: {output.get('input', '')}")
        print(f"  Entities: corridor={output.get('corridor','?')}, commodity={output.get('commodity','?')}, economy={output.get('economy','?')}")
        print(f"  Specificity: {output.get('specificity_score', 0)}")
        print(f"  Queries: {output.get('generated_queries', [])[:3]}")
    elif aid == 1:
        print(f"  Documents processed: {output.get('total_documents', 0)}")
        print(f"  Claims retrieved: {len(output.get('claims', []))}")
        for c in output.get("claims", [])[:3]:
            print(f"    [{c.get('source_tier','?')}] {c.get('headline','')[:60]}... -> {c.get('source_url','')[:60]}")
        if output.get("quarantined"):
            print(f"  Quarantined: {len(output['quarantined'])} items")
    elif aid == 2:
        verified = output.get("verified_claims", [])
        flagged = output.get("flagged_claims", [])
        quarantined = output.get("quarantined_claims", [])
        print(f"  Verified: {len(verified)} | Flagged: {len(flagged)} | Quarantined: {len(quarantined)}")
        for fc in flagged:
            print(f"    [FLAGGED] {fc.get('reason', '')}")
    elif aid == 3:
        stats = output.get("stats", {})
        summary = output.get("graph_summary", {})
        print(f"  Nodes: {summary.get('total_nodes', 0)} | Edges: {summary.get('total_edges', 0)}")
        print(f"  Node types: {summary.get('node_types', {})}")
        if summary.get("analytics"):
            print(f"  Density: {summary['analytics'].get('density', 'N/A')}")
        print(f"  Persisted: {output.get('graph_persisted', 'N/A')}")
    elif aid == 4:
        print(f"  Risk Score: {output.get('risk_score', 'N/A')} ({output.get('risk_level', 'N/A')})")
        print(f"  Confidence: {output.get('confidence', 'N/A')}")
        for comp in output.get("components", []):
            print(f"    {comp['name']}: value={comp['value']}, weight={comp['weight']}, contribution={comp['contribution']}")
    elif aid == 5:
        narrative = output.get("narrative", "")
        lines = narrative.split("\n")
        print(f"  Narrative ({len(lines)} sections):")
        for line in lines[:5]:
            print(f"    {line[:120]}")
        print(f"  Citations: {len(output.get('citations', []))}")
    elif aid == 6:
        alts = output.get("alternatives", [])
        print(f"  Alternatives ranked: {len(alts)}")
        for a in alts[:3]:
            print(f"    #{a['rank']} {a['name']} (score: {a['score']:.4f})")
    elif aid == 7:
        print(f"  Status: {output.get('status', '?')} | Variance: {output.get('variance', '?')}")
        ops = output.get("agent_opinions", {})
        for k, v in ops.items():
            print(f"    {k}: {v}")
        if output.get("status") == "HALTED":
            print(f"  [HALT] {output.get('recommendation', '')}")
    if eraser:
        print(f"  ERASER: {eraser.get('status', '?')} | Flags: {len(eraser.get('flags', []))}")
        for f in eraser.get("flags", []):
            print(f"    [FLAG] {f[:80]}")

def print_result(result: dict):
    print_divider("=", 70)
    print(f"  ARGUS — Complete Analysis Report")
    print(f"  Status: {result.get('status', 'UNKNOWN')}")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_divider("=", 70)
    print()
    print_agent_result(0, "Search Quality Gate", result.get("agent_0", {}), result.get("agent_0_eraser"))
    print_agent_result(1, "Research & Retrieval", result.get("agent_1", {}), result.get("agent_1_eraser"))
    print_agent_result(2, "Source Verification", result.get("agent_2", {}), result.get("agent_2_eraser"))
    print_agent_result(3, "Graph Builder (NetworkX)", result.get("agent_3", {}), result.get("agent_3_eraser"))
    print_agent_result(4, "Risk Analyzer", result.get("agent_4_risk", {}), result.get("agent_4_eraser"))
    print_agent_result(5, "CSCO Synthesizer", result.get("agent_5", {}), result.get("agent_5_eraser"))
    print_agent_result(6, "Alternative Sourcing (MCDA)", result.get("agent_6", {}), result.get("agent_6_eraser"))
    print_agent_result(7, "Consensus & Conflict Detector", result.get("agent_7", {}), result.get("agent_7_eraser"))
    fe = result.get("agent_8_final_eraser", {})
    print_section("Final ERASER (LLM Audit)")
    if fe.get("status") == "ERROR":
        print(f"  [ERROR] {fe.get('error', 'Unknown error')}")
    elif fe.get("llm_audit"):
        print(f"  Model: {fe.get('model', 'N/A')}")
        audit_text = fe["llm_audit"]
        for line in audit_text.split("\n")[:8]:
            print(f"    {line[:120]}")
        print(f"  (... {len(audit_text.split())} words total)")
    print()
    final_status = result.get("status", "UNKNOWN")
    if final_status == "HALTED":
        print(f"  FINAL STATUS: SYSTEM HALTED - Human review required")
        print(f"  The 15M vs 9.1M Saudi shut-in discrepancy was detected and quarantined.")
    elif final_status == "REJECTED":
        print(f"  FINAL STATUS: INPUT REJECTED - {result.get('agent_0', {}).get('reason', '')}")
    elif final_status == "CONSENSUS":
        print(f"  FINAL STATUS: CONSENSUS REACHED - Awaiting human validation")
    elif final_status == "FLAGGED":
        print(f"  FINAL STATUS: FLAGGED - Human review recommended")
    elif final_status == "RUNNING":
        print(f"  FINAL STATUS: Pipeline incomplete")
    print_divider("=", 70)

if __name__ == "__main__":
    test_inputs = [
        "Iran-Israel conflict, Strait of Hormuz, crude oil, India",
        "Red Sea shipping attacks, LNG, Japan",
        "vague input",
    ]
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
    else:
        user_input = test_inputs[0]
    print(f"ARGUS v1.0 — Agentic Resilience Gateway & Unified Scrutiny")
    print(f"Running analysis for: {user_input}")
    print()
    result = run_argus(user_input)
    print_result(result)
    
    # Save for the Streamlit dashboard
    output_file = "latest_run.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"\n" + "="*70)
    print(f"✅ Full output saved to: {output_file}")
    print(f"🚀 You can now run 'streamlit run app.py' to view this data in the dashboard!")
    print("="*70 + "\n")
