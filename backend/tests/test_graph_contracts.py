"""Offline graph-store contracts covering retrieval and persistence."""

import tempfile
import unittest
from pathlib import Path

from graphrag.graph_store import GraphStore


class GraphContractTests(unittest.TestCase):
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
