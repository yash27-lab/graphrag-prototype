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

    def test_context_node_order(self):
        nodes = [{"id": n, "type": "T", "description": n} for n in ("B", "A")]
        self.assertEqual(_format_context(nodes, []), _format_context(list(reversed(nodes)), []))
        self.assertEqual(nodes[0]["id"], "B")

    def test_empty_payload(self):
        self.assertEqual(_payload([], []), {"nodes": [], "links": []})

    def test_token_whitespace(self):
        self.assertEqual(estimate_tokens("one two three"), estimate_tokens("one\n two\tthree"))
        self.assertEqual(estimate_tokens("one two three"), 3)

    def test_empty_tokens(self):
        self.assertEqual(estimate_tokens(""), 0)
        self.assertEqual(estimate_tokens(" \n\t "), 0)

    def test_relations_immutable(self):
        raw = [{"source": " A ", "target": " B "}]
        _clean_relationships(raw)
        self.assertEqual(raw[0]["source"], " A ")
        self.assertEqual(raw[0]["target"], " B ")

    def test_relations_trim(self):
        self.assertEqual(_clean_relationships([{"source": " A ", "target": " B "}]),
                         [{"source": "A", "target": "B"}])

    def test_relations_endpoints(self):
        self.assertEqual(_clean_relationships([{"source": "A"}, {"target": "B"},
                                             {"source": " ", "target": "B"}]), [])

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
