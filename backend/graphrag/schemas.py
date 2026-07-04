"""Request and response models for the HTTP API."""

from typing import List, Optional

from pydantic import BaseModel, Field

MAX_TRAVERSAL_DEPTH = 3
MAX_INGEST_CHARS = 50_000


class IngestRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_INGEST_CHARS)
    model: str = "gemini-2.5-flash"


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2_000)
    depth: int = Field(1, ge=0, le=MAX_TRAVERSAL_DEPTH)
    top_k: int = Field(3, ge=1, le=10)
    model: str = "gemini-2.5-flash"


class GraphNode(BaseModel):
    id: str
    label: str
    group: str = "Unknown"


class GraphLink(BaseModel):
    source: str
    target: str
    label: str = ""


class GraphPayload(BaseModel):
    nodes: List[GraphNode]
    links: List[GraphLink]


class IngestResponse(BaseModel):
    status: str
    entities_count: int
    relationships_count: int
    graph: GraphPayload


class QueryMetrics(BaseModel):
    seed_entities: List[str]
    nodes_retrieved: int
    edges_retrieved: int
    depth_used: int
    estimated_tokens: int


class QueryResponse(BaseModel):
    answer: str
    graph: GraphPayload
    metrics: Optional[QueryMetrics] = None


class HealthResponse(BaseModel):
    status: str
    entities: int
    relationships: int


class ResetResponse(BaseModel):
    status: str
