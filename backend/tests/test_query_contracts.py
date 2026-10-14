"""Pipeline orchestration contracts without network or embedding downloads."""

import unittest
from unittest.mock import Mock

from graphrag.pipeline import GraphRAGPipeline, estimate_tokens


class QueryContractTests(unittest.TestCase):
    def test_metrics_counts(self):
        metrics = self.query()["metrics"]
        self.assertEqual(metrics["nodes_retrieved"], 2)
        self.assertEqual(metrics["edges_retrieved"], 1)
        self.assertEqual(metrics["depth_used"], 1)

    def test_answer_passthrough(self):
        self.assertEqual(self.query()["answer"], "answer")

    def test_synthesis_credentials(self):
        self.query(api_key="synthetic-test-key")
        args, kwargs = self.llm.synthesize_answer.call_args
        self.assertEqual((args[0], args[2]), ("question", "model"))
        self.assertEqual(kwargs, {"api_key": "synthetic-test-key"})

    def test_edge_filter(self):
        self.query()
        self.graph.edge_records.assert_called_once_with({"A", "B"})

    def test_node_filter(self):
        self.query()
        self.graph.node_records.assert_called_once_with({"A", "B"})

    def test_traversal_arguments(self):
        self.query()
        self.graph.expand.assert_called_once_with(["A"], 1)

    def test_retrieval_arguments(self):
        self.query()
        self.vectors.find_entry_points.assert_called_once_with("question", 3)

    def test_stale_index(self):
        self.graph.expand.return_value = set()
        result = self.query()
        self.assertEqual(result["graph"], {"nodes": [], "links": []})
        self.llm.synthesize_answer.assert_not_called()

    def test_no_seeds(self):
        self.vectors.find_entry_points.return_value = []
        result = self.query()
        self.assertIsNone(result["metrics"])
        self.graph.expand.assert_not_called()
        self.llm.synthesize_answer.assert_not_called()

    def test_sorted_seeds(self):
        self.vectors.find_entry_points.return_value = ["B", "A"]
        self.assertEqual(self.query()["metrics"]["seed_entities"], ["A", "B"])

    def test_duplicate_seeds(self):
        self.vectors.find_entry_points.return_value = ["A", "A"]
        self.assertEqual(self.query()["metrics"]["seed_entities"], ["A"])

    def test_stale_seed_metrics(self):
        self.vectors.find_entry_points.return_value = ["A", "missing"]
        self.assertEqual(self.query()["metrics"]["seed_entities"], ["A"])

    def setUp(self):
        self.graph = Mock()
        self.graph.expand.return_value = {"A", "B"}
        self.graph.node_records.return_value = [
            {"id": n, "type": "T", "description": n} for n in ("A", "B")
        ]
        self.graph.edge_records.return_value = [
            {"source": "A", "target": "B", "relationship": "r", "description": ""}
        ]
        self.vectors = Mock()
        self.vectors.find_entry_points.return_value = ["A"]
        self.llm = Mock()
        self.llm.synthesize_answer.return_value = "answer"
        self.pipeline = GraphRAGPipeline(self.graph, self.vectors, self.llm)

    def query(self, **kwargs):
        return self.pipeline.query("question", depth=1, top_k=3, model="model", **kwargs)
