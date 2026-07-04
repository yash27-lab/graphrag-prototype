"""API-level tests covering ingestion, validation, health, and reset."""

import pytest

from graphrag.llm import LLMError
from graphrag.schemas import IngestRequest, QueryRequest

from .conftest import CHAIN_EXTRACTION, FakeLLM


def test_health_starts_empty(make_client):
    client, _ = make_client()
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "entities": 0, "relationships": 0}


def test_ingest_builds_graph(make_client):
    client, _ = make_client(extraction=CHAIN_EXTRACTION)
    res = client.post("/ingest", json={"text": "some article"})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert body["entities_count"] == 4
    assert body["relationships_count"] == 3
    assert len(body["graph"]["nodes"]) == 4
    assert len(body["graph"]["links"]) == 3

    health = client.get("/health").json()
    assert health == {"status": "ok", "entities": 4, "relationships": 3}


def test_reingesting_same_entities_is_idempotent(make_client):
    client, fake_llm = make_client(extraction=CHAIN_EXTRACTION)
    client.post("/ingest", json={"text": "first pass"})

    # Second extraction mentions an existing entity with a richer description.
    fake_llm.extraction = {
        "entities": [
            {"id": "Nova EV", "type": "Product", "description": "solid-state powered sedan"}
        ],
        "relationships": [],
    }
    client.post("/ingest", json={"text": "second pass"})

    health = client.get("/health").json()
    assert health["entities"] == 4  # updated in place, not duplicated

    graph = client.get("/graph").json()
    ids = [node["id"] for node in graph["nodes"]]
    assert sorted(ids) == sorted(
        ["Lithium Mine", "ElectroChem", "Apex Motors", "Nova EV"]
    )


def test_ingest_discards_malformed_extraction_items(make_client):
    client, _ = make_client(
        extraction={
            "entities": [
                {"id": "  Valid Entity  ", "type": "Concept", "description": "kept"},
                {"id": "", "type": "Concept", "description": "dropped"},
                "not a dict",
            ],
            "relationships": [
                {"source": "Valid Entity", "target": "", "relationship": "dropped"},
            ],
        }
    )
    res = client.post("/ingest", json={"text": "messy"})
    assert res.status_code == 200
    body = res.json()
    assert body["entities_count"] == 1
    assert body["graph"]["nodes"][0]["id"] == "Valid Entity"  # whitespace stripped
    assert body["relationships_count"] == 0


def test_request_validation():
    with pytest.raises(ValueError):
        QueryRequest(query="q", depth=7)
    with pytest.raises(ValueError):
        QueryRequest(query="q", depth=-1)
    with pytest.raises(ValueError):
        IngestRequest(text="")


def test_query_depth_out_of_range_is_rejected(make_client):
    client, _ = make_client()
    res = client.post("/query", json={"query": "anything", "depth": 10})
    assert res.status_code == 422


def test_query_on_empty_store(make_client):
    client, fake_llm = make_client()
    res = client.post("/query", json={"query": "who supplies whom?"})
    assert res.status_code == 200
    body = res.json()
    assert "empty" in body["answer"].lower()
    assert body["graph"] == {"nodes": [], "links": []}
    assert body["metrics"] is None
    assert fake_llm.synthesis_calls == []  # no LLM call without context


def test_reset_clears_graph_and_vectors(make_client):
    client, _ = make_client(extraction=CHAIN_EXTRACTION)
    client.post("/ingest", json={"text": "some article"})

    res = client.delete("/graph")
    assert res.status_code == 200

    assert client.get("/health").json()["entities"] == 0
    body = client.post("/query", json={"query": "strike halts output"}).json()
    assert body["metrics"] is None


def test_state_survives_restart(make_client, tmp_path):
    persist_dir = tmp_path / "persist"
    client, _ = make_client(extraction=CHAIN_EXTRACTION, persist_dir=persist_dir)
    client.post("/ingest", json={"text": "some article"})

    # New app instance over the same directory simulates a restart.
    reloaded_client, _ = make_client(persist_dir=persist_dir)
    graph = reloaded_client.get("/graph").json()
    assert len(graph["nodes"]) == 4
    assert len(graph["links"]) == 3

    # Vector index also persisted: querying still finds entry points.
    body = reloaded_client.post(
        "/query", json={"query": "strike halts output", "depth": 0, "top_k": 1}
    ).json()
    assert body["metrics"]["seed_entities"] == ["Lithium Mine"]


def test_llm_errors_map_to_http_status(make_client):
    class RateLimitedLLM(FakeLLM):
        def extract_graph(self, text, model, api_key=None):
            raise LLMError(429, "rate limit reached")

    client, _ = make_client()
    client.app.state.pipeline.llm = RateLimitedLLM()
    res = client.post("/ingest", json={"text": "anything"})
    assert res.status_code == 429
    assert "rate limit" in res.json()["detail"]
