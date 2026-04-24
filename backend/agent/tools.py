"""
SmartCal Graph Agent — Generic Graph Navigation Tools

These tools know NOTHING about TÜV SÜD, pricing, or inspections.
They are pure graph primitives. The agent discovers the domain
by exploring the graph structure.

Tool count: 5 navigation + 1 math + 1 completeness check = 7 total
"""

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Tool definitions (passed to LLM as function schemas)
# ---------------------------------------------------------------------------

AGENT_TOOLS = [
    {
        "name": "find_nodes",
        "description": (
            "Find nodes by label and optional property filters. "
            "Use this to discover what exists in the graph. "
            "Example: find_nodes('Dienstleistung') returns all services. "
            "Example: find_nodes('Merkmal', {kategorie: 'bma'}) returns BMA-specific characteristics."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "label": {
                    "type": "string",
                    "description": "Node label (e.g. 'Dienstleistung', 'Merkmal', 'Gebaeudetyp')"
                },
                "filters": {
                    "type": "object",
                    "description": "Optional property filters as key-value pairs",
                    "additionalProperties": True
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 50)",
                    "default": 50
                }
            },
            "required": ["label"]
        },
        "cypher": """
            MATCH (n:{label})
            {where_clause}
            RETURN n
            LIMIT $limit
        """
    },
    {
        "name": "follow_edges",
        "description": (
            "From a specific node, follow outgoing or incoming edges. "
            "Optionally filter by relationship type. Returns the edge properties "
            "AND the connected node. This is your primary traversal tool. "
            "Example: follow_edges('DL_WALLBOX', 'HAT_PREISPOSITION') → price components. "
            "Example: follow_edges('MERK_BGF', 'SCHAETZT') → what BGF estimates. "
            "Example: follow_edges('DL_BMA', direction='in') → what points TO this service."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "node_id": {
                    "type": "string",
                    "description": "The id of the starting node"
                },
                "rel_type": {
                    "type": "string",
                    "description": "Optional: filter by relationship type (e.g. 'SCHAETZT', 'HAT_PREISPOSITION')"
                },
                "direction": {
                    "type": "string",
                    "enum": ["out", "in", "both"],
                    "description": "Edge direction (default: out)",
                    "default": "out"
                }
            },
            "required": ["node_id"]
        },
        "cypher_out": """
            MATCH (n {id: $node_id})-[r{rel_filter}]->(target)
            RETURN type(r) AS rel_type, properties(r) AS rel_props,
                   labels(target)[0] AS target_label, target.id AS target_id,
                   properties(target) AS target_props
        """,
        "cypher_in": """
            MATCH (n {id: $node_id})<-[r{rel_filter}]-(source)
            RETURN type(r) AS rel_type, properties(r) AS rel_props,
                   labels(source)[0] AS source_label, source.id AS source_id,
                   properties(source) AS source_props
        """
    },
    {
        "name": "find_paths",
        "description": (
            "Find multi-hop paths between nodes or from a node to a target label. "
            "Use this to discover estimation chains (SCHAETZT→SCHAETZT), "
            "causal chains (LOEST_AUS→BEWIRKT_ZUSCHLAG→Zuschlag), "
            "or any multi-hop pattern. "
            "Example: find_paths('MERK_BGF', target_label='Preisposition', max_hops=3) "
            "→ discovers BGF→SCHAETZT→Merkmal→(via DL)→Preisposition"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "from_id": {
                    "type": "string",
                    "description": "Starting node id"
                },
                "target_label": {
                    "type": "string",
                    "description": "Optional: label of target nodes to reach"
                },
                "target_id": {
                    "type": "string",
                    "description": "Optional: specific target node id"
                },
                "rel_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: only traverse these relationship types"
                },
                "max_hops": {
                    "type": "integer",
                    "description": "Maximum path length (default: 3)",
                    "default": 3
                }
            },
            "required": ["from_id"]
        },
        "cypher": """
            MATCH path = (start {id: $from_id})-[*1..{max_hops}]->(end{target_filter})
            {rel_type_filter}
            RETURN [n IN nodes(path) | {id: n.id, label: labels(n)[0], props: properties(n)}] AS nodes,
                   [r IN relationships(path) | {type: type(r), props: properties(r)}] AS edges,
                   length(path) AS hops
            LIMIT 20
        """
    },
    {
        "name": "find_internal_edges",
        "description": (
            "Given a SET of node IDs, find all edges between them. "
            "This is the BUNDLE DISCOVERY tool — pass in all selected services "
            "and it finds GLEICHE_BEGEHUNG, EMPFIEHLT, SCHLIESST_EIN relationships. "
            "Example: find_internal_edges(['DL_WALLBOX', 'DL_BMA', 'DL_DGUV_ORTF']) "
            "→ discovers which services can share site visits."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "node_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of node IDs to check connections between"
                },
                "rel_type": {
                    "type": "string",
                    "description": "Optional: filter by relationship type"
                }
            },
            "required": ["node_ids"]
        },
        "cypher": """
            MATCH (a)-[r{rel_filter}]->(b)
            WHERE a.id IN $node_ids AND b.id IN $node_ids
            RETURN a.id AS from_id, type(r) AS rel_type,
                   properties(r) AS rel_props, b.id AS to_id
        """
    },
    {
        "name": "get_schema",
        "description": (
            "Inspect the graph schema — what node labels, relationship types, "
            "and property keys exist. Use this FIRST to understand the graph structure "
            "before navigating. Like 'ls' for the graph."
        ),
        "parameters": {
            "type": "object",
            "properties": {}
        },
        "cypher_nodes": """
            MATCH (n)
            WITH labels(n)[0] AS label, count(n) AS count, keys(n) AS props
            RETURN label, count, collect(DISTINCT props)[0] AS sample_properties
            ORDER BY count DESC
        """,
        "cypher_rels": """
            MATCH ()-[r]->()
            WITH type(r) AS rel_type, count(r) AS count,
                 startNode(r) AS s, endNode(r) AS e
            RETURN rel_type, count,
                   collect(DISTINCT labels(s)[0])[0] AS from_label,
                   collect(DISTINCT labels(e)[0])[0] AS to_label
            ORDER BY count DESC
        """
    },
    {
        "name": "evaluate",
        "description": (
            "Evaluate a mathematical expression with variables. "
            "Use this to compute prices, apply formulas from SCHAETZT edges, "
            "or calculate totals. "
            "Example: evaluate('bgf_m2 / 30 * sicherheitsfaktor', {bgf_m2: 5000, sicherheitsfaktor: 1.2}) → 200"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression (Python syntax)"
                },
                "variables": {
                    "type": "object",
                    "description": "Variable values",
                    "additionalProperties": True
                }
            },
            "required": ["expression", "variables"]
        }
    },
    {
        "name": "check_completeness",
        "description": (
            "After building a Kalkulation, verify you haven't missed anything. "
            "Pass in the service IDs you've priced — this tool checks which "
            "relationship types exist for those services and reports any unexplored edges. "
            "Think of it as 'did I follow all paths?'"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "service_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "IDs of Dienstleistungen in the Kalkulation"
                },
                "explored_rel_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Relationship types you've already explored"
                }
            },
            "required": ["service_ids", "explored_rel_types"]
        },
        "cypher": """
            MATCH (dl:Dienstleistung)-[r]->(target)
            WHERE dl.id IN $service_ids
            WITH type(r) AS rel_type, count(*) AS edge_count,
                 collect(DISTINCT labels(target)[0]) AS target_labels
            RETURN rel_type, edge_count, target_labels,
                   CASE WHEN rel_type IN $explored THEN 'EXPLORED' ELSE 'MISSED' END AS status
            ORDER BY status DESC, edge_count DESC
        """
    }
]
