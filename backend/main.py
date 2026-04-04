import os
import json
import networkx as nx
import chromadb
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize GenAI Client
# Expects GEMINI_API_KEY in environment
try:
    client = genai.Client()
except Exception as e:
    print(f"Failed to initialize GenAI client. Is GEMINI_API_KEY set? {e}")
    client = None

# Initialize ChromaDB and NetworkX
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="graphrag_entities")
G = nx.Graph()

class QueryRequest(BaseModel):
    query: str
    depth: int = 1

class IngestRequest(BaseModel):
    text: str

@app.post("/ingest")
def ingest_text(req: IngestRequest):
    if not client:
        raise HTTPException(status_code=500, detail="GenAI client not initialized")
    
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
        model='gemini-2.5-flash',
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
def query_graphrag(req: QueryRequest):
    if not client:
        raise HTTPException(status_code=500, detail="GenAI client not initialized")

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
        model='gemini-2.5-flash',
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
