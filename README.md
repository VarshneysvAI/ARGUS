# ARGUS v3 — Agentic Resilience with Epistemic Scrutiny & Evidence Review

> *"Every other team built an AI that answers. We built a system of experts that debate — and when they can't agree, it stops."*

**ET AI Hackathon 2026 — PS2: Energy Supply Chain Resilience for Import-Dependent Economies**

---

## What ARGUS Does

An **11-agent AI system** that analyzes supply chain disruptions and generates real-time, heavily-cited intelligence briefings. Unlike standard AI pipelines that produce static, hallucination-prone reports, ARGUS:

- **Extracts and cross-verifies every claim** using live web search and local baseline data.
- **Audits itself** via the ERASER agent, producing a PolitiFact-style credibility rating for its own output.
- **Quarantines disinformation** using the D-Shield agent to filter out untrustworthy sources.
- **Ranks alternative suppliers** using the Cambridge Risk Formula and TOPSIS MCDA (Multi-Criteria Decision Analysis).
- **Drafts automated RFQs (Request for Quotations)** for the highest-ranked alternative suppliers.
- **Forces Human-in-the-Loop (HitL) validation** — users can question or override any claim directly in the UI.

## The 11-Agent Architecture

```text
Agent 0 (Catalyst)      → Extracts entities & plans queries
Agent 1 (Research)      → Live web search + PDF data + claim extraction  
Agent 2 (Verification)  → Cross-references claims against baseline data
Agent 3 (Graph)         → Builds semantic NetworkX graph from verified claims
Agent 9 (D-Shield)      → Quarantines disinformation & unreliable domains
Agent 4 (Risk)          → Computes Cambridge weighted risk formula & satellite intelligence
Agent 6 (MCDA)          → Ranks alternative sourcing via TOPSIS
Agent 7 (Consensus)     → Compares Risk vs MCDA for logical alignment
Agent 5 (Synthesizer)   → Generates CSCO narrative briefing with strict citations
Agent 10 (RFQ)          → Drafts procurement document for top alternative
Agent 8 (ERASER)        → Full pipeline epistemic audit
```

## Tech Stack

The architecture has evolved significantly from its original prototype into a robust, production-ready full-stack application:

- **Backend Orchestration**: FastAPI (Python) orchestrating asynchronous agent execution.
- **Frontend Dashboard**: React 18 with Recharts for dynamic data visualization, built on a custom glassmorphism design system (`ui-ux-pro-max`).
- **Graph Processing**: NetworkX for semantic supply chain mapping.
- **LLM Reasoning**: Modular 4-tier fallback system (NIM → Groq → OpenRouter → Deterministic Fallback) using LangChain.
- **Reporting**: `fpdf2` for instant PDF export of the generated intelligence briefing.

## Quick Start

### 1. Environment Setup
```bash
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
```

### 2. API Keys (`.env`)
You must provide API keys for the LLM providers and search tools:
```env
SERPER_API_KEY=your_serper_key
GROQ_API_KEY=your_groq_key
OPENROUTER_API_KEY=your_openrouter_key
```

### 3. Run the System
```bash
# Start the FastAPI backend and React dashboard
python server.py
```
Open `http://localhost:8080` in your browser.

## Key Differentiators

- **11 Specialized Experts**: Instead of one monolithic prompt, the workload is distributed across specialized agents (Risk Analyzer, Synthesizer, Disinformation Shield, ERASER).
- **"I don't know" as a feature**: The system prefers to flag or quarantine claims (Agent 9) rather than hallucinate.
- **Interactive Intelligence Briefing**: The UI is not a static grid; it is a scrollable, professional report where every claim is cited and can be questioned by the user.
- **Causal Graphing**: Agent 3 builds a semantic dependency graph, allowing ARGUS to understand *how* a disruption in the Strait of Hormuz cascades to FMCG markets in India.

## License

MIT — Built for the ET AI Hackathon 2026.
