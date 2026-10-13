"""Offline contracts for extraction cleanup and synthesis context."""

import unittest

from graphrag.pipeline import (
    _clean_entities,
    _clean_relationships,
    _format_context,
    _payload,
    estimate_tokens,
)


class PipelineContractTests(unittest.TestCase):
    """Exercise pure helpers without importing Gemini or Chroma."""

    def test_relations_non_dict(self):
        self.assertEqual(_clean_relationships([None, "bad", [], 42]), [])

    def test_relations_non_list(self):
        for raw in (None, {}, "text", 42):
            self.assertEqual(_clean_relationships(raw), [])

    def test_entities_immutable(self):
        raw = [{"id": " A "}]
        _clean_entities(raw)
        self.assertEqual(raw, [{"id": " A "}])

    def test_entities_trim(self):
        self.assertEqual(_clean_entities([{"id": " A ", "type": "T"}]), [{"id": "A", "type": "T"}])

    def test_entities_blank(self):
        self.assertEqual(_clean_entities([{}, {"id": None}, {"id": "  "}]), [])

    def test_entities_non_dict(self):
        self.assertEqual(_clean_entities([None, "bad", 1, [], {"id": "ok"}]), [{"id": "ok"}])

    def test_entities_non_list(self):
        for raw in (None, {}, "text", 42):
            self.assertEqual(_clean_entities(raw), [])
