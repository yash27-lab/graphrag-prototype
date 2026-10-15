"""Offline ingestion orchestration regressions with explicit store fakes."""

import unittest
from unittest.mock import Mock

from graphrag.pipeline import GraphRAGPipeline


class IngestContractTests(unittest.TestCase):
    def test_mutation_order(self):
        events = Mock()
        events.attach_mock(self.graph.upsert, "graph")
        events.attach_mock(self.vectors.upsert_entities, "vectors")
        self.ingest()
        self.assertEqual([c[0] for c in events.mock_calls], ["graph", "vectors"])

    def test_vector_failure(self):
        self.vectors.upsert_entities.side_effect = RuntimeError("index failed")
        with self.assertRaisesRegex(RuntimeError, "index failed"):
            self.ingest()
        self.graph.node_records.assert_not_called()

    def test_graph_failure(self):
        self.graph.upsert.side_effect = RuntimeError("graph failed")
        with self.assertRaisesRegex(RuntimeError, "graph failed"):
            self.ingest()
        self.vectors.upsert_entities.assert_not_called()

    def test_extract_failure(self):
        self.llm.extract_graph.side_effect = RuntimeError("extract failed")
        with self.assertRaisesRegex(RuntimeError, "extract failed"):
            self.ingest()
        self.graph.upsert.assert_not_called()
        self.vectors.upsert_entities.assert_not_called()

    def test_no_synthesis(self):
        self.ingest()
        self.llm.synthesize_answer.assert_not_called()

    def test_graph_payload(self):
        self.assertEqual(self.ingest()["graph"], {
            "nodes": [{"id": "A", "label": "A", "group": "Concept"}], "links": []
        })

    def test_status(self):
        self.assertEqual(self.ingest()["status"], "success")

    def test_non_list_relationships(self):
        self.llm.extract_graph.return_value["relationships"] = "invalid"
        self.assertEqual(self.ingest()["relationships_count"], 0)

    def test_non_list_entities(self):
        self.llm.extract_graph.return_value["entities"] = {"id": "A"}
        self.assertEqual(self.ingest()["entities_count"], 0)
        self.vectors.upsert_entities.assert_called_once_with([])

    def test_empty_extraction(self):
        self.llm.extract_graph.return_value = {}
        result = self.ingest()
        self.assertEqual((result["entities_count"], result["relationships_count"]), (0, 0))

    def test_relationship_count(self):
        self.llm.extract_graph.return_value["relationships"] = [
            {"source": "A", "target": "B"}, {"source": "A"}, None
        ]
        self.assertEqual(self.ingest()["relationships_count"], 1)

    def test_entity_count(self):
        self.llm.extract_graph.return_value["entities"] += [None, {}, {"id": " "}]
        self.assertEqual(self.ingest()["entities_count"], 1)

    def test_relationship_normalization(self):
        self.llm.extract_graph.return_value["relationships"] = [{"source": " A ", "target": " B "}]
        self.ingest()
        self.assertEqual(self.graph.upsert.call_args.args[1], [{"source": "A", "target": "B"}])

    def test_normalized_vector_entities(self):
        self.ingest()
        self.assertEqual(self.vectors.upsert_entities.call_args.args[0],
                         self.graph.upsert.call_args.args[0])

    def test_normalized_graph_entities(self):
        self.ingest()
        entities, _ = self.graph.upsert.call_args.args
        self.assertEqual(entities[0]["id"], "A")

    def test_extraction_key(self):
        self.ingest(api_key="synthetic-test-key")
        self.llm.extract_graph.assert_called_once_with(
            "source text", "model", api_key="synthetic-test-key"
        )

    def test_extraction_arguments(self):
        self.ingest()
        self.llm.extract_graph.assert_called_once_with("source text", "model", api_key=None)

    def setUp(self):
        self.graph = Mock()
        self.graph.node_records.return_value = [
            {"id": "A", "type": "Concept", "description": "source"}
        ]
        self.graph.edge_records.return_value = []
        self.vectors = Mock()
        self.llm = Mock()
        self.llm.extract_graph.return_value = {
            "entities": [{"id": " A ", "type": "Concept", "description": "source"}],
            "relationships": [],
        }
        self.pipeline = GraphRAGPipeline(self.graph, self.vectors, self.llm)

    def ingest(self, **kwargs):
        return self.pipeline.ingest("source text", "model", **kwargs)
