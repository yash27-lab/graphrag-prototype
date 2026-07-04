"""Persistent knowledge graph backed by NetworkX.

The whole graph lives in memory, which is a deliberate tradeoff for this
prototype: traversals are trivial to express and instant at the scale of
pasted documents. Every mutation is flushed to a JSON file (written
atomically) so the graph survives restarts.
"""

import json
import os
import threading
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import networkx as nx


class GraphStore:
    def __init__(self, path: str) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._graph = self._load()

    def upsert(
        self,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
    ) -> None:
        """Merge extracted entities and relationships into the graph.

        Re-ingesting an entity updates its attributes rather than duplicating
        it; empty attribute values never overwrite existing ones.
        """
        with self._lock:
            for ent in entities:
                attrs = {k: v for k, v in ent.items() if v not in (None, "")}
                self._graph.add_node(ent["id"], **attrs)
            for rel in relationships:
                self._graph.add_edge(
                    rel["source"],
                    rel["target"],
                    relationship=rel.get("relationship", ""),
                    description=rel.get("description", ""),
                )
            self._save_locked()

    def expand(self, seeds: Iterable[str], depth: int) -> Set[str]:
        """Breadth-first expansion from seed nodes, up to ``depth`` hops."""
        with self._lock:
            visited = {s for s in seeds if self._graph.has_node(s)}
            frontier = set(visited)
            for _ in range(depth):
                next_frontier = set()
                for node in frontier:
                    for neighbor in self._graph.neighbors(node):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            next_frontier.add(neighbor)
                if not next_frontier:
                    break
                frontier = next_frontier
            return visited

    def node_records(self, nodes: Optional[Iterable[str]] = None) -> List[Dict[str, str]]:
        """Entity records (id, type, description) for the given nodes, or all."""
        with self._lock:
            selected = self._graph.nodes if nodes is None else nodes
            records = []
            for node_id in selected:
                if not self._graph.has_node(node_id):
                    continue
                data = self._graph.nodes[node_id]
                records.append(
                    {
                        "id": node_id,
                        "type": data.get("type", "Unknown"),
                        "description": data.get("description", ""),
                    }
                )
            return records

    def edge_records(self, nodes: Optional[Iterable[str]] = None) -> List[Dict[str, str]]:
        """Relationship records between the given nodes (or all edges)."""
        with self._lock:
            allowed = None if nodes is None else set(nodes)
            records = []
            for source, target, data in self._graph.edges(data=True):
                if allowed is not None and (source not in allowed or target not in allowed):
                    continue
                records.append(
                    {
                        "source": source,
                        "target": target,
                        "relationship": data.get("relationship", ""),
                        "description": data.get("description", ""),
                    }
                )
            return records

    def stats(self) -> Tuple[int, int]:
        with self._lock:
            return self._graph.number_of_nodes(), self._graph.number_of_edges()

    def clear(self) -> None:
        with self._lock:
            self._graph = nx.Graph()
            if os.path.exists(self._path):
                os.remove(self._path)

    def _load(self) -> nx.Graph:
        if os.path.exists(self._path):
            try:
                with open(self._path, "r") as f:
                    return nx.node_link_graph(json.load(f), edges="links")
            except Exception as exc:
                # A corrupted file should not prevent startup; start fresh.
                print(f"Failed to load graph from {self._path}: {exc}")
        return nx.Graph()

    def _save_locked(self) -> None:
        data = nx.node_link_data(self._graph, edges="links")
        tmp_path = f"{self._path}.tmp"
        with open(tmp_path, "w") as f:
            json.dump(data, f)
        os.replace(tmp_path, self._path)
