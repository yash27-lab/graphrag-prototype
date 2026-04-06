import os
import json
import networkx as nx
import chromadb
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
load_dotenv()

app = FastAPI()

# Secure CORS: Only allow local frontend development servers to access this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

def get_client(api_key: Optional[str] = None):
    # Prioritize client-provided key from Settings UI, fallback to local .env
    final_key = api_key or os.getenv("GEMINI_API_KEY")
    if final_key:
        return genai.Client(api_key=final_key)
    try:
        return genai.Client()
    except Exception:
        return None

# Initialize ChromaDB and NetworkX with persistence
PERSIST_DIR = "./data"
os.makedirs(PERSIST_DIR, exist_ok=True)

chroma_client = chromadb.PersistentClient(path=os.path.join(PERSIST_DIR, "chroma_db"))
collection = chroma_client.get_or_create_collection(name="graphrag_entities")

GRAPH_FILE = os.path.join(PERSIST_DIR, "graph.json")
if os.path.exists(GRAPH_FILE):
    try:
        with open(GRAPH_FILE, "r") as f:
            data = json.load(f)
            G = nx.node_link_graph(data)
    except Exception as e:
        print(f"Failed to load graph from {GRAPH_FILE}: {e}")
        G = nx.Graph()
else:
    G = nx.Graph()

def save_graph():
    data = nx.node_link_data(G)
    with open(GRAPH_FILE, "w") as f:
        json.dump(data, f)


class QueryRequest(BaseModel):
    query: str
    depth: int = 1
    model: str = 'gemini-2.5-flash'

class IngestRequest(BaseModel):
    text: str
    model: str = 'gemini-2.5-flash'

@app.post("/ingest")
def ingest_text(req: IngestRequest, x_api_key: Optional[str] = Header(None)):
    client = get_client(x_api_key)
    if not client:
        raise HTTPException(status_code=500, detail="GenAI client not initialized. Provide an API key in settings or environment.")
    
    prompt = f"""
    Extract key entities and their relationships from the following text.
    Return the result strictly as a JSON object with this structure:
    {{
        "entities": [
            {{"id": "entity_name", "type": "Person/Organization/Concept", "description": "brief description"}}
        ],
        "relationships": [
            {{"source": "entity1", "target": "entity2", "relationship": "relationship_type", "description": "brief description"}}
        ]
    }}
    Text: {req.text}
    """
    
    response = client.models.generate_content(
        model=req.model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        )
    )
    
    try:
        data = json.loads(response.text)
    except json.JSONDecodeError:
        print("Failed to decode JSON", response.text)
        raise HTTPException(status_code=500, detail="Failed to parse LLM response")

    entities = data.get("entities", [])
    relationships = data.get("relationships", [])

    for ent in entities:
        node_id = ent.get("id")
        if not node_id: continue
        G.add_node(node_id, **ent)
        collection.add(
            documents=[ent.get("description", "")],
            metadatas=[{"type": ent.get("type", "Concept"), "id": node_id}],
            ids=[node_id]
        )

    for rel in relationships:
        source = rel.get("source")
        target = rel.get("target")
        if source and target:
            G.add_edge(source, target, relationship=rel.get("relationship", ""), description=rel.get("description", ""))

    # Serialize the full graph to return it
    all_nodes = []
    all_links = []
    for n, data in G.nodes(data=True):
        all_nodes.append({"id": n, "label": n, "group": data.get('type', 'Unknown')})
    for u, v, data in G.edges(data=True):
        all_links.append({"source": u, "target": v, "label": data.get('relationship', '')})

    # Save to disk
    save_graph()

    return {
        "status": "success", 
        "entities_count": len(entities), 
        "relationships_count": len(relationships),
        "graph": {
            "nodes": all_nodes,
            "links": all_links
        }
    }

@app.post("/query")
def query_graphrag(req: QueryRequest, x_api_key: Optional[str] = Header(None)):
    client = get_client(x_api_key)
    if not client:
        raise HTTPException(status_code=500, detail="GenAI client not initialized. Provide an API key in settings or environment.")

    # 1. Vector Search: Find starting nodes
    results = collection.query(
        query_texts=[req.query],
        n_results=3
    )

    if not results["ids"] or not results["ids"][0]:
        return {"answer": "I don't have enough context to answer that.", "graph": {"nodes": [], "links": []}, "metrics": {}}

    start_nodes = results["ids"][0]
    
    # 2. Graph Traversal: Multi-hop reasoning based on depth
    context_nodes = set(start_nodes)
    current_level = set(start_nodes)
    
    for _ in range(req.depth):
        next_level = set()
        for node in current_level:
            if node in G:
                for neighbor in G.neighbors(node):
                    if neighbor not in context_nodes:
                        next_level.add(neighbor)
                        context_nodes.add(neighbor)
        current_level = next_level

    context_text = "Entities:\n"
    nodes_data = []
    links_data = []
    
    for n in context_nodes:
        if n in G:
            node_data = G.nodes[n]
            context_text += f"- {n} ({node_data.get('type', 'Unknown')}): {node_data.get('description', '')}\n"
            nodes_data.append({"id": n, "label": n, "group": node_data.get('type', 'Unknown')})
            
    context_text += "\nRelationships:\n"
    for u, v, data in G.edges(data=True):
        if u in context_nodes and v in context_nodes:
            rel = data.get('relationship', '')
            desc = data.get('description', '')
            context_text += f"- {u} --[{rel}]--> {v}: {desc}\n"
            links_data.append({"source": u, "target": v, "label": rel})

    # Estimate tokens to showcase pruning efficiency
    estimated_tokens = int(len(context_text.split()) * 1.3)

    # 3. Synthesis: Generate answer from pruned context
    synthesis_prompt = f"""
    Answer the user's query based ONLY on the provided Knowledge Graph context.
    
    Context:
    {context_text}
    
    User Query: {req.query}
    """
    
    response = client.models.generate_content(
        model=req.model,
        contents=synthesis_prompt
    )

    return {
        "answer": response.text,
        "graph": {
            "nodes": nodes_data,
            "links": links_data
        },
        "metrics": {
            "nodes_retrieved": len(context_nodes),
            "depth_used": req.depth,
            "estimated_tokens": estimated_tokens
        }
    }
