# ARGUS v5.0 (FINAL): PRODUCTION-READY MASTER BLUEPRINT

> **Supersedes ARGUS v4.2.** This is the build-locked engineering canvas for the ET AI Hackathon 2026, Problem Statement 2 (AI-Driven Energy Supply Chain Resilience for Import-Dependent Economies). All v4.2 content is carried forward except where the changelog below explicitly modifies it. If a section conflicts with an older document, this file wins.

---

## 0. CHANGELOG: v4.2 → v5.0 (THE FIX PLAN)

Work these items in the order listed. Effort estimates assume the 3-developer split defined in Section 9.

| # | Change | Decision | Lands In | Effort |
|---|--------|----------|----------|--------|
| C1 | **LIVE SIGNAL demo trigger** replaces continuous-monitoring cron loop. Cron/watch-mode is **deferred** to post-hackathon roadmap (API-call cost). | ACCEPTED (modified) | Stage 2 entry point + UI + DB | 0.5 day |
| C2 | **SPR Drawdown Optimizer** — upgrade from descriptive depletion curve to prescriptive strategy ranking. Reserve floor 20%, static replenishment windows, no separate trigger (runs inside Stage 3). | ACCEPTED | Stage 3 | 0.5–1 day |
| C3 | **National Economic Cascade** — extend impact chain refinery → pump price (₹/litre) → power-sector stress flag → GDP bps via static elasticity table. Cost delta also reported in **₹ crore/day** for a named refinery. | ACCEPTED | Stage 3 + UI | 0.5 day |
| C4 | **Sanctions Compliance Pre-Filter** — static JSON of sanctioned entities/corridors applied as a hard filter *before* the heuristic matrix. | ACCEPTED | Stage 3 | 2–3 hours |
| C5 | **Thread D (multi-modal PDF/image parser) CUT.** Stretch goal only; maps to no PS2 evaluation point. | CUT | — | saves ~1 day |
| C6 | **Deployment split locked:** Next.js frontend on Vercel; FastAPI + AIS WebSocket backend on Azure (always-on). Vercel serverless **cannot** hold the persistent AIS WebSocket. | ACCEPTED | Section 7 | config only |
| C7 | **Units convention fixed:** display `"15 mbd"`, never `"15M mbd"` (mbd already = million barrels/day). Pydantic hard bound `volume_lost_mbd ≤ 21` (total Hormuz throughput ≈ 20–21 mbd). | ACCEPTED | Stage 1 schema | 3 lines |
| C8 | **Config-driven corridors** — every corridor is one JSON file (throughput, exposure, freight matrix, AIS bounding box). This *is* the Scalability (15%) answer. | ACCEPTED | Section 8 | 1 hour per corridor |

**Carried forward from the v4.2 de-risking pass (already locked, do not regress):**
- "Cambridge Risk Score" renamed → **Composite Supply Chain Risk Index (SCRI)**; weights labeled as heuristic hackathon baselines in the Math X-Ray.
- OSINT is **load-bearing but gated**: the D-Shield Python script flags `variance=True` when OSINT-claimed volume loss deviates >20% from baseline; only then does Agent 5 write Scenario A/B branching.
- EIA price labeled **"Daily Official Benchmark"** — never "live computed" / tick-real-time.

---

## 1. ARCHITECTURAL CANVAS & TOPOLOGY

ARGUS v5.0 is a high-fidelity, adversarial energy supply chain intelligence platform. It strictly separates speculative open-source signals (OSINT) from deterministic economic, physical, and geospatial realities. Two generative LLM agents handle text extraction and synthesis; a core **Deterministic Python Analytics Engine** owns all risk math, compliance filtering, MCDA ranking, reserve optimisation, financial mapping, and final schema validation.

```text
+---------------------------------------------------------------------------------------+
|                                ARGUS v5.0 CANVAS                                      |
+---------------------------------------------------------------------------------------+
|                                                                                       |
|  [ENTRY: LIVE SIGNAL BUTTON / CACHED INCIDENT / MANUAL PROMPT]                        |
|   └── Demo-deterministic trigger; t0 timestamped for latency metric (C1)              |
|                                                                                       |
|  [STAGE 1: INTERACTIVE PARSER (Agent 1)]                                              |
|   └── Extracts core parameters into strict Pydantic schema                            |
|   └── HARD BOUND: volume_lost_mbd ≤ 21.0 (C7)                                         |
|                                                                                       |
|  [STAGE 2: CONCURRENT RETRIEVAL & STREAMING]                                          |
|   ├── Thread A: Ground Truth (EIA API v2 — "Daily Official Benchmark")                |
|   ├── Thread B: OSINT Sidecar (Serper.dev async social scraping)                      |
|   └── Thread C: Live Vessel Tracking (Aisstream.io WebSocket + cached AIS fallback)   |
|   (Thread D multi-modal parser: CUT — stretch goal only)                              |
|                                                                                       |
|  [D-SHIELD: DETERMINISTIC VARIANCE GATE]                                              |
|   └── Python: OSINT vs baseline deviation >20% → variance=True → enables A/B branch   |
|                                                                                       |
|  [STAGE 3: DETERMINISTIC ANALYTICS ENGINE (Pure Python / NumPy / SciPy)]              |
|   ├── Financial Pass-Through Calculator ($/day AND ₹ crore/day)                       |
|   ├── Sanctions Compliance Pre-Filter (hard filter, pre-TOPSIS)          [NEW — C4]   |
|   ├── Heuristic Alternative Sourcing Ranker → Executable Procurement Cards            |
|   ├── SPR Drawdown Optimizer (strategy ranking, 20% floor)               [NEW — C2]   |
|   ├── National Economic Cascade (₹/litre, power stress, GDP bps)         [NEW — C3]   |
|   └── SCRI Composite Risk Index (heuristic weights, disclosed)                        |
|                                                                                       |
|  [STAGE 4: ADVERSARIAL SYNTHESIS (Agent 5 — serial)]                                  |
|   └── Scenario A/B branching ONLY when D-Shield variance=True                         |
|   └── Wraps every fact in [CLAIM id="" source=""] tags                                |
|                                                                                       |
|  [STAGE 5: DETERMINISTIC REGEX VALIDATOR]                                             |
|   └── Every [CLAIM] must map to valid URL metadata else ValueError (pipeline halts)   |
|   └── Hard-checks all printed math against Stage 3 floats                             |
|                                                                                       |
|  [HUMAN-IN-THE-LOOP CONTROL GATE (Next.js on Vercel)]                                 |
|   └── Strategic briefing, 3D satellite map, procurement cards, cascade panel          |
|   └── Math X-Ray transparency panel + Hover-to-Argue counterfactual recompute         |
|   └── Signal→Recommendation latency banner                                            |
|                                                                                       |
+---------------------------------------------------------------------------------------+
```

---

## 2. THE HYBRID EXECUTION FLOW: PARALLEL VS. SERIAL

```text
        [ LIVE SIGNAL BUTTON / CACHED INCIDENT / MANUAL PROMPT ]
                          │  (t0 written to argus_signal_events)
                          ▼
                STAGE 1: LLM EXTRACTION
              (Agent 1 — strict Pydantic, mbd ≤ 21)
                          │
                          ▼
            STAGE 2: DATA AGGREGATION (concurrent)
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   Thread A: EIA      Thread B: OSINT      Thread C: AISSTREAM
   Daily Official     Serper.dev feed      WebSocket + cached
   Benchmark          (gated by D-Shield)  snapshot fallback
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                     D-SHIELD VARIANCE GATE
              (pure Python; sets variance flag)
                            │
                            ▼
              STAGE 3: DETERMINISTIC ENGINE
   ┌──────────┬──────────┬──────────┬──────────┬──────────┐
   ▼          ▼          ▼          ▼          ▼          ▼
  Cost Δ    Sanctions   Heuristic  SPR        Economic   SCRI
  $ + ₹cr   Pre-Filter  Ranking    Optimizer  Cascade    Index
    └──────────┴──────────┴──────────┴──────────┴──────────┘
                            │
                            ▼
              STAGE 4: ADVERSARIAL SYNTHESIS
            (Agent 5 — serial; A/B only if gated)
                            │
                            ▼
              STAGE 5: REGEX / SCHEMA VALIDATOR
               (pure Python safety gate — serial)
                            │  (t1 written; latency = t1 − t0)
                            ▼
               HUMAN-IN-THE-LOOP CONTROL GATE
              (Next.js Command Center — Vercel)
```

### Stage-by-Stage Operational Walkthrough

- **Entry (C1):** Three trigger modes. `LIVE_SIGNAL` loads a pre-cached breaking-event payload (e.g., *"Tanker seizure reported, Strait of Hormuz"*), writes `t0` to `argus_signal_events`, and starts the UI timer. `CACHED_SCENARIO` runs a stored session for offline fallback. `MANUAL_PROMPT` accepts free text. No background polling exists in v5.0 — see Section 6.
- **Stage 1 — LLM Extraction:** Produces the clean JSON payload (`corridor, commodity, economy, volume_lost_mbd, duration_days, confidence`). Pydantic enforces the schema and the ≤21 mbd physical bound, so the Python engine can never receive a KeyError or a physically impossible scenario.
- **Stage 2 — Aggregation:** Async workers. Serper.dev fetches social chatter. The core pipeline relies on static corridor baseline JSONs, the EIA daily benchmark, and the AISstream.io bounding-box stream (with a cached AIS snapshot if the socket drops).
- **D-Shield:** Pure Python comparator. If any OSINT-carried volume claim deviates >20% from the baseline figure, sets `variance=True`. This is the *only* path by which OSINT influences the narrative — it can trigger Scenario A/B text, but it can never touch Stage 3 math.
- **Stage 3 — Python Analytics:** The absolute center of system truth. Executes cost delta (dual currency), sanctions pre-filter, Heuristic ranking, SPR optimization, economic cascade, and SCRI in one NumPy pass. Re-runs identically on every Hover-to-Argue counterfactual.
- **Stage 4 — Synthesis:** Receives flawless math. Drafts Scenario A vs. B **only** when `variance=True`; otherwise drafts a single coherent narrative. Wraps facts in `[CLAIM]` tags.
- **Stage 5 — Regex Validator:** Scans the narrative. A `[CLAIM]` tag without valid citation metadata → `ValueError`, pipeline halts. Printed numbers are string-matched against Stage 3 floats.
- **Control Gate:** Renders validated data, geospatial layers, procurement cards, cascade panel, and the latency banner (`t1 − t0`).

---

## 3. THE DETERMINISTIC ANALYTICS ENGINE & FINANCES

All numerical mechanics live in standard Python. No LLM ever computes, rounds, or estimates a number.

### A. Financial Pass-Through Pricing Model (dual-currency)

Computes the **Daily Cost Delta** `C_Δ`:

```
C_Δ = V_lost × (P_spot − P_contract + M_freight + δ_grade) + D_congestion
```

**Dual output (C3):** reported as `C_Δ_usd/day` **and** `C_Δ_inr_crore/day = C_Δ_usd × fx / 1e7`, pinned to the named refinery from the extraction schema (default demo refinery: Jamnagar or Paradip). `fx` is a static, user-adjustable field (default ₹86/USD, labeled as an assumption).

**Data Origin Matrix (rendered in the UI "Math X-Ray"):**

| Variable | Meaning | Origin Class |
|---|---|---|
| `V_lost` | Disrupted volume (mbd) | **Live Extracted** — Stage 1, bounded ≤ 21 |
| `P_spot` | Spot crude benchmark | **Daily Official Benchmark** — EIA API v2 |
| `P_contract` | Pre-existing term contract | **Static Estimate** — user-adjustable (default $75/bbl) |
| `M_freight` | Alternate routing markup | **Matrix Lookup** — corridor freight dictionary |
| `δ_grade` | Quality compatibility penalty | **Matrix Lookup** — refinery configuration table |
| `D_congestion` | Destination demurrage | **Derived Proxy** — AIS vessel-speed variation |
| `fx` | USD/INR rate | **Static Adjustable** — default 86.0, labeled assumption |

### B. Sanctions Compliance Pre-Filter (NEW — C4)

Hard filter executed **before** Heuristic Ranking. Any candidate supplier, flag state, or corridor present in `sanctions_snapshot.json` is removed from the decision matrix and surfaced in the UI as **"COMPLIANCE-BLOCKED"** (deliberately visible — demonstrating the filter working is a demo asset, not a hidden step).

```json
{
  "sanctioned_suppliers": ["NIOC (Iran)", "PDVSA (Venezuela)"],
  "sanctioned_flag_states": ["IR", "VE"],
  "restricted_corridors": [],
  "source": "OFAC SDN + EU consolidated list — static snapshot",
  "note": "Heuristic snapshot for hackathon demo; production = live list ingestion"
}
```

### C. Alternative Site Tracker (Heuristic MCDA → Executable Procurement Cards)

Six criteria: *Refinery Grade Compatibility, Tanker Availability, Port Congestion Index, Landed Cost Profile, Transit Lead Time, Geopolitical Hazard Delta.*

1. **Normalize:** `r_ij = x_ij / √(Σ x_ij²)`
2. **Weighted matrix:** `v_ij = w_j · r_ij`
3. **Euclidean distance to ideals:** `D_i⁺ = √(Σ(v_ij − v_j⁺)²)`, `D_i⁻ = √(Σ(v_ij − v_j⁻)²)`
4. **Score:** `C_i = D_i⁻ / (D_i⁺ + D_i⁻)`

**Output is not a bare ranking — it is an executable Procurement Card** (PS2 demands recommendations "teams can act on within hours"):

```json
{
  "rank": 1,
  "supplier_route": "Saudi Aramco — Ras Tanura → Jamnagar",
  "heuristic_score": 0.81,
  "landed_cost_usd_bbl": 84.20,
  "lead_time_days": 7,
  "vessel_class": "VLCC",
  "grade_compatibility": "HIGH (Arab Heavy match 0.90)",
  "compliance_status": "CLEAR",
  "action_window": "executable within 6h"
}
```

### D. SPR Drawdown Optimizer (NEW — C2, replaces depletion-only curve)

Models India's Strategic Petroleum Reserve as a **decision problem**, not an obituary chart.

**Anchors (stated as explicit, testable assumptions in the X-Ray):**
- SPR cover: **9.5 days** of national consumption (per the problem statement); `S_0 = 9.5 × daily_consumption`.
- A second mode models **SPR + commercial stocks (~60+ days)** — the two modes are always distinguished on the chart.
- Reserve floor: `S_min = 0.20 × S_0` (hard constraint — prevents the trivial "draw forever" loophole).
- Replenishment window `W`: static heuristic 45–90 days, labeled assumption.

**Candidate strategies** (each yields an x,y depletion array):
- **S1 — Max Immediate:** draw at full gap rate `g` until floor → longest *full* coverage.
- **S2 — Phased:** draw at `0.5g` (partial substitution) → extended calendar coverage with managed shortfall.
- **S3 — Delayed Trigger:** hold X days (decision latency), then max draw → models political reality.

**Objective:** maximize days of full supply coverage before `W`, subject to `S(t) ≥ S_min`; tie-break by minimum unmet-demand integral `∫ shortfall(t) dt`. Output: recommended strategy ID, coverage days, and all three curve arrays for the comparative chart.

**Triggering:** none required. The optimizer is a pure function of the Stage 1 extraction (`volume_lost_mbd`, `duration_days`) and runs inside every Stage 3 pass, including Hover-to-Argue recomputes.

### E. National Economic Cascade (NEW — C3)

Extends the impact chain past the refinery gate to the level PS2 scores (Business Impact, 25%): *refinery run rates → domestic fuel prices → power sector stress → GDP trajectory.* All elasticities are static heuristic defaults, user-adjustable, and disclosed in the X-Ray.

| Output | Heuristic Default | Label |
|---|---|---|
| Pump price impact | `ΔP × ₹0.55/litre` (crude-cost pass-through, pre-tax shielding) | Heuristic estimate |
| Power sector stress | flag `ELEVATED` if landed crude premium > 15% sustained | Threshold heuristic |
| GDP impact | `ΔP × 1.2 bps × (duration_days / 90)` | Heuristic estimate |

### F. Composite Supply Chain Risk Index (SCRI)

`SCRI = 0.35·Exposure + 0.25·Dependency + 0.20·Corridor Hazard + 0.20·Criticality` (normalized 0–1). The X-Ray states plainly: *"Weights are heuristic estimates configured for the hackathon baseline, not a published academic formula."*

---

## 4. DATA SCHEMAS & STATEFUL MEMORY

PostgreSQL (SQLite acceptable for local dev). Supports Hover-to-Argue state rollbacks and the signal-latency metric.

```sql
-- Core Session State
CREATE TABLE argus_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    trigger_type VARCHAR(50) NOT NULL,      -- 'LIVE_SIGNAL', 'CACHED_SCENARIO', 'MANUAL_PROMPT'
    incident_corridor VARCHAR(100),
    raw_ingested_content TEXT NOT NULL,
    extracted_variables JSONB NOT NULL,     -- Stage 1 output
    deterministic_state JSONB NOT NULL,     -- Stage 3 output
    status VARCHAR(50) NOT NULL
);

-- Claims Auditing
CREATE TABLE argus_extracted_claims (
    claim_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES argus_sessions(session_id),
    extracted_text TEXT NOT NULL,
    source_url TEXT NOT NULL,
    verification_status VARCHAR(50) NOT NULL
);

-- Signal Latency Metric (NEW — C1)
CREATE TABLE argus_signal_events (
    signal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES argus_sessions(session_id),
    signal_source VARCHAR(50) NOT NULL,     -- 'LIVE_SIGNAL_BUTTON'
    t_signal TIMESTAMPTZ NOT NULL,
    t_recommendation TIMESTAMPTZ            -- written when briefing renders
);
```

**Pydantic extraction schema (with C7 physical bound):**

```python
class ExtractionSchema(BaseModel):
    corridor: str
    commodity: str = "crude_oil"
    economy: str = "IN"
    volume_lost_mbd: float = Field(ge=0.0, le=21.0)  # Hormuz total ≈ 20–21 mbd
    duration_days: int = Field(ge=1, le=180)
    confidence: float = Field(ge=0.0, le=1.0)
```

**Unit display convention (C7):** UI and narrative always render `15 mbd`. The string `"15M mbd"` is banned — `mbd` already means million barrels/day.

---

## 5. THE BESPOKE STRATEGIC BRIEFING UI

React/Next.js, deployed on Vercel.

```text
+---------------------------------------------------------------------------------------+
|  ARGUS COMMAND PANEL      [ ⚡ LIVE SIGNAL ] [ SCENARIOS ▾ ] [ EXPORT BRIEFING PDF ] |
|  Signal → Recommendation: 03m 41s                                                     |
+---------------------------------------------------------------------------------------+
|                                       |                                               |
|  LEFT PANEL: STRATEGIC INTEL (60%)    |  RIGHT PANEL: VISUAL EVIDENCE (40%)           |
|                                       |                                               |
|  BLUF: High-risk disruption in the    |  [ 3D SATELLITE MAP — Mapbox ]                |
|  Strait of Hormuz. Daily exposure     |   - Blocked route     [ RED VECTOR ]          |
|  ₹ 412 crore/day at Jamnagar.         |   - MCDA priority     [ GREEN VECTOR ]        |
|                                       |   - Tankers           [ LIVE AIS DOTS ]       |
|  Narrative with [CLAIM] hover tags... |                                               |
|                                       |  [ SPR DRAWDOWN STRATEGIES ]                  |
|  [Scenario A — Worst Case]            |  100%┤╲ S1 max                                |
|  (rendered only when D-Shield         |      │ ╲╲ S2 phased                           |
|   variance=True)                      |   FLR├─ ─ ─S_min 20% floor─ ─ ─               |
|    volume lost 15 mbd → ...           |    0 └┬────┬────┬────┬────┬────┬──            |
|                                       |    0    10   20   30   40   50  days         |
|  [Scenario B — Base Case]             |   Recommended: S2 — coverage 34 days          |
|  official baseline 9.1 mbd → ...      |                                               |
|                                       |  [ PROCUREMENT CARDS — HEURISTIC RANKED ]      |
|  [ NATIONAL ECONOMIC CASCADE ]        |  #1 Ras Tanura→Jamnagar  $84.2  7d  CLEAR     |
|  Pump: +₹3.4/litre | Power: ELEVATED  |  #2 Bonny→Paradip        $86.9 19d  CLEAR     |
|  GDP: −18 bps (heuristic)             |  ✕ NIOC — COMPLIANCE-BLOCKED                  |
|                                       |                                               |
|                                       |  [ OSINT TICKER ]  [Unverified]/[Verified]    |
|                                       |  [ MATH X-RAY ▾ Data Origin Matrix + NumPy ]  |
+---------------------------------------------------------------------------------------+
```

### Advanced UI Interaction Mechanics

- **⚡ LIVE SIGNAL button (C1):** Fires the cached breaking event, starts the on-screen timer, runs the full pipeline, freezes the timer when the briefing renders. The banner *is* the "end-to-end response time" evaluation metric, made visible.
- **Hover-to-Argue Engine:** Narrative parsed for `[CLAIM]` tags. Hover → citation metadata. Click → counterfactual input (*"Assume volume lost is 15 mbd"*) → POST to FastAPI → `extracted_variables` updated → Stage 3 re-runs (cost, Heuristic Ranking, SPR strategies, cascade all shift) → screen updates instantly.
- **Geospatial Canvas:** `react-map-gl` on `mapbox://styles/mapbox/satellite-streets-v12`; live AIS telemetry overlaid (cached snapshot if the socket drops).
- **PDF Export:** Native CSS `@media print` strips sidebars and formats map + charts to A4. No backend rendering.
- **SPR chart** always shows all three strategy curves, the 20% floor line, both inventory modes (SPR-only vs SPR+commercial), and the optimizer's recommendation.

---

## 6. DEMO-DAY SIGNAL MODE (Replaces Continuous Monitoring)

**Decision:** The continuous watch-loop (polling Serper + AIS anomaly scoring on a cron) is **deferred to the post-hackathon roadmap** — API-call cost is unjustified for the event.

**What ships instead:** the LIVE SIGNAL button (Section 5). One cached breaking-event JSON, one pipeline run, near-zero cost, fully deterministic — and the judges still see the signal-to-recommendation latency metric on screen, which is the only form of "detection lead time" demonstrable in a 5-minute demo.

**Demo script:** open dashboard → click ⚡ LIVE SIGNAL → narrate while the pipeline stages light up → briefing lands at ~3–4 min → walk the cascade panel and procurement cards → fire one Hover-to-Argue counterfactual to show stateful recompute → export PDF.

---

## 7. DEPLOYMENT TOPOLOGY (C6)

```text
  Vercel (frontend)                    Azure (backend — ALWAYS-ON)
  ┌────────────────────┐   HTTPS     ┌─────────────────────────────┐
  │ Next.js Command    │ ──────────► │ FastAPI (Container Apps /    │
  │ Center UI          │ ◄────────── │  App Service / VM)           │
  │ Mapbox, Recharts   │   JSON      │  ├── Stage 3 NumPy engine    │
  └────────────────────┘             │  ├── AISstream WebSocket ────┼──► persistent
                                     │  ├── Agent 1 / Agent 5       │    socket
                                     │  └── PostgreSQL              │
                                     └─────────────────────────────┘
```

**Hard rule:** the FastAPI backend must never be deployed to Vercel. Vercel serverless functions cannot hold the persistent AIS WebSocket — the live vessel layer would die silently. Frontend on Vercel, backend + database on Azure. Non-negotiable.

---

## 8. SCALABILITY MODEL (C8) — The 15% Answer

Scalability is answered by **configuration, not code**. Every corridor is a single JSON file:

```json
{
  "corridor_id": "hormuz",
  "display_name": "Strait of Hormuz",
  "throughput_mbd": 20.5,
  "india_exposure_share": 0.42,
  "ais_bounding_box": [[24.0, 54.0], [27.5, 58.5]],
  "freight_markup_matrix": { "jamnagar": 1.8, "paradip": 2.6 },
  "grade_penalty_table": { "heavy_sour": 2.2, "medium_sour": 1.1 },
  "baseline_flow_mbd": 17.0
}
```

Pitch line for judges: *"Adding a new corridor — Bab el-Mandeb, Malacca, anything — is adding one JSON file. No code changes."* The sanctions list, elasticity table, and refinery configs are likewise flat JSON. That is the entire scalability story, and it is true.

---

## 9. SPRINT IMPLEMENTATION TRACKS (Revised — 3 Developers)

**Sprint 1 — Core Infra & Schemas** *(Dev 3 lead)*
1. Init FastAPI + Next.js repos; Azure + Vercel skeleton deploys (C6).
2. PostgreSQL tables: `argus_sessions`, `argus_extracted_claims`, `argus_signal_events` (C1).
3. Pydantic `ExtractionSchema` with mbd ≤ 21 bound (C7); `MathStateSchema`.
4. Corridor config JSONs ×3 (Hormuz default) (C8); `sanctions_snapshot.json` (C4).

**Sprint 2 — Deterministic Engine & Telemetry** *(Dev 1 lead)*
1. AISstream.io WebSocket client + geo-filter + **cached AIS snapshot fallback**.
2. Cost delta `C_Δ` with dual $/₹-crore output (C3).
3. Sanctions pre-filter → Heuristic Ranking → Procurement Card JSON (C4).
4. SPR Drawdown Optimizer: S1/S2/S3 strategies, 20% floor, recommendation logic (C2).
5. Economic cascade module: ₹/litre, power flag, GDP bps (C3).

**Sprint 3 — AI Agents & Validation** *(Dev 3 lead)*
1. Agent 1 extraction via `with_structured_output` → Pydantic schema.
2. D-Shield variance gate (>20% deviation → `variance=True`).
3. Agent 5 synthesis with `[CLAIM id="" source=""]` tagging; A/B branching only when gated.
4. Python regex validator: citation hard-check + math string-match → `ValueError` on failure.
5. `POST /api/signal` endpoint: cached event load, `t0`/`t1` timestamps, latency return (C1).

**Sprint 4 — Command Center + Deliverables** *(Dev 2 lead, all hands at the end)*
1. Mapbox satellite layer, AIS scatterplot, route vectors.
2. Recharts: SPR strategy curves + floor line; cascade panel; procurement cards; compliance-blocked row.
3. LIVE SIGNAL button + latency banner; Hover-to-Argue wiring to recompute endpoint.
4. `@media print` PDF export.
5. **Mandatory deliverables block (do not skip):** proper architecture diagram (not ASCII), presentation deck, demo video. Reserve the final half-day. The demo video is insurance against live-demo failure.

---

## 10. JUDGING CRITERIA MAP

| Criterion (Weight) | ARGUS v5.0 Answer | Where Shown |
|---|---|---|
| Innovation (25%) | Epistemic split (LLMs never do math), regex claim-validator, D-Shield gated OSINT, Hover-to-Argue | Live demo + architecture diagram |
| Business Impact (25%) | ₹ crore/day exposure, national cascade (pump/power/GDP), executable procurement cards | Cascade panel + cards |
| Technical Excellence (20%) | Deterministic NumPy engine, Pydantic hard bounds, Heuristic Ranking, SPR optimizer, WebSocket AIS | Math X-Ray |
| Scalability (15%) | Config-driven corridors — "new corridor = one JSON" | Deck slide + config file |
| User Experience (15%) | Command-center UI, 3D map, live latency banner, one-click PDF | Live demo |

| PS2 Evaluation Focus | Answer |
|---|---|
| Signal→recommendation response time | LIVE SIGNAL latency banner |
| Procurement alternative quality/executability | Procurement Cards with cost, lead time, vessel class, compliance |
| Scenario fidelity (explicit, testable assumptions) | Math X-Ray Data Origin Matrix — every variable origin-classed |
| Geospatial evidence depth | Satellite map + live/cached AIS telemetry |
| Signal detection lead time | Demo-mode latency (full continuous watch = roadmap, stated honestly) |

---

## 11. RISKS & KNOWN LIMITS

- **Name collision:** "Argus" is also Argus Media, the energy pricing agency. Prepared one-liner: *"Argus Panoptes — the all-seeing watcher."* Rename only if a judge pushes.
- **AIS free tier:** rate limits and Hormuz-box traffic volume may strain the socket → cached snapshot fallback is mandatory, and the demo script must survive on it.
- **Heuristic disclosures:** SCRI weights, elasticities, replenishment windows, and `fx` are labeled assumptions in the X-Ray. This honesty is a scoring feature under "testable assumptions" — never hide it.
- **OSINT epistemics:** OSINT can trigger narrative branching but never touches Stage 3 math. State this in the pitch; it pre-empts the "fake tweet triggers false alarm" attack.

---

## 12. FUTURE ROADMAP (Post-Hackathon — say this when judges ask "what's next")

1. **Continuous corridor watch loop** — cron-polled Serper + AIS anomaly scoring that auto-fires the pipeline on threshold breach (deferred from v5.0 for API cost; design already specced).
2. **Knowledge graph** of supplier–route–risk–refinery relationships backing the Heuristic matrices.
3. **Thread D multi-modal parser** (PyMuPDF + vision) for incident PDFs/imagery.
4. **Live sanctions list ingestion** (OFAC/EU APIs) replacing the static snapshot.
5. **Replenishment-window estimation** from real tender and freight data.

---

*ARGUS v5.0 — build-locked. Deviation requires team sign-off.*
