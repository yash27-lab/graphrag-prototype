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

    def test_entities_non_list(self):
        for raw in (None, {}, "text", 42):
            self.assertEqual(_clean_entities(raw), [])
