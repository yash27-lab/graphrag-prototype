"""The core thesis of the project, as an executable test.

With a chained supply graph (Mine -> ElectroChem -> Apex Motors -> Nova EV),
plain vector retrieval (depth 0) only surfaces the entity that is
semantically similar to the query. Graph traversal (depth >= 2) pulls in the
downstream entities that the LLM needs to actually answer a multi-hop
question.
"""

from .conftest import CHAIN_EXTRACTION

# Matches only the "Lithium Mine" description in CHAIN_EXTRACTION.
SEED_QUERY = "strike halts output"


def ingest_chain(client):
    res = client.post("/ingest", json={"text": "supply chain article"})
    assert res.status_code == 200


def run_query(client, depth):
    res = client.post(
        "/query", json={"query": SEED_QUERY, "depth": depth, "top_k": 1}
    )
    assert res.status_code == 200
    return res.json()


def test_depth_zero_sees_only_the_seed_entity(make_client):
    client, fake_llm = make_client(extraction=CHAIN_EXTRACTION)
    ingest_chain(client)

    body = run_query(client, depth=0)
    assert body["metrics"]["seed_entities"] == ["Lithium Mine"]
    assert body["metrics"]["nodes_retrieved"] == 1
    assert body["metrics"]["edges_retrieved"] == 0

    context = fake_llm.synthesis_calls[-1]["context"]
    assert "Lithium Mine" in context
    assert "Apex Motors" not in context  # the downstream chain is invisible


def test_depth_two_reaches_two_hops_out(make_client):
    client, fake_llm = make_client(extraction=CHAIN_EXTRACTION)
    ingest_chain(client)

    body = run_query(client, depth=2)
    retrieved = {node["id"] for node in body["graph"]["nodes"]}
    assert retrieved == {"Lithium Mine", "ElectroChem", "Apex Motors"}
    assert body["metrics"]["nodes_retrieved"] == 3
    assert body["metrics"]["edges_retrieved"] == 2

    context = fake_llm.synthesis_calls[-1]["context"]
    assert "Apex Motors" in context
    assert "Nova EV" not in context  # three hops away, still out of reach


def test_depth_three_reaches_the_end_of_the_chain(make_client):
    client, fake_llm = make_client(extraction=CHAIN_EXTRACTION)
    ingest_chain(client)

    body = run_query(client, depth=3)
    retrieved = {node["id"] for node in body["graph"]["nodes"]}
    assert retrieved == {"Lithium Mine", "ElectroChem", "Apex Motors", "Nova EV"}

    context = fake_llm.synthesis_calls[-1]["context"]
    assert "Nova EV" in context
    assert "--[manufactures]-->" in context


def test_metrics_report_context_size(make_client):
    client, _ = make_client(extraction=CHAIN_EXTRACTION)
    ingest_chain(client)

    shallow = run_query(client, depth=0)["metrics"]["estimated_tokens"]
    deep = run_query(client, depth=3)["metrics"]["estimated_tokens"]
    assert 0 < shallow < deep  # deeper traversal sends more context
