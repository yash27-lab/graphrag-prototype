"""Offline graph-store contracts covering retrieval and persistence."""

import tempfile
import unittest
from pathlib import Path

from graphrag.graph_store import GraphStore


class GraphContractTests(unittest.TestCase):
    def test_entity_update(self):
        self.chain()
        self.store.upsert([{"id": "A", "description": "updated"}], [])
        self.assertEqual(self.store.stats(), (3, 2))
        self.assertEqual(self.store.node_records(["A"])[0]["description"], "updated")

    def test_empty_edge_filter(self):
        self.chain()
        self.assertEqual(self.store.edge_records([]), [])

    def test_edge_induced_filter(self):
        self.chain()
        self.assertEqual(self.store.edge_records(["A"]), [])
        edges = self.store.edge_records(["A", "B"])
        self.assertEqual(len(edges), 1)
        self.assertEqual({edges[0]["source"], edges[0]["target"]}, {"A", "B"})

    def test_unknown_node_filter(self):
        self.chain()
        self.assertEqual(self.store.node_records(["missing", "B"])[0]["id"], "B")
        self.assertEqual(len(self.store.node_records(["missing", "B"])), 1)

    def test_empty_node_filter(self):
        self.chain()
        self.assertEqual(self.store.node_records([]), [])

    def test_disconnected(self):
        self.chain()
        self.store.upsert([{"id": "D"}], [])
        self.assertEqual(self.store.expand(["A"], 100), {"A", "B", "C"})

    def test_self_loop(self):
        self.store.upsert([{"id": "A"}], [{"source": "A", "target": "A"}])
        self.assertEqual(self.store.expand(["A"], 100), {"A"})

    def test_cycle_termination(self):
        self.chain()
        self.store.upsert([], [{"source": "C", "target": "A"}])
        self.assertEqual(self.store.expand(["A"], 100), {"A", "B", "C"})

    def test_generator_seeds(self):
        self.chain()
        self.assertEqual(self.store.expand(iter(["A"]), 2), {"A", "B", "C"})

    def test_duplicate_seeds(self):
        self.chain()
        self.assertEqual(self.store.expand(["A", "A"], 1), {"A", "B"})

    def test_empty_seeds(self):
        self.chain()
        self.assertEqual(self.store.expand([], 3), set())

    def test_empty_records(self):
        self.assertEqual(self.store.node_records(), [])
        self.assertEqual(self.store.edge_records(), [])
        self.assertEqual(self.store.stats(), (0, 0))

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "graph.json"
        self.store = GraphStore(str(self.path))

    def chain(self):
        self.store.upsert(
            [{"id": name, "type": "T", "description": name} for name in ("A", "B", "C")],
            [{"source": "A", "target": "B"}, {"source": "B", "target": "C"}],
        )
