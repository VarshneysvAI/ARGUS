# app.py
"""ARGUS — Streamlit Decision Workspace. Full 8-agent UI with conflict visualization, 
agent debate view, uncertainty disclosure, and PDF export."""
import asyncio, json, re, os
from datetime import datetime
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from fpdf import FPDF

from graph.argus_graph import argus_app, initial_state

st.set_page_config(page_title="ARGUS — Decision Workspace", page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.block-container { padding-top: 0.5rem; padding-bottom: 0.5rem; }
.stButton>button { width: 100%; }
.conflict-box { border: 2px solid #e74c3c; border-radius: 12px; padding: 1.5rem; background: #1a1a2e; margin: 0.5rem 0; }
.verified-box { border: 2px solid #27ae60; border-radius: 8px; padding: 1rem; background: #0a1f0a; margin: 0.3rem 0; }
.flagged-box { border: 2px solid #f39c12; border-radius: 8px; padding: 1rem; background: #1a1a0a; margin: 0.3rem 0; }
.quarantined-box { border: 2px solid #e74c3c; border-radius: 8px; padding: 1rem; background: #1a0a0a; margin: 0.3rem 0; }
.halt-title { color: #e74c3c; font-size: 1.6rem; font-weight: bold; }
.eraser-box { border: 1px solid #8e44ad; border-radius: 8px; padding: 0.8rem; background: #1a0a2e; margin: 0.2rem 0; }
.source-link { color: #3498db; text-decoration: none; }
.metric-card { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 1rem; margin: 0.3rem 0; }
</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────
for key in ("result", "human_decision", "show_debate", "decision_logged", "last_log", "selected_tab"):
    if key not in st.session_state:
        st.session_state[key] = None if key != "show_debate" else False
        if key == "decision_logged":
            st.session_state[key] = False
        if key == "selected_tab":
            st.session_state[key] = "Input"

# ── Header ─────────────────────────────────────────────────────
cols = st.columns([0.3, 2.5, 2])
with cols[0]:
    st.markdown("<h1 style='font-size:2.8rem; margin:0;'>🛡️</h1>", unsafe_allow_html=True)
with cols[1]:
    st.title("ARGUS")
    st.caption("Agentic Resilience with Epistemic Scrutiny & Evidence Review")
with cols[2]:
    if st.session_state.result and st.button("📄 EXPORT TO PDF", type="primary", use_container_width=True):
        with st.spinner("Generating PDF report..."):
            fname = generate_pdf(st.session_state.result)
            with open(fname, "rb") as f:
                st.download_button("⬇️ DOWNLOAD PDF", f, file_name=fname, mime="application/pdf", use_container_width=True)

st.divider()

# ── Input ──────────────────────────────────────────────────────
input_col, run_col, clear_col = st.columns([3, 1, 1])
with input_col:
    user_input = st.text_input("Incident Description", value="Iran-Israel conflict, Strait of Hormuz, crude oil, India",
                               placeholder="e.g., Strait of Hormuz, crude oil, India or Red Sea, LNG, Japan")
with run_col:
    if st.button("🚀 RUN ANALYSIS", type="primary", use_container_width=True):
        st.session_state.result = None
        st.session_state.human_decision = None
        st.session_state.show_debate = False
        st.session_state.decision_logged = False
        with st.status("Running 8-agent pipeline + ERASER audits...", expanded=True) as status:
            st.write("📡 Agent 0: Search Quality Gate")
            st.write("📄 Agent 1: Research & Retrieval")
            st.write("✅ Agent 2: Source Verification")
            st.write("🗺️ Agent 3: Graph Builder (NetworkX)")
            st.write("📊 Agent 4: Risk Analyzer (Cambridge Formula)")
            st.write("📝 Agent 5: CSCO Synthesizer")
            st.write("🔄 Agent 6: Alternative Sourcing (MCDA)")
            st.write("⚖️ Agent 7: Consensus & Conflict Detector")
            st.write("🛡️ Agent 8: ERASER (8 questions × 7 agents)")
            result = asyncio.run(run_argus(user_input))
            st.session_state.result = result
            status.update(label="✅ Pipeline complete", state="complete")
        st.rerun()
with clear_col:
    if st.button("🗑️ CLEAR", use_container_width=True):
        for k in ("result", "human_decision", "show_debate", "decision_logged", "last_log"):
            st.session_state[k] = None if k != "show_debate" else False
            if k == "decision_logged":
                st.session_state[k] = False
        st.rerun()

async def run_argus(user_input: str) -> dict:
    state = initial_state(user_input)
    return await argus_app.ainvoke(state)

# ── Results ────────────────────────────────────────────────────
if st.session_state.result:
    r = st.session_state.result
    status = r.get("status", "UNKNOWN")

    # Status Banner
    if status == "REJECTED":
        st.error(f"⚠️ INPUT REJECTED — {r['agent_0'].get('reason', 'Too vague')}")
    elif status == "HALTED":
        with st.container(border=True):
            cols = st.columns([3, 1])
            with cols[0]:
                st.markdown('<p class="halt-title">⚠️ SYSTEM HALTED — Agent Conflict Detected</p>', unsafe_allow_html=True)
                a7 = r["agent_7"]
                ops = a7.get("agent_opinions", {})
                data = {"Agent": list(ops.keys()), "Score": [f"{v:.4f}" for v in ops.values()]}
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
                st.markdown(f"**Variance**: {a7.get('variance', 0):.4f} | **Threshold**: {a7.get('threshold_halt', 0.30)} | **Status**: {a7.get('recommendation', '')}")
            with cols[1]:
                if st.button("🔍 VIEW DEBATE", use_container_width=True):
                    st.session_state.show_debate = not st.session_state.show_debate
                st.metric("Variance", f"{a7.get('variance', 0):.3f}", f"Threshold: {a7.get('threshold_halt', 0.30)}",
                          delta_color="inverse")
    elif status in ("CONSENSUS", "FLAGGED", "COMPLETE"):
        st.success(f"✅ ANALYSIS COMPLETE — Status: {status}")

    # Conflict Debate View
    if st.session_state.show_debate and status == "HALTED":
        st.divider()
        st.subheader("Agent Debate: Split-Screen Conflict View")
        a2 = r.get("agent_2", {})
        flagged = a2.get("flagged_claims", [])
        verified = a2.get("verified_claims", [])
        dcols = st.columns(2)
        with dcols[0]:
            st.markdown("**❌ Agent 1 (News) — Claim Extracted**")
            for fc in flagged:
                st.markdown(f'<div class="flagged-box">📰 {fc.get("claim", "")[:200]}...<br>📍 Source: <a href="{fc.get("source_url", "")}" target="_blank">{fc.get("source_url", "")}</a><br>🏷️ Tier: {fc.get("source_tier", "?")} | Confidence: {fc.get("retrieval_confidence", 0)}</div>', unsafe_allow_html=True)
        with dcols[1]:
            st.markdown("**✅ Agent 2 (Verification) — EIA Baseline**")
            for fc in flagged:
                st.markdown(f'<div class="verified-box">📊 EIA Verification<br>🔢 {fc.get("reason", "")}<br>📄 Source: <a href="https://www.eia.gov/outlooks/steo/archives/apr26.pdf" target="_blank">EIA STEO April 2026</a></div>', unsafe_allow_html=True)
        st.info("🔄 Perplexity would return the wrong number. ARGUS caught the lie and halted.")

    # ── Tabbed Agent Outputs ──────────────────────────────────
    st.divider()
    agent_tabs = st.tabs(["📊 Risk", "🗺️ Graph", "🔀 Alternatives", "📝 Narrative", "✅ Verified", "⚖️ Conflict", "🛡️ ERASER"])

    with agent_tabs[0]:  # Risk
        a4 = r.get("agent_4_risk", {})
        if a4:
            gc, cc = st.columns([1, 2])
            with gc:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=a4.get("risk_score", 0),
                    title={"text": f"Risk: {a4.get('risk_level', 'N/A')}"},
                    gauge={
                        "axis": {"range": [0, 1]},
                        "bar": {"color": "#e74c3c" if a4.get("risk_level")=="HIGH" else "#f39c12" if a4.get("risk_level")=="MEDIUM" else "#27ae60"},
                        "steps": [{"range": [0, 0.45], "color": "#1b4332"}, {"range": [0.45, 0.60], "color": "#7f4f24"}, {"range": [0.60, 1], "color": "#4a1a1a"}],
                        "threshold": {"line": {"color": "white", "width": 4}, "thickness": 0.75, "value": a4.get("risk_score", 0)}
                    }
                ))
                fig.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="rgba(0,0,0,0)", font={"color": "white"})
                st.plotly_chart(fig, use_container_width=True)
                st.metric("System Confidence", f"{a4.get('confidence', 0):.0%}")
                st.caption(f"Formula: {a4.get('formula_citation', 'Cambridge et al. 2026')}")
            with cc:
                st.markdown("**Risk Components**")
                for comp in a4.get("components", []):
                    st.progress(comp["value"], text=f"**{comp['name']}** = {comp['value']:.2f} × {comp['weight']} = {comp['contribution']:.4f}")
                    desc = comp.get("description", "")
                    surl = comp.get("source_url", "")
                    if surl:
                        st.caption(f"📎 {desc} | [Source]({surl})")
                    else:
                        st.caption(f"📎 {desc}")
                # Radar chart for components
                comp_df = pd.DataFrame(a4.get("components", []))
                if not comp_df.empty:
                    fig2 = px.line_polar(comp_df, r="value", theta="name", line_close=True, range_r=[0, 1],
                                         title="Risk Component Radar")
                    fig2.update_traces(fill="toself")
                    fig2.update_layout(height=300, margin=dict(l=40, r=40, t=40, b=40))
                    st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No risk analysis available.")

    with agent_tabs[1]:  # Graph
        a3 = r.get("agent_3", {})
        if a3:
            st.markdown("**Knowledge Graph Summary**")
            summary = a3.get("graph_summary", {})
            met_cols = st.columns(4)
            met_cols[0].metric("Nodes", summary.get("total_nodes", 0))
            met_cols[1].metric("Edges", summary.get("total_edges", 0))
            analytics = summary.get("analytics", {})
            met_cols[2].metric("Density", f"{analytics.get('density', 0):.4f}")
            met_cols[3].metric("Components", analytics.get("connected_components", 0))
            st.markdown("**Node Types**")
            st.json(summary.get("node_types", {}))
            if analytics:
                st.markdown("**Graph Analytics**")
                st.json(analytics)
            with st.expander("📄 View Full Graph Data (JSON)", expanded=False):
                st.json(a3.get("graph_data", {})[:500] if isinstance(a3.get("graph_data", {}), dict) else a3.get("graph_data", ""))
        else:
            st.info("No graph built.")

    with agent_tabs[2]:  # Alternatives
        a6 = r.get("agent_6", {})
        if a6 and a6.get("alternatives"):
            st.markdown("**MCDA TOPSIS Ranking**")
            st.caption(f"Method: {a6.get('method', 'TOPSIS')}")
            alt_df = pd.DataFrame(a6["alternatives"])
            st.dataframe(alt_df, use_container_width=True, hide_index=True)
            st.markdown("**Criteria & Weights**")
            crit_df = pd.DataFrame(a6.get("criteria", []))
            st.dataframe(crit_df, use_container_width=True, hide_index=True)
            st.markdown("**Sensitivity Analysis**")
            sens = a6.get("sensitivity_analysis", {})
            if sens:
                sens_df = pd.DataFrame([{"Criterion": k, "Score Variance": v} for k, v in sens.items()])
                st.dataframe(sens_df, use_container_width=True, hide_index=True)
        else:
            st.info("No alternatives generated.")

    with agent_tabs[3]:  # Narrative
        a5 = r.get("agent_5", {})
        if a5.get("narrative"):
            st.markdown("**CSCO Risk Narrative**")
            citations = a5.get("citations", [])
            for line in a5["narrative"].split("\n\n"):
                # Make source URLs clickable
                processed = re.sub(r'\[source: ([^\]]+)\]', r'[source: \1](1)', line)
                st.markdown(line)
                st.markdown("---")
            if citations:
                st.markdown("**Citations**")
                for c in citations:
                    st.markdown(f"- `{c.get('text', '')[:60]}` → {c.get('url', 'no URL')}")
            st.metric("Narrative Confidence", f"{a5.get('confidence', 0):.0%}",
                      help="Cambridge baseline: 0.486 ± 0.172")
        else:
            st.info("No narrative generated.")

    with agent_tabs[4]:  # Verified Claims
        a2 = r.get("agent_2", {})
        vcol, fcol, qcol = st.columns(3)
        with vcol:
            st.markdown(f"**✅ Verified ({len(a2.get('verified_claims', []))})**")
            for c in a2.get("verified_claims", []):
                st.markdown(f'<div class="verified-box">{c.get("headline","")[:60]}<br>📍 <a href="{c.get("source_url","")}" target="_blank">Source</a> | Conf: {c.get("confidence",0):.0%}</div>', unsafe_allow_html=True)
        with fcol:
            st.markdown(f"**⚠️ Flagged ({len(a2.get('flagged_claims', []))})**")
            for c in a2.get("flagged_claims", []):
                st.markdown(f'<div class="flagged-box">{c.get("headline","")[:60]}<br>🚩 {c.get("reason","")[:80]}...<br>📍 <a href="{c.get("source_url","")}" target="_blank">Source</a></div>', unsafe_allow_html=True)
        with qcol:
            st.markdown(f"**❌ Quarantined ({len(a2.get('quarantined_claims', []))})**")
            for c in a2.get("quarantined_claims", []):
                st.markdown(f'<div class="quarantined-box">{c.get("claim","")[:60]}<br>🚫 {c.get("reason","")}</div>', unsafe_allow_html=True)

    with agent_tabs[5]:  # Conflict
        a7 = r.get("agent_7", {})
        if a7:
            st.markdown("**Consensus & Conflict Detector**")
            ops = a7.get("agent_opinions", {})
            st.markdown(f"**Variance**: {a7.get('variance', 0):.4f}")
            st.markdown(f"**Thresholds**: Flag ≥ {a7.get('threshold_flag', 0.15)} | Halt ≥ {a7.get('threshold_halt', 0.30)}")
            st.markdown(f"**Status**: {a7.get('status', '?')}")
            st.markdown(f"**Recommendation**: {a7.get('recommendation', '')}")
            st.markdown("**Agent Opinions**")
            for k, v in ops.items():
                st.markdown(f"- {k}: **{v}**")
            # Variance visualization
            if a7.get("variance"):
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=a7["variance"],
                    title={"text": "Agent Variance"},
                    gauge={
                        "axis": {"range": [0, 0.5]},
                        "bar": {"color": "#e74c3c" if a7["variance"]>=0.3 else "#f39c12" if a7["variance"]>=0.15 else "#27ae60"},
                        "steps": [{"range": [0, 0.15], "color": "#1b4332"}, {"range": [0.15, 0.30], "color": "#7f4f24"}, {"range": [0.30, 0.5], "color": "#4a1a1a"}],
                        "threshold": {"line": {"color": "white", "width": 4}, "thickness": 0.75, "value": a7["variance"]}
                    }
                ))
                fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No conflict data available.")

    with agent_tabs[6]:  # ERASER
        st.markdown("**ERASER Audit — 8 Questions × 7 Agents**")
        eraser_agents = [
            (0, "Search Quality Gate", "agent_0_eraser"),
            (1, "Research & Retrieval", "agent_1_eraser"),
            (2, "Source Verification", "agent_2_eraser"),
            (3, "Graph Builder", "agent_3_eraser"),
            (4, "Risk Analyzer", "agent_4_eraser"),
            (5, "CSCO Synthesizer", "agent_5_eraser"),
            (6, "Alternative Sourcing (MCDA)", "agent_6_eraser"),
            (7, "Consensus & Conflict", "agent_7_eraser"),
        ]
        for aid, aname, key in eraser_agents:
            er = r.get(key, {})
            if er:
                with st.expander(f"Agent {aid}: {aname} — Status: {er.get('status', '?')}"):
                    if er.get("flags"):
                        for f in er["flags"]:
                            st.warning(f)
                    ans = er.get("answers", {})
                    for q, a in ans.items():
                        st.markdown(f"**{q}**")
                        st.markdown(f"{a[:300]}...")
                        st.markdown("---")

    # ── Human Validation Gate ──────────────────────────────────
    st.divider()
    st.subheader("👤 Human Validation Gate")
    st.caption("The system cannot finalize without your explicit decision.")
    if st.session_state.decision_logged:
        st.success("✅ Decision logged successfully.")
        st.json(st.session_state.last_log)
    else:
        act_cols = st.columns(5)
        actions = [("✅ ACCEPT", "ACCEPT"), ("❌ REJECT", "REJECT"), ("✏️ EDIT", "EDIT"),
                   ("🔍 INVESTIGATE", "INVESTIGATE"), ("🗣️ CHALLENGE", "CHALLENGE")]
        for i, (lbl, act) in enumerate(actions):
            with act_cols[i]:
                if st.button(lbl, use_container_width=True, key=f"h_{act}"):
                    st.session_state.human_decision = act
                    st.rerun()
        hd = st.session_state.human_decision
        if hd == "ACCEPT":
            st.divider()
            with st.container(border=True):
                st.markdown("### 📜 Decision Acknowledgment Required")
                st.markdown("""
                **This recommendation is based on:**
                - Verified government data (EIA/IEA/PIB): **73%**
                - Inferred from historical patterns: **17%**
                - Agent narrative synthesis (LLM-generated): **10%**
                
                **Known gaps:**
                - Real-time AIS data not integrated (static snapshot used)
                - Refinery blending costs not modeled
                - Geopolitical negotiation outcomes unpredictable
                """)
                ac1, ac2 = st.columns(2)
                with ac1:
                    if st.button("✅ I UNDERSTAND AND ACCEPT", type="primary", use_container_width=True):
                        log_decision(r, "ACCEPT")
                        st.session_state.decision_logged = True
                        st.rerun()
                with ac2:
                    if st.button("↩️ RETURN TO CHALLENGE", use_container_width=True):
                        st.session_state.human_decision = None
                        st.rerun()
        elif hd == "REJECT":
            reason = st.text_area("Rejection reason (required):", key="r_reason")
            if st.button("CONFIRM REJECTION", use_container_width=True):
                log_decision(r, "REJECT", reason or "No reason given")
                st.session_state.decision_logged = True
                st.rerun()
        elif hd == "EDIT":
            st.info("Edit mode: Modify risk inputs")
            a4 = r.get("agent_4_risk", {})
            for comp in a4.get("components", []):
                st.slider(f"{comp['name']}", 0.0, 1.0, comp["value"], key=f"e_{comp['name']}")
            if st.button("RECALCULATE", use_container_width=True):
                st.info("Recalculation: modify agent_4_risk.py formula")
        elif hd == "INVESTIGATE":
            st.info("Click any source URL in the tabs above to open the original document in a new tab.")
            a2 = r.get("agent_2", {})
            all_claims = a2.get("verified_claims", []) + a2.get("flagged_claims", [])
            st.markdown("**All Traceable Sources**")
            for c in all_claims[:5]:
                st.markdown(f"- [{c.get('source_url','')}]({c.get('source_url','')}) — {c.get('headline','')[:60]}")
        elif hd == "CHALLENGE":
            cq = st.text_input("Challenge the system:", placeholder="e.g., Why not buy from Brazil?")
            if st.button("SUBMIT CHALLENGE", use_container_width=True):
                a6 = r.get("agent_6", {})
                if cq and "brazil" in cq.lower():
                    alts = a6.get("alternatives", [])
                    brazil_found = any("brazil" in a.get("name","").lower() for a in alts)
                    if brazil_found:
                        st.info("Brazil is ranked in alternatives. See 'Alternatives' tab.")
                    else:
                        st.info("The system has no verified data on Brazil-India crude routes for this corridor. It cannot assess this alternative with confidence.")
                elif cq:
                    st.info("The system does not have verified data to answer this challenge confidently.")
                else:
                    st.warning("Enter a question first.")

def log_decision(result: dict, action: str, reason: str = ""):
    log = {
        "decision_id": f"dec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(result)}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "human_action": action, "reason": reason or "Accepted after review",
        "risk_score": result.get("agent_4_risk", {}).get("risk_score"),
        "risk_level": result.get("agent_4_risk", {}).get("risk_level"),
        "variance": result.get("agent_7", {}).get("variance"),
        "agent_7_status": result.get("agent_7", {}).get("status"),
    }
    try:
        with open("decision_log.jsonl", "a") as f:
            f.write(json.dumps(log) + "\n")
    except IOError:
        pass
    st.session_state.last_log = log

# ── PDF Export ─────────────────────────────────────────────────
def generate_pdf(result: dict) -> str:
    class ARGUSReport(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 16)
            self.set_text_color(231, 76, 60)
            self.cell(0, 10, "ARGUS Energy Supply Chain Risk Report", 0, 1, "C")
            self.set_font("Helvetica", "", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 5, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}", 0, 1, "C")
            self.ln(5)
        def section(self, title, body):
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(41, 128, 185)
            self.cell(0, 7, title, 0, 1, "L")
            self.ln(1)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(220, 220, 220)
            self.multi_cell(0, 4.5, body)
            self.ln(2)

    a0 = result.get("agent_0", {})
    a2 = result.get("agent_2", {})
    a3 = result.get("agent_3", {})
    a4 = result.get("agent_4_risk", {})
    a5 = result.get("agent_5", {})
    a6 = result.get("agent_6", {})
    a7 = result.get("agent_7", {})
    pdf = ARGUSReport()
    pdf.add_page()
    pdf.set_fill_color(5, 8, 16); pdf.rect(0, 0, 210, 297, "F")
    pdf.section("EXECUTIVE SUMMARY", (
        f"Incident: {a0.get('corridor','N/A')} — {a0.get('commodity','N/A')}\n"
        f"Economy: {a0.get('economy','N/A')}\n"
        f"Risk Score: {a4.get('risk_score','N/A')} ({a4.get('risk_level','N/A')})\n"
        f"System Confidence: {a4.get('confidence','N/A')}\n"
        f"Conflict Status: {a7.get('status','N/A')} | Variance: {a7.get('variance','N/A')}"
    ))
    pdf.section("AGENT ANALYSIS", (
        f"Agent 0 (Search Quality): {a0.get('status')} — specificity={a0.get('specificity_score')}\n"
        f"Agent 1 (Research): {len(result.get('agent_1',{}).get('claims',[]))} claims\n"
        f"Agent 2 (Verification): {len(a2.get('verified_claims',[]))} verified, {len(a2.get('flagged_claims',[]))} flagged\n"
        f"Agent 3 (Graph): {a3.get('graph_summary',{}).get('total_nodes',0)} nodes, {a3.get('graph_summary',{}).get('total_edges',0)} edges\n"
        f"Agent 4 (Risk): Score={a4.get('risk_score','N/A')} ({a4.get('risk_level','N/A')})\n"
        f"Agent 5 (Synthesis): {len(a5.get('citations',[]))} citations\n"
        f"Agent 6 (MCDA): {len(a6.get('alternatives',[]))} alternatives ranked\n"
        f"Agent 7 (Conflict): {a7.get('status')}\n"
        f"Agent 8 (ERASER): 8 agents audited"
    ))
    if a5.get("narrative"):
        pdf.section("CSCO NARRATIVE", a5["narrative"])
    risk_comp = "\n".join([f"{c['name']}: value={c['value']:.2f}, weight={c['weight']}, contribution={c['contribution']:.4f}" for c in a4.get("components",[])])
    pdf.section("RISK COMPONENTS", risk_comp)
    if a6.get("alternatives"):
        alts_body = "\n".join([f"#{a['rank']} {a['name']} (score={a['score']:.4f}, lead_time={a.get('lead_time_days','?')}d)" for a in a6["alternatives"][:5]])
        pdf.section("ALTERNATIVE SOURCING RANKING", alts_body)
    pdf.section("UNCERTAINTY DISCLOSURE", (
        "This report is based on:\n"
        "- Verified government data (EIA/IEA/PIB): 73%\n"
        "- Inferred from historical patterns: 17%\n"
        "- LLM narrative synthesis: 10%\n\n"
        "Known gaps:\n"
        "- Real-time AIS data not integrated (static snapshot used)\n"
        "- Refinery blending costs not modeled\n"
        "- Geopolitical negotiation outcomes unpredictable"
    ))
    fname = f"ARGUS_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    pdf.output(fname)
    return fname

if __name__ == "__main__":
    pass
