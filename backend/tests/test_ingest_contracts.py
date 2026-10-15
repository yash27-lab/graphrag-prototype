"""Offline ingestion orchestration regressions with explicit store fakes."""

import unittest
from unittest.mock import Mock

from graphrag.pipeline import GraphRAGPipeline


class IngestContractTests(unittest.TestCase):
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
