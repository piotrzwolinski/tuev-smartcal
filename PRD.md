# SmartCal@EG — Product Requirements Document

**Version:** 1.0
**Date:** 2026-03-11
**Target:** MVP demo for TÜV SÜD deep-dive call, KW12 (March 16, 2026)

---

## 1. Problem Statement

TÜV SÜD's Elektro- und Gebäudetechnik (EG) division needs a tool that generates **inspection service price estimates** based on building parameters. Currently this requires manual lookup across multiple catalogs and expert knowledge of cross-dependencies between services.

## 2. Solution

A **graph-based pricing agent** that:
- Stores services, pricing rules, estimation formulas, and causal relationships in a knowledge graph (FalkorDB)
- Uses a **ReAct agent** (LLM + generic graph navigation tools) to traverse the graph and compute prices
- Shows the calculation trace in real-time via SSE streaming
- Requires **zero hardcoded domain logic** — all intelligence lives in the graph

## 3. Architecture

```
┌──────────────────┐    SSE     ┌──────────────────┐   Cypher   ┌──────────────┐
│   Next.js UI     │ ◄────────► │   FastAPI Backend │ ◄────────► │   FalkorDB   │
│   (super simple) │            │   + ReAct Agent   │            │   "smartcal"  │
└──────────────────┘            │   + Gemini LLM    │            └──────────────┘
                                └──────────────────┘
```

### 3.1 Stack
| Layer | Technology | Notes |
|-------|-----------|-------|
| Graph DB | FalkorDB | Named graph `smartcal`, same instance as HVAC project |
| Backend | FastAPI + Python 3.12 | Lightweight, async |
| LLM | Google Gemini (google-genai SDK) | Function calling for tool use |
| Frontend | Next.js 15 + Tailwind | Single-page, minimal |
| Streaming | SSE (Server-Sent Events) | Real-time agent trace |

### 3.2 Graph Schema Summary
| Element | Count | Examples |
|---------|-------|---------|
| Node labels | 14 | Dienstleistung, Preisposition, Merkmal, Stressor, Trait, Gebaeudetyp, ... |
| Relationship types | 17 | HAT_PREISPOSITION, SCHAETZT, GLEICHE_BEGEHUNG, EXPOSES_TO, DEMANDS_TRAIT, AFFECTS, ... |
| Total nodes | ~130 | 11 services, 12 Stressors, 9 Traits, pricing tiers, ... |
| Total edges | ~210 | Cross-cutting: bundles, estimation chains, causal chains |

### 3.3 Key Graph Features (Demonstrating "Power of the Graph")
1. **SCHAETZT chains**: BGF → estimates multiple service quantities via formulas (fan-out)
2. **GLEICHE_BEGEHUNG**: Bundle discovery — services sharing site visits → discount
3. **LOEST_AUS**: Combinatorial risk detection (e.g., Tiefgarage + Wallbox → ATEX surcharge)
4. **EXPOSES_TO / DEMANDS_TRAIT / AFFECTS**: Causal reasoning (Stressor → Trait → Service impact)
5. **EMPFIEHLT**: Cross-sell discovery from graph relationships
6. **ERFORDERT_PRUEFUNG**: Mandatory services by building type

### 3.4 ReAct Agent
- **7 generic tools**: `get_schema`, `find_nodes`, `follow_edges`, `find_paths`, `find_internal_edges`, `evaluate`, `check_completeness`
- **Max 15 steps** with forced finish fallback
- **Scratchpad**: Working memory for facts, gaps, positions, surcharges, discounts
- **No domain knowledge in code** — graph structure guides reasoning

## 4. API Specification

### 4.1 Endpoints

#### `POST /api/calculate`
Start a new calculation with SSE streaming.

**Request:**
```json
{
  "input": "Bürogebäude, 5.000m² BGF, 3 Etagen, 2 Aufzüge, Tiefgarage mit 15 Wallboxen",
  "params": {
    "gebaeudetyp": "Bürogebäude",
    "bgf_m2": 5000,
    "etagen": 3,
    "aufzuege": 2,
    "wallboxen": 15,
    "tiefgarage": true
  }
}
```

**Response:** SSE stream with events:
```
event: step
data: {"step": 1, "action": "get_schema", "params": {}, "result_summary": "14 node types, 17 rel types"}

event: step
data: {"step": 2, "action": "find_nodes", "params": {"label": "Gebaeudetyp"}, "result_summary": "5 results"}

event: thinking
data: {"step": 3, "reasoning": "Bürogebäude found. Now checking mandatory services..."}

...

event: result
data: {"kalkulation": {...}, "trace": [...], "steps": 12}
```

#### `GET /api/health`
Health check — verifies FalkorDB connection and graph existence.

#### `POST /api/graph/load`
Load/reload the graph schema from `graph_schema.cypher`.

## 5. Frontend Specification

**Design principle:** "Megaprosty" — super simple, one page.

### 5.1 Layout
```
┌─────────────────────────────────────────────────┐
│  SmartCal@EG                        [TÜV SÜD]  │
├────────────────────┬────────────────────────────┤
│                    │                            │
│  INPUT PANEL       │  RESULT PANEL              │
│                    │                            │
│  Gebäudetyp: [▼]   │  Agent Trace (collapsible) │
│  BGF (m²): [____]  │  ├─ Step 1: get_schema     │
│  Etagen: [____]    │  ├─ Step 2: find_nodes     │
│  Aufzüge: [____]   │  └─ ...                    │
│  Wallboxen: [____] │                            │
│  ☐ Tiefgarage      │  Kalkulation               │
│  ☐ BMA vorhanden   │  ┌──────────────────────┐  │
│  ☐ PV-Anlage       │  │ Position  │ Betrag   │  │
│                    │  │ DGUV V3   │ 2.450€   │  │
│  [Berechnen]       │  │ Aufzug HP │ 1.200€   │  │
│                    │  │ ...       │ ...      │  │
│                    │  │───────────│──────────│  │
│                    │  │ Gesamt    │11.071€   │  │
│                    │  └──────────────────────┘  │
│                    │                            │
│                    │  Rückfragen (yellow)        │
│                    │  Empfehlungen (blue)        │
└────────────────────┴────────────────────────────┘
```

### 5.2 Input Fields
| Field | Type | Default | Notes |
|-------|------|---------|-------|
| Gebäudetyp | Dropdown | — | Bürogebäude, Industriegebäude, Wohngebäude, Krankenhaus, Schule |
| BGF (m²) | Number | — | Required |
| Etagen | Number | 1 | |
| Aufzüge | Number | 0 | |
| Wallboxen | Number | 0 | |
| Tiefgarage | Checkbox | false | |
| BMA vorhanden | Checkbox | false | Brandmeldeanlage |
| PV-Anlage | Checkbox | false | Photovoltaik |
| Sprinkleranlage | Checkbox | false | |
| RLT-Anlage | Checkbox | false | Raumlufttechnik |

### 5.3 Result Display
1. **Agent Trace** — collapsible panel showing each step (tool call + result summary)
2. **Kalkulation Table** — positions, surcharges, discounts, total
3. **Rückfragen** — yellow info boxes with questions for the customer
4. **Empfehlungen** — blue info boxes with cross-sell suggestions
5. **Facts** — provenance trail showing where each number came from

## 6. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Calculation time | < 30s (agent loop) |
| Max agent steps | 15 |
| Graph load time | < 5s |
| No auth required | MVP only |
| Single user | MVP only |

---

## 7. Implementation Plan

### Step 1: Graph Loading (`backend/load_graph.py`)
**Files:** `backend/load_graph.py`
**What:** Script to load `graph_schema.cypher` into FalkorDB named graph `smartcal`.
**Test:**
- `test_graph_loaded`: After loading, verify node count ≥ 120, edge count ≥ 200
- `test_node_labels`: Verify all 14 expected labels exist
- `test_sample_service`: Query `DL_DGUV_ORTV` and verify properties
- `test_schaetzt_edges`: Verify BGF estimation chain exists (MERK_BGF has SCHAETZT edges)

### Step 2: LLM Client (`backend/llm.py`)
**Files:** `backend/llm.py`
**What:** Thin wrapper around `google-genai` SDK with function-calling support. Adapts Gemini's tool calling format to the agent's expected interface.
**Test:**
- `test_llm_chat_basic`: Send a simple message, get a response
- `test_llm_tool_calling`: Send a message with tool schemas, verify tool_calls in response

### Step 3: FastAPI Server (`backend/main.py`)
**Files:** `backend/main.py`
**What:** FastAPI app with `/api/calculate` (SSE), `/api/health`, `/api/graph/load` endpoints. The calculate endpoint runs the ReAct agent and streams steps via SSE.
**Test:**
- `test_health`: GET `/api/health` returns 200 with graph info
- `test_calculate_sse`: POST `/api/calculate` returns SSE stream with step events and final result event
- `test_graph_load_endpoint`: POST `/api/graph/load` triggers schema reload

### Step 4: Agent Integration Test
**Files:** `backend/tests/test_agent_integration.py`
**What:** End-to-end test: load graph → run agent with known input → verify output structure.
**Test:**
- `test_buerogebaeude_scenario`: Input "Bürogebäude, 5000m² BGF, 3 Etagen, 2 Aufzüge" → verify kalkulation has positionen, gesamtbetrag > 0, facts trail
- `test_agent_discovers_bundles`: Verify GLEICHE_BEGEHUNG relationships are found
- `test_agent_completeness`: Verify check_completeness reports no missed rels
- `test_atex_surcharge`: Input with Tiefgarage + Wallboxen → verify ATEX Zuschlag present

### Step 5: Frontend (`frontend/`)
**Files:** `frontend/app/page.tsx`, `frontend/app/layout.tsx`, `frontend/app/globals.css`, `frontend/components/InputPanel.tsx`, `frontend/components/ResultPanel.tsx`, `frontend/components/AgentTrace.tsx`, `frontend/components/KalkulationTable.tsx`
**What:** Next.js app with input form, SSE connection, and result display.
**Test:**
- Manual: Fill form → click Berechnen → see trace stream → see result table
- `test_sse_connection`: Verify EventSource connects and receives events
- `test_form_validation`: BGF and Gebäudetyp are required

### Step 6: Polish & Demo Prep
- Loading states and error handling
- Responsive layout
- Demo scenario pre-filled
- Deploy instructions

---

## 8. File Structure

```
tuev/
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── main.py              ← FastAPI server + SSE
│   ├── database.py          ← FalkorDB connection (done)
│   ├── llm.py               ← Gemini wrapper
│   ├── load_graph.py        ← Graph schema loader
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── tools.py         ← 7 generic tools (done)
│   │   ├── react_agent.py   ← ReAct loop (done)
│   │   └── example_trace.md
│   ├── database/
│   │   ├── graph_schema.cypher
│   │   └── example_traversals.cypher
│   └── tests/
│       ├── test_graph.py
│       ├── test_agent.py
│       └── test_api.py
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   └── components/
│       ├── InputPanel.tsx
│       ├── ResultPanel.tsx
│       ├── AgentTrace.tsx
│       └── KalkulationTable.tsx
└── PRD.md
```

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Agent takes too many steps / loops | max_steps=15 + forced finish |
| Gemini doesn't call tools correctly | Fallback: retry with clearer prompt |
| Graph too complex for 15 steps | Tune graph or increase limit |
| FalkorDB connection issues | Health check endpoint + clear error messages |
| LLM hallucinates prices | check_completeness verifies all from graph |

## 10. Success Criteria (MVP)

1. User enters building parameters → gets price estimate in < 30s
2. Agent trace visible in UI showing graph navigation
3. At least 3 cross-cutting graph features demonstrated (bundles, estimation chains, causal detection)
4. No hardcoded prices or domain logic in code
5. TÜV SÜD can see the demo and understand the graph approach
