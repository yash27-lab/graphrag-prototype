"""Offline ingestion orchestration regressions with explicit store fakes."""

import unittest
from unittest.mock import Mock

from graphrag.pipeline import GraphRAGPipeline


class IngestContractTests(unittest.TestCase):
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
