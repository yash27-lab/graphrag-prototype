"""Unit tests for GraphStore traversal and persistence edge cases."""

from graphrag.graph_store import GraphStore

CHAIN = {
    "entities": [
        {"id": "A", "type": "T", "description": "node a"},
        {"id": "B", "type": "T", "description": "node b"},
        {"id": "C", "type": "T", "description": "node c"},
    ],
    "relationships": [
        {"source": "A", "target": "B", "relationship": "r1"},
        {"source": "B", "target": "C", "relationship": "r2"},
    ],
}


def make_store(tmp_path):
    store = GraphStore(str(tmp_path / "graph.json"))
    store.upsert(CHAIN["entities"], CHAIN["relationships"])
    return store


def test_expand_by_depth(tmp_path):
    store = make_store(tmp_path)
    assert store.expand(["A"], depth=0) == {"A"}
    assert store.expand(["A"], depth=1) == {"A", "B"}
    assert store.expand(["A"], depth=2) == {"A", "B", "C"}
    assert store.expand(["A"], depth=99) == {"A", "B", "C"}  # stops at frontier


def test_expand_ignores_unknown_seeds(tmp_path):
    store = make_store(tmp_path)
    assert store.expand(["A", "does-not-exist"], depth=1) == {"A", "B"}


def test_upsert_does_not_clobber_with_empty_values(tmp_path):
    store = make_store(tmp_path)
    store.upsert([{"id": "A", "type": "T", "description": ""}], [])
    assert store.node_records(["A"])[0]["description"] == "node a"


def test_corrupted_file_starts_fresh(tmp_path):
    path = tmp_path / "graph.json"
    path.write_text("{ this is not json")
    store = GraphStore(str(path))
    assert store.stats() == (0, 0)


def test_roundtrip_persistence(tmp_path):
    make_store(tmp_path)
    reloaded = GraphStore(str(tmp_path / "graph.json"))
    assert reloaded.stats() == (3, 2)
    assert reloaded.expand(["A"], depth=2) == {"A", "B", "C"}
