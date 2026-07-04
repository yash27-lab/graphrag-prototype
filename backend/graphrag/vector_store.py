"""Entity embedding index backed by ChromaDB.

Each graph entity gets one embedding, used only to find entry points for
graph traversal. The embedding function is injectable so tests run
hermetically without downloading the default ONNX model.
"""

import os
from typing import Any, Dict, List, Optional

# Opt out of Chroma's anonymized telemetry before the client is imported;
# it adds noise to logs and phones home from a local tool.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb  # noqa: E402

COLLECTION_NAME = "graphrag_entities"


class VectorStore:
    def __init__(self, persist_path: str, embedding_function: Optional[Any] = None) -> None:
        self._client = chromadb.PersistentClient(path=persist_path)
        self._embedding_function = embedding_function
        self._collection = self._get_collection()

    def upsert_entities(self, entities: List[Dict[str, Any]]) -> None:
        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict[str, str]] = []
        for ent in entities:
            entity_id = ent.get("id")
            if not entity_id:
                continue
            ids.append(entity_id)
            # Embed the name alongside the description so queries that mention
            # an entity by name match even when its description does not.
            description = ent.get("description") or entity_id
            documents.append(f"{entity_id}: {description}")
            metadatas.append({"type": ent.get("type", "Concept"), "id": entity_id})
        if ids:
            self._collection.upsert(documents=documents, metadatas=metadatas, ids=ids)

    def find_entry_points(self, query: str, top_k: int) -> List[str]:
        count = self._collection.count()
        if count == 0:
            return []
        results = self._collection.query(query_texts=[query], n_results=min(top_k, count))
        ids = results.get("ids") or []
        return ids[0] if ids else []

    def clear(self) -> None:
        self._client.delete_collection(COLLECTION_NAME)
        self._collection = self._get_collection()

    def _get_collection(self) -> chromadb.Collection:
        kwargs: Dict[str, Any] = {}
        if self._embedding_function is not None:
            kwargs["embedding_function"] = self._embedding_function
        return self._client.get_or_create_collection(name=COLLECTION_NAME, **kwargs)
