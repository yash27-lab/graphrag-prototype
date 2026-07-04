"""GraphRAG orchestration: the ingestion and retrieval pipelines.

Ingestion: LLM extraction -> graph upsert -> embedding upsert.
Retrieval: vector search for entry points -> bounded graph traversal ->
context assembly -> LLM synthesis over the pruned context only.
"""

from typing import Any, Dict, List, Optional

from .graph_store import GraphStore
from .llm import GeminiService
from .vector_store import VectorStore


def estimate_tokens(text: str) -> int:
    """Rough token estimate (about 1.3 tokens per whitespace-delimited word)."""
    return int(len(text.split()) * 1.3)


class GraphRAGPipeline:
    def __init__(self, graph: GraphStore, vectors: VectorStore, llm: GeminiService) -> None:
        self.graph = graph
        self.vectors = vectors
        self.llm = llm

    def ingest(self, text: str, model: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        extraction = self.llm.extract_graph(text, model, api_key=api_key)
        entities = _clean_entities(extraction.get("entities", []))
        relationships = _clean_relationships(extraction.get("relationships", []))

        self.graph.upsert(entities, relationships)
        self.vectors.upsert_entities(entities)

        return {
            "status": "success",
            "entities_count": len(entities),
            "relationships_count": len(relationships),
            "graph": self.graph_payload(),
        }

    def query(
        self,
        query: str,
        depth: int,
        top_k: int,
        model: str,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        seeds = self.vectors.find_entry_points(query, top_k)
        if not seeds:
            return {
                "answer": "The knowledge graph is empty. Ingest some text first.",
                "graph": {"nodes": [], "links": []},
                "metrics": None,
            }

        context_nodes = self.graph.expand(seeds, depth)
        if not context_nodes:
            # Vector index and graph disagree (e.g. partial reset); do not
            # call the LLM with an empty context.
            return {
                "answer": "The knowledge graph is empty. Ingest some text first.",
                "graph": {"nodes": [], "links": []},
                "metrics": None,
            }
        node_records = self.graph.node_records(context_nodes)
        edge_records = self.graph.edge_records(context_nodes)

        context_text = _format_context(node_records, edge_records)
        answer = self.llm.synthesize_answer(query, context_text, model, api_key=api_key)

        return {
            "answer": answer,
            "graph": _payload(node_records, edge_records),
            "metrics": {
                "seed_entities": sorted(set(seeds)),
                "nodes_retrieved": len(node_records),
                "edges_retrieved": len(edge_records),
                "depth_used": depth,
                "estimated_tokens": estimate_tokens(context_text),
            },
        }

    def graph_payload(self) -> Dict[str, Any]:
        return _payload(self.graph.node_records(), self.graph.edge_records())

    def reset(self) -> None:
        self.graph.clear()
        self.vectors.clear()

    def stats(self) -> Dict[str, int]:
        nodes, edges = self.graph.stats()
        return {"entities": nodes, "relationships": edges}


def _clean_entities(raw: Any) -> List[Dict[str, Any]]:
    entities = []
    for ent in raw if isinstance(raw, list) else []:
        if not isinstance(ent, dict):
            continue
        entity_id = str(ent.get("id") or "").strip()
        if not entity_id:
            continue
        entities.append({**ent, "id": entity_id})
    return entities


def _clean_relationships(raw: Any) -> List[Dict[str, Any]]:
    relationships = []
    for rel in raw if isinstance(raw, list) else []:
        if not isinstance(rel, dict):
            continue
        source = str(rel.get("source") or "").strip()
        target = str(rel.get("target") or "").strip()
        if not source or not target:
            continue
        relationships.append({**rel, "source": source, "target": target})
    return relationships


def _format_context(
    node_records: List[Dict[str, str]], edge_records: List[Dict[str, str]]
) -> str:
    lines = ["Entities:"]
    for node in node_records:
        lines.append(f"- {node['id']} ({node['type']}): {node['description']}")
    lines.append("")
    lines.append("Relationships:")
    for edge in edge_records:
        lines.append(
            f"- {edge['source']} --[{edge['relationship']}]--> "
            f"{edge['target']}: {edge['description']}"
        )
    return "\n".join(lines)


def _payload(
    node_records: List[Dict[str, str]], edge_records: List[Dict[str, str]]
) -> Dict[str, Any]:
    return {
        "nodes": [
            {"id": n["id"], "label": n["id"], "group": n["type"]} for n in node_records
        ],
        "links": [
            {"source": e["source"], "target": e["target"], "label": e["relationship"]}
            for e in edge_records
        ],
    }
