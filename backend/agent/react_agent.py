"""
SmartCal Graph Agent — ReAct Loop

The agent knows NOTHING about TÜV SÜD, pricing, or inspections.
It receives the graph ONTOLOGY in its system prompt and navigates
the graph using 7 generic tools. The graph structure itself
guides the agent's reasoning.

Key difference from hardcoded pipeline:
  - Agent decides what to explore next based on what it sees
  - New node types / relationship types → agent discovers them automatically
  - No code changes needed for new domains
  - Completeness is verified by the graph itself, not by the code
"""

import json
import math
import time
from dataclasses import dataclass, field
from typing import Literal


# ---------------------------------------------------------------------------
# Scratchpad — the agent's working memory
# ---------------------------------------------------------------------------

@dataclass
class Fact:
    claim: str
    source: Literal["GRAPH", "CALCULATED", "ESTIMATED"]
    node_ids: list[str] = field(default_factory=list)
    confidence: str = "high"  # high = direct from graph, medium = estimated


@dataclass
class Scratchpad:
    """Agent's working memory. Accumulates facts, gaps, and prices."""
    facts: list[Fact] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    positionen: list[dict] = field(default_factory=list)  # price line items
    zuschlaege: list[dict] = field(default_factory=list)
    rabatte: list[dict] = field(default_factory=list)
    rueckfragen: list[str] = field(default_factory=list)
    empfehlungen: list[dict] = field(default_factory=list)
    explored_rels: set = field(default_factory=set)

    def add_fact(self, claim: str, source: str = "GRAPH", node_ids: list = None):
        self.facts.append(Fact(claim=claim, source=source, node_ids=node_ids or []))

    def add_gap(self, description: str):
        self.gaps.append(description)

    def add_position(self, **kwargs):
        self.positionen.append(kwargs)

    def add_zuschlag(self, **kwargs):
        self.zuschlaege.append(kwargs)

    def add_rabatt(self, **kwargs):
        self.rabatte.append(kwargs)

    def total(self) -> float:
        base = sum(p.get("betrag", 0) for p in self.positionen)
        zuschlaege = sum(z.get("betrag", 0) for z in self.zuschlaege)
        rabatte = sum(r.get("betrag", 0) for r in self.rabatte)
        return base + zuschlaege - rabatte


# ---------------------------------------------------------------------------
# System Prompt — ONLY the ontology, no domain logic
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a graph navigation agent. You explore a knowledge graph
to produce a complete Kalkulation (price calculation) for building inspection services.

## YOUR TOOLS
You have 7 tools:
- get_schema: See what node types and relationship types exist. START HERE.
- find_nodes: Find nodes by label and filters.
- follow_edges: From a node, follow outgoing/incoming edges. Your PRIMARY tool.
- find_paths: Multi-hop traversal (e.g. estimation chains).
- find_internal_edges: Find relationships BETWEEN a set of nodes (bundle discovery).
- evaluate: Calculate math expressions.
- check_completeness: Verify you haven't missed relationship types.

## YOUR TASK
Given user input (building parameters), produce a complete Kalkulation:
1. Explore the graph to understand its structure
2. Identify which services (Dienstleistung) are relevant
3. For each service, find ALL price components and applicable volume tiers
4. Discover cross-cutting relationships (bundles, surcharges, recommendations)
5. Compute the total price
6. Verify completeness

## CRITICAL RULES
- Do NOT guess prices. Every number must come from the graph or from evaluate().
- Do NOT skip relationship types. If a node has edges you haven't explored, explore them.
- When you see a SCHAETZT edge with a formula, use evaluate() to compute the estimate.
- When you see GLEICHE_BEGEHUNG, calculate the Bündelrabatt.
- When you see LOEST_AUS with a bedingung, check if the condition is met.
- After computing all prices, call check_completeness to verify nothing was missed.

## PERFORMANCE — BATCH YOUR TOOL CALLS
- You can call MULTIPLE tools in a single turn. DO THIS whenever possible!
- Example: after identifying 5 services, call follow_edges for ALL 5 in one turn.
- Example: call find_nodes for multiple labels at once (separate calls, same turn).
- NEVER call follow_edges one node at a time when you have multiple nodes to explore.
- Group related queries: e.g. get all HAT_PREISPOSITION edges in one turn, then all HAT_STAFFEL in the next.
- Aim for 8-12 total turns, not 25+. Batch aggressively.

## OUTPUT FORMAT
After FINISH, output a JSON Kalkulation with:
- positionen: [{dienstleistung, beschreibung, menge, einheitspreis, betrag}]
- zuschlaege: [{name, grund, betrag}]
- rabatte: [{name, grund, betrag}]
- anfahrt: {typ, betrag}
- gesamtbetrag: number
- rueckfragen: [string] — questions for the customer
- empfehlungen: [{dienstleistung, grund, geschaetzter_preis}]
- facts: [{claim, source}] — provenance trail
"""


# ---------------------------------------------------------------------------
# Tool Executor — translates tool calls to Cypher
# ---------------------------------------------------------------------------

class ToolExecutor:
    """Executes agent tool calls against FalkorDB. Domain-agnostic."""

    def __init__(self, db):
        self.db = db

    async def execute(self, tool_name: str, params: dict) -> dict:
        match tool_name:
            case "get_schema":
                return await self._get_schema()
            case "find_nodes":
                return await self._find_nodes(**params)
            case "follow_edges":
                return await self._follow_edges(**params)
            case "find_paths":
                return await self._find_paths(**params)
            case "find_internal_edges":
                return await self._find_internal_edges(**params)
            case "evaluate":
                return self._evaluate(**params)
            case "check_completeness":
                return await self._check_completeness(**params)
            case _:
                return {"error": f"Unknown tool: {tool_name}"}

    async def _get_schema(self) -> dict:
        nodes = await self.db.query(
            "MATCH (n) "
            "WITH labels(n)[0] AS label, count(n) AS cnt "
            "RETURN label, cnt ORDER BY cnt DESC"
        )
        rels = await self.db.query(
            "MATCH (a)-[r]->(b) "
            "WITH type(r) AS rel, labels(a)[0] AS from_l, labels(b)[0] AS to_l, count(*) AS cnt "
            "RETURN rel, from_l, to_l, cnt ORDER BY cnt DESC"
        )
        return {"node_types": nodes, "relationship_types": rels}

    async def _find_nodes(self, label: str, filters: dict = None, limit: int = 50) -> dict:
        where_parts = []
        params = {"limit": limit}

        if filters:
            for i, (key, value) in enumerate(filters.items()):
                param_name = f"fv_{i}"
                where_parts.append(f"n.{key} = ${param_name}")
                params[param_name] = value

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        query = f"MATCH (n:{label}) {where_clause} RETURN properties(n) AS props LIMIT $limit"

        results = await self.db.query(query, **params)
        return {"nodes": results, "count": len(results)}

    async def _follow_edges(
        self, node_id: str, rel_type: str = None, direction: str = "out"
    ) -> dict:
        rel_filter = f":{rel_type}" if rel_type else ""

        if direction == "out":
            query = (
                f"MATCH (n {{id: $node_id}})-[r{rel_filter}]->(target) "
                "RETURN type(r) AS rel_type, properties(r) AS rel_props, "
                "labels(target)[0] AS target_label, target.id AS target_id, "
                "properties(target) AS target_props"
            )
        elif direction == "in":
            query = (
                f"MATCH (n {{id: $node_id}})<-[r{rel_filter}]-(source) "
                "RETURN type(r) AS rel_type, properties(r) AS rel_props, "
                "labels(source)[0] AS source_label, source.id AS source_id, "
                "properties(source) AS source_props"
            )
        else:  # both
            query = (
                f"MATCH (n {{id: $node_id}})-[r{rel_filter}]-(other) "
                "RETURN type(r) AS rel_type, properties(r) AS rel_props, "
                "labels(other)[0] AS other_label, other.id AS other_id, "
                "properties(other) AS other_props"
            )

        results = await self.db.query(query, node_id=node_id)
        return {"edges": results, "count": len(results)}

    async def _find_paths(
        self,
        from_id: str,
        target_label: str = None,
        target_id: str = None,
        rel_types: list = None,
        max_hops: int = 3,
    ) -> dict:
        target_filter = ""
        if target_label:
            target_filter = f":{target_label}"
        if target_id:
            target_filter += f" {{id: '{target_id}'}}"

        # Build relationship type filter
        rel_pattern = f"*1..{max_hops}"
        if rel_types:
            rel_type_str = "|".join(rel_types)
            rel_pattern = f":{rel_type_str}*1..{max_hops}"

        query = (
            f"MATCH path = (start {{id: $from_id}})-[{rel_pattern}]->(end{target_filter}) "
            "RETURN [n IN nodes(path) | {id: n.id, label: labels(n)[0]}] AS nodes, "
            "[r IN relationships(path) | {type: type(r), props: properties(r)}] AS edges, "
            "length(path) AS hops "
            "ORDER BY hops ASC LIMIT 20"
        )
        results = await self.db.query(query, from_id=from_id)
        return {"paths": results, "count": len(results)}

    async def _find_internal_edges(
        self, node_ids: list, rel_type: str = None
    ) -> dict:
        rel_filter = f":{rel_type}" if rel_type else ""
        query = (
            f"MATCH (a)-[r{rel_filter}]->(b) "
            "WHERE a.id IN $node_ids AND b.id IN $node_ids "
            "RETURN a.id AS from_id, type(r) AS rel_type, "
            "properties(r) AS rel_props, b.id AS to_id"
        )
        results = await self.db.query(query, node_ids=node_ids)
        return {"edges": results, "count": len(results)}

    def _evaluate(self, expression: str, variables: dict) -> dict:
        """Safe math evaluation — no exec/eval, only math operations."""
        try:
            # Build a safe namespace with only math functions
            safe_ns = {
                "__builtins__": {},
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "ceil": math.ceil,
                "floor": math.floor,
                "CEIL": math.ceil,
                "FLOOR": math.floor,
                **variables,
            }
            # Sanitize: only allow math-like expressions
            allowed_chars = set("0123456789+-*/()._ ,")
            expr_check = expression
            for var_name in variables:
                expr_check = expr_check.replace(var_name, "")
            for func_name in ["abs", "round", "min", "max", "ceil", "floor", "CEIL", "FLOOR"]:
                expr_check = expr_check.replace(func_name, "")

            if not all(c in allowed_chars for c in expr_check):
                return {"error": f"Unsafe expression: {expression}"}

            result = eval(expression, safe_ns)  # noqa: S307
            return {"expression": expression, "variables": variables, "result": round(result, 2)}
        except Exception as e:
            return {"error": str(e)}

    async def _check_completeness(
        self, service_ids: list, explored_rel_types: list
    ) -> dict:
        query = (
            "MATCH (dl:Dienstleistung)-[r]->(target) "
            "WHERE dl.id IN $service_ids "
            "WITH type(r) AS rel_type, count(*) AS edge_count, "
            "collect(DISTINCT labels(target)[0]) AS target_labels "
            "RETURN rel_type, edge_count, target_labels, "
            "CASE WHEN rel_type IN $explored THEN 'EXPLORED' ELSE 'MISSED' END AS status "
            "ORDER BY status DESC, edge_count DESC"
        )
        results = await self.db.query(
            query, service_ids=service_ids, explored=explored_rel_types
        )
        missed = [r for r in results if r.get("status") == "MISSED"]
        return {
            "all_rel_types": results,
            "missed": missed,
            "is_complete": len(missed) == 0,
        }


# ---------------------------------------------------------------------------
# ReAct Agent Loop
# ---------------------------------------------------------------------------

class GraphReActAgent:
    """
    ReAct agent that navigates a knowledge graph using generic tools.

    The agent:
    1. Receives user input (building parameters)
    2. Explores the graph schema
    3. Navigates nodes and edges to build a Kalkulation
    4. Self-verifies completeness
    5. Returns structured result with provenance

    No domain knowledge is hardcoded. The graph guides the agent.
    """

    def __init__(self, db, llm, max_steps: int = 15):
        self.executor = ToolExecutor(db)
        self.llm = llm
        self.max_steps = max_steps
        self.scratchpad = Scratchpad()

    async def run(self, user_input: str, extracted_params: dict, on_step=None) -> dict:
        """Main ReAct loop. on_step callback is called after each step for live streaming."""

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Customer request: {user_input}\n\n"
                    f"Extracted parameters: {json.dumps(extracted_params, ensure_ascii=False)}\n\n"
                    "Start by calling get_schema() to understand the graph, "
                    "then navigate to produce a complete Kalkulation."
                ),
            },
        ]

        tool_schemas = self._build_tool_schemas()
        trace = []  # Full reasoning trace for transparency

        for step in range(self.max_steps):
            # THINK + ACT — LLM decides what to do next
            t0 = time.monotonic()
            response = await self.llm.chat(
                messages=messages,
                tools=tool_schemas,
                tool_choice="auto",
            )
            llm_ms = int((time.monotonic() - t0) * 1000)

            # Record the assistant's response
            messages.append(response.to_message())

            # If no tool calls → agent is done (FINISH)
            if not response.tool_calls:
                step_data = {
                    "step": step + 1,
                    "action": "FINISH",
                    "reasoning": response.text,
                    "duration_ms": llm_ms,
                }
                trace.append(step_data)
                if on_step:
                    await on_step(step_data)
                break

            # Process tool calls IN PARALLEL
            import asyncio as _aio

            parsed_calls = []
            for tool_call in response.tool_calls:
                params = tool_call.arguments if isinstance(tool_call.arguments, dict) else json.loads(tool_call.arguments)
                parsed_calls.append((tool_call, params))

            # Execute all tool calls concurrently
            t1 = time.monotonic()

            async def _exec(tc, params):
                return await self.executor.execute(tc.name, params)

            results = await _aio.gather(
                *[_exec(tc, p) for tc, p in parsed_calls]
            )
            graph_ms = int((time.monotonic() - t1) * 1000)
            total_ms = llm_ms + graph_ms

            # Record trace + feed results back (must keep order for Anthropic API)
            reasoning = response.text if response.text else None
            num_calls = len(parsed_calls)
            for idx, ((tool_call, params), result) in enumerate(zip(parsed_calls, results)):
                step_data = {
                    "step": step + 1,
                    "action": tool_call.name,
                    "params": params,
                    "result_summary": self._summarize_result(result),
                    "reasoning": reasoning,
                    "duration_ms": total_ms if idx == 0 else 0,  # attribute time to first call in batch
                    "batch_size": num_calls,
                }
                trace.append(step_data)
                if on_step:
                    await on_step(step_data)

                if tool_call.name == "follow_edges" and params.get("rel_type"):
                    self.scratchpad.explored_rels.add(params["rel_type"])
                if tool_call.name == "find_internal_edges" and params.get("rel_type"):
                    self.scratchpad.explored_rels.add(params["rel_type"])

                # Truncate large results to keep context lean → faster LLM calls
                result_str = json.dumps(result, ensure_ascii=False, default=str)
                if len(result_str) > 3000:
                    result_str = result_str[:3000] + '... (truncated)'
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_str,
                })

        # If agent hit max steps without finishing, inject final prompt
        if step == self.max_steps - 1:
            messages.append({
                "role": "user",
                "content": (
                    "You've reached the maximum number of steps. "
                    "Please produce the best Kalkulation you can with the data you've gathered. "
                    "Output ONLY a JSON object (no markdown, no explanation before or after) with these keys: "
                    "positionen, zuschlaege, rabatte, gesamtbetrag, rueckfragen, empfehlungen, facts."
                ),
            })
            response = await self.llm.chat(messages=messages, max_tokens=8192)
            step_data = {"step": step + 2, "action": "FORCED_FINISH", "reasoning": response.text}
            trace.append(step_data)
            if on_step:
                await on_step(step_data)

        return {
            "kalkulation": self._parse_kalkulation(response.text),
            "trace": trace,
            "steps": len(trace),
            "scratchpad": {
                "facts": [{"claim": f.claim, "source": f.source} for f in self.scratchpad.facts],
                "gaps": self.scratchpad.gaps,
                "explored_rels": list(self.scratchpad.explored_rels),
            },
        }

    def _build_tool_schemas(self) -> list:
        """Build OpenAI-style function schemas from AGENT_TOOLS."""
        from .tools import AGENT_TOOLS

        schemas = []
        for tool in AGENT_TOOLS:
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                },
            })
        return schemas

    def _summarize_result(self, result: dict) -> str:
        """Short, user-friendly summary for trace display. No technical IDs."""
        if "error" in result:
            return f"Fehler: {result['error'][:60]}"

        # find_nodes → show human-readable names only
        if "nodes" in result and "count" in result:
            count = result["count"]
            nodes = result["nodes"]
            names = []
            for n in nodes[:4]:
                props = n.get("props", n) if isinstance(n, dict) else {}
                name = props.get("name", "")
                if name:
                    names.append(name)
            if names:
                txt = ", ".join(names[:3])
                if count > 3:
                    txt += f" (+{count - 3})"
                return txt
            return f"{count} gefunden"

        # follow_edges → show target names, NO relationship types
        if "edges" in result and "count" in result:
            count = result["count"]
            edges = result["edges"]
            names = set()
            for e in edges[:8]:
                if isinstance(e, dict):
                    tprops = e.get("target_props") or e.get("source_props") or {}
                    name = tprops.get("name", "")
                    if name:
                        names.add(name)
            if names:
                shown = sorted(names)[:3]
                txt = ", ".join(shown)
                if len(names) > 3:
                    txt += f" (+{len(names) - 3})"
                return txt
            return f"{count} gefunden"

        # find_internal_edges
        if "internal_edges" in result:
            count = len(result["internal_edges"])
            return f"{count} Verbindungen gefunden" if count else "keine gefunden"

        # evaluate
        if "result" in result:
            return f"= {result['result']}"

        # check_completeness
        if "is_complete" in result:
            missed = result.get("missed", [])
            if missed:
                return f"{len(missed)} Beziehungen noch offen"
            return "Alles geprüft"

        # get_schema
        if "node_types" in result:
            return "Graph-Struktur geladen"

        return "ok"

    def _parse_kalkulation(self, text: str) -> dict:
        """Extract JSON Kalkulation from agent's final response."""
        # Try to find JSON block in the response
        try:
            # Look for ```json ... ``` block
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0]
            elif "{" in text:
                # Find the outermost JSON object
                start = text.index("{")
                depth = 0
                end = start
                for i, c in enumerate(text[start:], start):
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            end = i
                            break
                json_str = text[start : end + 1]
            else:
                return {"raw_response": text}

            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            return {"raw_response": text}
