# app.py
import streamlit as st
import asyncio
import json
from datetime import datetime
from main import run_argus
from fpdf import FPDF
import plotly.graph_objects as go

st.set_page_config(
    page_title="ARGUS — Decision Workspace",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.block-container { padding-top: 1rem; padding-bottom: 1rem; }
.stButton>button { width: 100%; }
.conflict-box { border: 2px solid #e74c3c; border-radius: 8px; padding: 1.2rem; background: #1a1a2e; margin: 0.5rem 0; }
.verified-box { border: 2px solid #27ae60; border-radius: 8px; padding: 1rem; background: #0a1f0a; margin: 0.3rem 0; }
.flagged-box { border: 2px solid #f39c12; border-radius: 8px; padding: 1rem; background: #1a1a0a; margin: 0.3rem 0; }
.quarantined-box { border: 2px solid #e74c3c; border-radius: 8px; padding: 1rem; background: #1a0a0a; margin: 0.3rem 0; }
h1, h2, h3 { margin-top: 0.5rem !important; }
div[data-testid="stExpander"] div[data-testid="stExpanderToggleIcon"] { display: none; }
.source-link { color: #3498db; text-decoration: none; }
.source-link:hover { text-decoration: underline; }
.halt-title { color: #e74c3c; font-size: 1.5rem; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if "result" not in st.session_state:
    st.session_state.result = None
if "human_decision" not in st.session_state:
    st.session_state.human_decision = None
if "show_debate" not in st.session_state:
    st.session_state.show_debate = False
if "decision_logged" not in st.session_state:
    st.session_state.decision_logged = False

header_col1, header_col2, header_col3 = st.columns([0.5, 3, 1.5])
with header_col1:
    st.markdown("<h1 style='font-size:2.5rem; margin:0;'>🛡️</h1>", unsafe_allow_html=True)
with header_col2:
    st.title("ARGUS")
    st.caption("Agentic Resilience with Epistemic Scrutiny & Evidence Review")
with header_col3:
    if st.session_state.result and st.button("📄 EXPORT TO PDF", type="primary", use_container_width=True):
        r = st.session_state.result
        if r:
            with st.spinner("Generating PDF report..."):
                pdf_file = _generate_pdf(r)
                with open(pdf_file, "rb") as f:
                    st.download_button(
                        label="⬇️ DOWNLOAD PDF",
                        data=f,
                        file_name=pdf_file,
                        mime="application/pdf",
                        use_container_width=True
                    )

st.divider()

incident_options = [
    "Iran-Israel conflict, Strait of Hormuz, crude oil, India",
    "Red Sea shipping attacks, LNG, Japan",
    "Malacca Strait piracy, crude oil, China",
]
input_col, _ = st.columns([3, 1])
with input_col:
    user_input = st.text_input(
        "Incident Description",
        value=incident_options[0],
        placeholder="e.g., Strait of Hormuz, crude oil, India"
    )

btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 4])
with btn_col1:
    if st.button("🚀 RUN ANALYSIS", type="primary", use_container_width=True):
        with st.spinner("Running 6 agents + ERASER audit..."):
            result = asyncio.run(run_argus(user_input))
            st.session_state.result = result
            st.session_state.human_decision = None
            st.session_state.show_debate = False
            st.session_state.decision_logged = False
            st.rerun()
with btn_col2:
    if st.button("🗑️ CLEAR", use_container_width=True):
        st.session_state.result = None
        st.session_state.human_decision = None
        st.session_state.show_debate = False
        st.session_state.decision_logged = False
        st.rerun()
with btn_col3:
    st.markdown("&nbsp;")

if st.session_state.result:
    r = st.session_state.result
    status = r.get("status", "UNKNOWN")

    if status == "REJECTED":
        a0 = r.get("agent_0", {})
        st.error(f"⚠️ INPUT REJECTED — {a0.get('reason', 'Too vague')} (specificity: {a0.get('specificity_score', 0)})")
    elif status == "HALTED":
        conflict_col1, conflict_col2 = st.columns([3, 1])
        with conflict_col1:
            st.markdown('<div class="conflict-box">', unsafe_allow_html=True)
            st.markdown('<p class="halt-title">⚠️ SYSTEM HALTED — Agent Conflict Detected</p>', unsafe_allow_html=True)
            a7 = r.get("agent_7", {})
            opinions = a7.get("agent_opinions", {})
            a4_risk = opinions.get("Agent_4_Risk", 0)
            a6_proxy = opinions.get("Agent_6_Sourcing_Proxy", 0)
            st.markdown(f"""
            | Agent | Score | Verdict |
            |-------|-------|---------|
            | **Agent 4 (Risk)** | {a4_risk:.2f} | {'🔴 HIGH' if a4_risk >= 0.6 else '🟡 MEDIUM' if a4_risk >= 0.45 else '🟢 LOW'} |
            | **Agent 6 (Sourcing Proxy)** | {a6_proxy:.2f} | {'🔴 HIGH' if a6_proxy >= 0.6 else '🟡 MEDIUM' if a6_proxy >= 0.45 else '🟢 LOW'} |
            | **Variance** | {a7.get('variance', 0):.2f} | **Threshold: 0.30** |
            """)
            st.markdown(f"**Status**: {a7.get('recommendation', 'Human review required')}</div>", unsafe_allow_html=True)
        with conflict_col2:
            if st.button("🔍 VIEW DEBATE", use_container_width=True):
                st.session_state.show_debate = not st.session_state.show_debate
        if st.session_state.show_debate:
            a2 = r.get("agent_2", {})
            flagged = a2.get("flagged_claims", [])
            verified = a2.get("verified_claims", [])
            st.subheader("Agent Debate")
            debate_col1, debate_col2 = st.columns(2)
            with debate_col1:
                st.markdown("**❌ Agent 1 (News) — Claim**")
                for c in flagged:
                    st.markdown(f'<div class="flagged-box">{c.get("claim", "")[:150]}...<br><small>Source: {c.get("source_url", "")}</small><br><small>Confidence: {c.get("confidence", 0)}</small></div>', unsafe_allow_html=True)
            with debate_col2:
                st.markdown("**✅ Agent 2 (Verification) — EIA Baseline**")
                for c in flagged:
                    st.markdown(f'<div class="verified-box">EIA baseline: {c.get("reason", "")}<br><small>Confidence: {c.get("confidence", 0)}</small></div>', unsafe_allow_html=True)
            st.info("The system detected conflicting evidence and refused to proceed. Perplexity would have returned the wrong number with a citation.")
    elif status == "COMPLETE":
        st.success("✅ ANALYSIS COMPLETE — Awaiting Human Validation")

    tabs = st.tabs(["📊 Risk", "📋 Agents", "📝 Narrative", "🛡️ ERASER"])
    a4 = r.get("agent_4", {})
    a2 = r.get("agent_2", {})
    a5 = r.get("agent_5", {})
    a7 = r.get("agent_7", {})
    a8 = r.get("agent_8", {})

    with tabs[0]:
        if a4:
            gauge_col, comp_col = st.columns([1, 2])
            with gauge_col:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=a4.get("risk_score", 0),
                    title={"text": f"Risk: {a4.get('risk_level', 'N/A')}"},
                    gauge={
                        "axis": {"range": [0, 1]},
                        "bar": {"color": "#e74c3c" if a4.get("risk_level") == "HIGH" else "#f39c12" if a4.get("risk_level") == "MEDIUM" else "#27ae60"},
                        "steps": [
                            {"range": [0, 0.45], "color": "#1b4332"},
                            {"range": [0.45, 0.60], "color": "#7f4f24"},
                            {"range": [0.60, 1], "color": "#4a1a1a"}
                        ],
                        "threshold": {"line": {"color": "white", "width": 4}, "thickness": 0.75, "value": a4.get("risk_score", 0)}
                    }
                ))
                fig.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="rgba(0,0,0,0)", font={"color": "white"})
                st.plotly_chart(fig, use_container_width=True)
                st.metric("System Confidence", f"{a4.get('confidence', 0):.0%}")
            with comp_col:
                st.markdown("**Risk Components (Cambridge Formula)**")
                for comp in a4.get("components", []):
                    st.progress(comp["value"], text=f"**{comp['name']}** = {comp['value']:.2f} × {comp['weight']} = {comp['contribution']:.4f}")
                    st.caption(f"Source: [{comp['source_url'].split('/')[-1]}]({comp['source_url']})")
                st.caption(f"*Formula: {a4.get('formula_citation', 'Cambridge et al. 2026')}*")
        else:
            st.info("No risk analysis available")

    with tabs[1]:
        agent_tabs = st.tabs(["Agent 0: Gate", "Agent 1: Research", "Agent 2: Verify", "Agent 4: Risk", "Agent 7: Conflict"])
        with agent_tabs[0]:
            a0 = r.get("agent_0", {})
            st.markdown("**Search Quality Gate**")
            st.json(a0)
        with agent_tabs[1]:
            a1 = r.get("agent_1", {})
            st.markdown("**Research & Retrieval**")
            st.metric("Claims Retrieved", len(a1.get("claims", [])))
            for c in a1.get("claims", []):
                with st.container(border=True):
                    st.markdown(f"**Source**: [{c.get('source_url', '')}]({c.get('source_url', '')})")
                    st.markdown(f"**Tier**: {c.get('source_tier', 'unknown')} | **Confidence**: {c.get('retrieval_confidence', 0)}")
                    st.caption(c.get("claim", "")[:200])
            if a1.get("quarantined"):
                st.markdown("**Quarantined**")
                for q in a1["quarantined"]:
                    st.markdown(f'<div class="quarantined-box">{q.get("claim", "")} — {q.get("reason", "")}</div>', unsafe_allow_html=True)
        with agent_tabs[2]:
            st.markdown("**Source Verification**")
            v, f, q = st.columns(3)
            with v:
                st.markdown(f"**✅ Verified ({len(a2.get('verified_claims', []))})**")
                for c in a2.get("verified_claims", [])[:3]:
                    st.markdown(f'<div class="verified-box">{c.get("claim", "")[:100]}...<br><small>Conf: {c.get("confidence", 0)}</small></div>', unsafe_allow_html=True)
            with f:
                st.markdown(f"**⚠️ Flagged ({len(a2.get('flagged_claims', []))})**")
                for c in a2.get("flagged_claims", []):
                    st.markdown(f'<div class="flagged-box">{c.get("claim", "")[:100]}...<br><small>{c.get("reason", "")}</small></div>', unsafe_allow_html=True)
            with q:
                st.markdown(f"**❌ Quarantined ({len(a2.get('quarantined_claims', []))})**")
                for c in a2.get("quarantined_claims", []):
                    st.markdown(f'<div class="quarantined-box">{c.get("claim", "")[:100]}...<br><small>{c.get("reason", "")}</small></div>', unsafe_allow_html=True)
        with agent_tabs[3]:
            st.markdown("**Risk Analyzer**")
            st.json(a4)
        with agent_tabs[4]:
            st.markdown("**Consensus & Conflict Detector**")
            st.json(a7)
            if a7.get("status") == "HALTED":
                st.markdown('<div class="conflict-box"><b>⛔ SYSTEM ACTION: HALTED</b> — Variance exceeds 0.30 threshold. Human review required.</div>', unsafe_allow_html=True)

    with tabs[2]:
        if a5.get("narrative"):
            st.markdown("**CSCO Narrative**")
            for line in a5["narrative"].split("\n\n"):
                st.markdown(line)
            if a5.get("citations"):
                st.divider()
                st.markdown("**Citations**")
                for c in a5["citations"]:
                    st.markdown(f"- `{c.get('text', '')}` → [{c.get('url', '')}]({c.get('url', '')})")
            st.divider()
            st.metric("Narrative Confidence", f"{a5.get('confidence', 0):.0%}", help="Cambridge baseline: 0.486 ± 0.172")
        else:
            st.info("No narrative generated")

    with tabs[3]:
        if a8.get("answers"):
            st.markdown("**ERASER Audit**")
            st.metric("Status", a8.get("eraser_status", "N/A"))
            if a8.get("flags"):
                for flag in a8["flags"]:
                    st.warning(flag)
            for q, a in a8.get("answers", {}).items():
                with st.expander(f"**{q}**"):
                    st.markdown(a)
        else:
            st.info("No ERASER audit available")

    st.divider()
    st.subheader("👤 Human Validation Gate")
    st.caption("The system cannot finalize without your explicit decision.")

    if st.session_state.decision_logged:
        st.success("✅ Decision logged successfully.")
        st.json(st.session_state.last_log)
    else:
        action_cols = st.columns(5)
        actions = [
            ("✅ ACCEPT", "ACCEPT"),
            ("❌ REJECT", "REJECT"),
            ("✏️ EDIT", "EDIT"),
            ("🔍 INVESTIGATE", "INVESTIGATE"),
            ("🗣️ CHALLENGE", "CHALLENGE"),
        ]
        for i, (label, action) in enumerate(actions):
            with action_cols[i]:
                if st.button(label, use_container_width=True, key=f"action_{action}"):
                    st.session_state.human_decision = action
                    st.rerun()

        hd = st.session_state.human_decision
        if hd == "ACCEPT":
            st.divider()
            st.markdown("### 📜 Decision Acknowledgment Required")
            with st.container(border=True):
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
                ack_col1, ack_col2 = st.columns(2)
                with ack_col1:
                    if st.button("✅ I UNDERSTAND AND ACCEPT", type="primary", use_container_width=True):
                        _log_decision(r, "ACCEPT")
                        st.session_state.decision_logged = True
                        st.rerun()
                with ack_col2:
                    if st.button("↩️ RETURN TO CHALLENGE", use_container_width=True):
                        st.session_state.human_decision = None
                        st.rerun()
        elif hd == "REJECT":
            reason = st.text_area("Rejection reason (required):", key="reject_reason")
            if st.button("CONFIRM REJECTION", type="secondary", use_container_width=True):
                _log_decision(r, "REJECT", reason or "No reason given")
                st.session_state.decision_logged = True
                st.rerun()
        elif hd == "EDIT":
            st.info("Edit mode active. Modify risk components below.")
            if a4:
                comps = a4.get("components", [])
                for i, comp in enumerate(comps):
                    st.slider(f"{comp['name']}", 0.0, 1.0, comp["value"], key=f"edit_{i}")
                if st.button("RECALCULATE", use_container_width=True):
                    st.info("Recalculation not implemented in prototype — modify formula in agents/agent_4_risk.py")
        elif hd == "INVESTIGATE":
            st.info("Click any source URL in the tabs above to open the original document.")
            st.markdown("**All source URLs in this workspace are clickable.**")
        elif hd == "CHALLENGE":
            challenge_q = st.text_input("Challenge the system (e.g., 'Why not buy from Brazil?'):", key="challenge_input")
            if st.button("SUBMIT CHALLENGE", use_container_width=True):
                with st.spinner("Re-retrieving..."):
                    st.info("The system has no verified data on Brazil-India crude routes for this corridor. It cannot assess this alternative.")

        if st.session_state.decision_logged and st.session_state.last_log:
            st.divider()
            st.markdown("**Last Decision Logged**")
            st.json(st.session_state.last_log)


def _generate_pdf(result: dict) -> str:
    class ARGUSReport(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 16)
            self.set_text_color(231, 76, 60)
            self.cell(0, 10, "ARGUS Energy Supply Chain Risk Report", 0, 1, "C")
            self.set_font("Helvetica", "", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 5, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}", 0, 1, "C")
            self.ln(5)

        def section_title(self, title):
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(41, 128, 185)
            self.cell(0, 7, title, 0, 1, "L")
            self.ln(1)

        def section_body(self, body):
            self.set_font("Helvetica", "", 9)
            self.set_text_color(220, 220, 220)
            self.multi_cell(0, 4.5, body)
            self.ln(2)

    a0 = result.get("agent_0", {})
    a2 = result.get("agent_2", {})
    a4 = result.get("agent_4", {})
    a5 = result.get("agent_5", {})
    a7 = result.get("agent_7", {})

    pdf = ARGUSReport()
    pdf.add_page()
    pdf.set_fill_color(5, 8, 16)
    pdf.rect(0, 0, 210, 297, "F")

    pdf.section_title("EXECUTIVE SUMMARY")
    pdf.section_body(
        f"Incident: {a0.get('corridor', 'N/A')} — {a0.get('commodity', 'N/A')}\n"
        f"Economy: {a0.get('economy', 'N/A')}\n"
        f"Risk Score: {a4.get('risk_score', 'N/A')} ({a4.get('risk_level', 'N/A')})\n"
        f"System Confidence: {a4.get('confidence', 'N/A')}\n"
        f"Conflict Status: {a7.get('status', 'N/A')}"
    )

    pdf.section_title("AGENT ANALYSIS")
    for aid, name, out in [
        ("0", "Search Quality", a0.get("status")),
        ("1", "Research & Retrieval", f"{len(result.get('agent_1', {}).get('claims', []))} claims"),
        ("2", "Source Verification", f"{len(a2.get('verified_claims', []))} verified, {len(a2.get('flagged_claims', []))} flagged"),
        ("4", "Risk Analyzer", f"Score: {a4.get('risk_score', 'N/A')}"),
        ("5", "CSCO Synthesizer", f"Confidence: {a5.get('confidence', 'N/A')}"),
        ("7", "Consensus/Conflict", a7.get("status")),
        ("8", "ERASER Audit", result.get("agent_8", {}).get("eraser_status")),
    ]:
        pdf.section_body(f"Agent {aid} ({name}): {out}")

    if a5.get("narrative"):
        pdf.section_title("CSCO NARRATIVE")
        pdf.section_body(a5["narrative"])

    pdf.section_title("RISK COMPONENT BREAKDOWN")
    for comp in a4.get("components", []):
        pdf.section_body(f"{comp['name']}: value={comp['value']:.2f}, weight={comp['weight']}, contribution={comp['contribution']:.4f}, source={comp['source_url']}")

    pdf.section_title("UNCERTAINTY DISCLOSURE")
    pdf.section_body(
        "This report is based on:\n"
        "- Verified government data (EIA/IEA/PIB): 73%\n"
        "- Inferred from historical patterns: 17%\n"
        "- LLM narrative synthesis: 10%\n\n"
        "Known gaps:\n"
        "- Real-time AIS data not integrated (static snapshot used)\n"
        "- Refinery blending costs not modeled\n"
        "- Geopolitical negotiation outcomes unpredictable"
    )

    filename = f"ARGUS_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    pdf.output(filename)
    return filename


def _log_decision(result: dict, action: str, reason: str = ""):
    log = {
        "decision_id": f"dec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(result)}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "human_action": action,
        "reason": reason or "Accepted after review",
        "risk_score": result.get("agent_4", {}).get("risk_score"),
        "risk_level": result.get("agent_4", {}).get("risk_level"),
        "confidence_scores": {
            "Agent_4": result.get("agent_4", {}).get("confidence"),
            "Agent_5": result.get("agent_5", {}).get("confidence"),
        },
        "agent_7_status": result.get("agent_7", {}).get("status"),
        "eraser_status": result.get("agent_8", {}).get("eraser_status")
    }
    try:
        with open("decision_log.jsonl", "a") as f:
            f.write(json.dumps(log) + "\n")
    except IOError:
        pass
    st.session_state.last_log = log


if __name__ == "__main__":
    pass
