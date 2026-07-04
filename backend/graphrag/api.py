"""HTTP API for the GraphRAG prototype.

``create_app`` is a factory so tests can wire in a fake LLM, a deterministic
embedding function, and a temporary persistence directory.
"""

import os
from typing import Any, Optional

from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings
from .graph_store import GraphStore
from .llm import GeminiService, LLMError
from .pipeline import GraphRAGPipeline
from .schemas import (
    GraphPayload,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    ResetResponse,
)
from .vector_store import VectorStore


def create_app(
    settings: Optional[Settings] = None,
    llm: Optional[Any] = None,
    embedding_function: Optional[Any] = None,
) -> FastAPI:
    settings = settings or Settings()
    os.makedirs(settings.persist_dir, exist_ok=True)

    pipeline = GraphRAGPipeline(
        graph=GraphStore(os.path.join(settings.persist_dir, "graph.json")),
        vectors=VectorStore(
            os.path.join(settings.persist_dir, "chroma_db"),
            embedding_function=embedding_function,
        ),
        llm=llm if llm is not None else GeminiService(default_api_key=settings.gemini_api_key),
    )

    app = FastAPI(
        title="GraphRAG Prototype",
        description=(
            "Retrieval-augmented generation over an entity knowledge graph: "
            "vector search finds entry points, graph traversal supplies "
            "multi-hop context, and the LLM answers from that pruned context."
        ),
        version="1.0.0",
    )
    app.state.pipeline = pipeline

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.exception_handler(LLMError)
    async def handle_llm_error(request: Request, exc: LLMError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.get("/health", response_model=HealthResponse)
    def health() -> Any:
        return {"status": "ok", **pipeline.stats()}

    @app.post("/ingest", response_model=IngestResponse)
    def ingest(req: IngestRequest, x_api_key: Optional[str] = Header(None)) -> Any:
        return pipeline.ingest(req.text, req.model, api_key=x_api_key)

    @app.post("/query", response_model=QueryResponse)
    def query(req: QueryRequest, x_api_key: Optional[str] = Header(None)) -> Any:
        return pipeline.query(
            req.query, req.depth, req.top_k, req.model, api_key=x_api_key
        )

    @app.get("/graph", response_model=GraphPayload)
    def get_graph() -> Any:
        return pipeline.graph_payload()

    @app.delete("/graph", response_model=ResetResponse)
    def reset_graph() -> Any:
        pipeline.reset()
        return {"status": "reset"}

    return app
