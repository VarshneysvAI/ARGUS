# ARGUS — Agentic Resilience with Epistemic Scrutiny & Evidence Review

> *"Every other team built an AI that answers. We built a system of experts that debate — and when they can't agree, it stops."*

**ET AI Hackathon 2026 — PS2: Energy Supply Chain Resilience for Import-Dependent Economies**

---

## What ARGUS Does

An 8-agent AI system that analyzes energy supply chain disruptions. Unlike standard AI pipelines that produce static reports, ARGUS:

- **Verifies every claim** against government data (EIA, IEA, PIB) before trusting it
- **Detects conflicting evidence** — Saudi "15M b/d" shut-in vs EIA's verified 9.1M b/d
- **Halts automatically** when its agents disagree beyond a threshold
- **Forces human validation** — the system cannot finalize decisions without explicit approval
- **Shows its sources** — every number is clickable to the original document

## The "Applause Moment" Demo

Feed a news article claiming "Saudi Arabia shut in 15M b/d":

1. Agent 1 extracts the claim with its source URL
2. Agent 2 cross-checks against EIA data (9.1M b/d — 64.8% variance)
3. **SYSTEM HALTS** — red banner, agent conflict displayed
4. Split-screen shows the debate: Al Jazeera claim vs EIA verification
5. Human reviews, clicks ACCEPT → uncertainty disclosure → PDF export

## Architecture

```
User Input → Agent 0 (Search Quality Gate) → Agent 1 (Research & Retrieval)
→ Agent 2 (Source Verification) → Agent 4 (Risk Analyzer)
→ Agent 7 (Consensus/Conflict) → IF variance > 0.30: HALT
→ Agent 5 (CSCO Synthesizer) → Agent 8 (ERASER Audit)
→ Human Validation Gate → Decision Workspace
```

| Agent | Role | Implementation |
|-------|------|----------------|
| 0 | Search Quality Gate | Deterministic (regex + keyword extraction) |
| 1 | Research & Retrieval | Local file reader with source URL extraction |
| 2 | Source Verification | EIA baseline cross-check (±10% tolerance) |
| 4 | Risk Analyzer | Cambridge formula (35/25/20/10/10 weights) |
| 7 | Consensus/Conflict | Variance calculation; >0.30 = HALT |
| 5 | CSCO Synthesizer | Narrative with mandatory inline citations |
| 8 | ERASER | 8-question audit on final output |

## Stack

- **Pipeline**: LangGraph (6 agents + ERASER)
- **UI**: Streamlit (Decision Workspace)
- **Graph**: Python dict (NetworkX-compatible schema)
- **Data**: Pre-loaded (EIA, IEA, PIB, news articles)
- **PDF**: fpdf2 (one-click report export)
- **LLM**: NVIDIA NIM API (optional, for narrative synthesis)

## Quick Start

```bash
# Setup
python -m venv .venv
.venv\Scripts\Activate
pip install langgraph streamlit fpdf2 plotly networkx python-dotenv httpx

# Run CLI
python main.py "Iran-Israel conflict, Strait of Hormuz, crude oil, India"

# Run UI
streamlit run app.py
```

## 10-Day Build Plan

| Day | Task |
|-----|------|
| 1 | Environment + Agent 0 (entity extraction) |
| 2 | Agent 1 (local file retrieval) |
| 3 | Agent 2 (EIA cross-check verification) |
| 4 | Agent 4 (risk formula) + Agent 7 (conflict detection) |
| 5 | Agent 5 (narrative) + Agent 8 (ERASER) |
| 6 | LangGraph orchestration + CLI runner |
| 7 | Streamlit UI (core: input, gauge, conflict) |
| 8 | Human validation gate + PDF export |
| 9 | Polish + demo data + backup video |
| 10 | Rehearse 10× + final submission |

## Key Differentiators

- **8th agent is a professional skeptic** (not a helper — an adversary)
- **Citation-required graph writes** (no source URL = rejected)
- **Agent conflict halts the system** (variance > 0.30 stops the pipeline)
- **Human gate is a system invariant** (not a UI checkbox — a pipeline block)
- **"I don't know" as a feature** (admitted ignorance over hallucination)
- **Every number is clickable to its source** (full provenance)

## Data Sources

All pre-loaded in `data/articles/`:
- EIA Short-Term Energy Outlook (April 2026)
- IEA Oil Market Report (June 2026)
- PIB Government of India press releases
- Al Jazeera (with intentional error for demo)
- Conflicting EIA verification article

## License

MIT — Hackathon project for ET AI Hackathon 2026
