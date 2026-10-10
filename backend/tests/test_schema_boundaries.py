"""Offline request-contract regressions; no LLM or vector store required."""

import unittest

from pydantic import ValidationError

from graphrag.schemas import (
    MAX_INGEST_CHARS,
    MAX_TRAVERSAL_DEPTH,
    IngestRequest,
    QueryRequest,
)


class SchemaBoundaryTests(unittest.TestCase):
    """Protect API size and retrieval-budget boundaries."""

    def test_query_empty(self):
        with self.assertRaises(ValidationError):
            QueryRequest(query="")

    def test_query_oversized(self):
        with self.assertRaises(ValidationError):
            QueryRequest(query="x" * 2001)

    def test_query_maximum(self):
        self.assertEqual(len(QueryRequest(query="x" * 2000).query), 2000)

    def test_ingest_null(self):
        with self.assertRaises(ValidationError):
            IngestRequest(text=None)

    def test_ingest_missing(self):
        with self.assertRaises(ValidationError):
            IngestRequest()

    def test_ingest_oversized(self):
        with self.assertRaises(ValidationError):
            IngestRequest(text="x" * (MAX_INGEST_CHARS + 1))

    def test_ingest_maximum(self):
        request = IngestRequest(text="x" * MAX_INGEST_CHARS)
        self.assertEqual(len(request.text), MAX_INGEST_CHARS)
