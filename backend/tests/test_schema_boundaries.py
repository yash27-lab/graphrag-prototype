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

    def test_ingest_oversized(self):
        with self.assertRaises(ValidationError):
            IngestRequest(text="x" * (MAX_INGEST_CHARS + 1))

    def test_ingest_maximum(self):
        request = IngestRequest(text="x" * MAX_INGEST_CHARS)
        self.assertEqual(len(request.text), MAX_INGEST_CHARS)
