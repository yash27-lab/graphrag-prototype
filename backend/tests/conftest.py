"""Shared fixtures: a fake LLM and a deterministic embedding function.

The suite is fully hermetic: no API key, no network, no model downloads.
"""

import hashlib
import math
import re
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

from graphrag.api import create_app
from graphrag.config import Settings

EMBEDDING_DIM = 16


class FakeLLM:
    """Stands in for GeminiService; returns canned extractions and records
    the context passed to synthesis so tests can assert on it."""

    def __init__(self, extraction: Optional[Dict[str, Any]] = None) -> None:
        self.extraction = extraction or {"entities": [], "relationships": []}
        self.synthesis_calls: List[Dict[str, str]] = []

    def extract_graph(
        self, text: str, model: str, api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        return self.extraction

    def synthesize_answer(
        self, query: str, context: str, model: str, api_key: Optional[str] = None
    ) -> str:
        self.synthesis_calls.append({"query": query, "context": context, "model": model})
        return f"answer to: {query}"


class HashEmbeddingFunction:
    """Deterministic bag-of-words embedding: no model download, and queries
    sharing words with a document land close to it in vector space."""

    def __call__(self, input: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in input]

    @staticmethod
    def _embed(text: str) -> List[float]:
        vector = [0.0] * EMBEDDING_DIM
        for token in re.findall(r"\w+", text.lower()):
            digest = hashlib.md5(token.encode()).hexdigest()
            vector[int(digest, 16) % EMBEDDING_DIM] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


# A four-entity supply chain: Mine -> ElectroChem -> Apex Motors -> Nova EV.
# Each description uses distinct keywords so vector search is predictable.
CHAIN_EXTRACTION: Dict[str, Any] = {
    "entities": [
        {"id": "Lithium Mine", "type": "Organization", "description": "strike halts output"},
        {"id": "ElectroChem", "type": "Organization", "description": "battery manufacturer"},
        {"id": "Apex Motors", "type": "Organization", "description": "automaker"},
        {"id": "Nova EV", "type": "Product", "description": "flagship electric car"},
    ],
    "relationships": [
        {"source": "Lithium Mine", "target": "ElectroChem", "relationship": "supplies"},
        {"source": "ElectroChem", "target": "Apex Motors", "relationship": "supplies"},
        {"source": "Apex Motors", "target": "Nova EV", "relationship": "manufactures"},
    ],
}


@pytest.fixture
def make_client(tmp_path):
    """Factory building a TestClient wired with fakes.

    Reusing the same ``persist_dir`` across calls simulates a server restart
    against the same on-disk state.
    """

    def _make(extraction=None, persist_dir=None):
        settings = Settings()
        settings.persist_dir = str(persist_dir or tmp_path / "data")
        fake_llm = FakeLLM(extraction)
        app = create_app(
            settings=settings,
            llm=fake_llm,
            embedding_function=HashEmbeddingFunction(),
        )
        return TestClient(app), fake_llm

    return _make
