# GraphRAG Prototype

A functional prototype demonstrating Graph Retrieval-Augmented Generation (GraphRAG), addressing the limitations of standard RAG systems.

## Problem Statement

Standard Retrieval-Augmented Generation (RAG) relies heavily on dense vector similarity search. While effective for semantic matching, it struggles significantly with "multi-hop reasoning" or connecting distant pieces of information. When a query requires understanding the relationships between different entities that are not explicitly mentioned together in the source text, standard RAG often fails because it cannot follow logical connections across document chunks. This leads to fragmented context and hallucinations.

## Solution

GraphRAG solves this by extracting entities and their relationships into a structured Knowledge Graph. When a user queries the system, it does not just retrieve semantically similar text; it uses vector search to find relevant entry points (entities) and then traverses the graph to pull in logically connected concepts. This provides the Large Language Model (LLM) with a much richer, multi-hop context, resulting in highly accurate and comprehensive answers.

This prototype combines vector similarity search (ChromaDB) with graph traversal (NetworkX) to provide the LLM with this multi-hop context.

## Architecture

*   **Backend:** FastAPI (Python), NetworkX (In-memory Graph Database), ChromaDB (Vector Database), Google GenAI SDK (Gemini models).
*   **Frontend:** React (TypeScript), Vite, `react-force-graph-2d` for interactive force-directed graph visualization.

## Prerequisites

*   Node.js and npm
*   Python 3.9+
*   A Google Gemini API Key (`GEMINI_API_KEY`)

## Setup and Running

### Option A: Docker (Recommended)

To run the entire stack (Frontend + Backend with persistent storage) using Docker Compose:

```bash
# macOS users: If you don't have Docker Desktop, you can install Colima:
# brew install colima docker docker-compose
# colima start

# Set your API key (or put it in backend/.env)
export GEMINI_API_KEY="your_api_key_here"

docker compose up --build
```

The frontend will be available at `http://localhost:5173` and the backend at `http://localhost:8000`. The graph data and vector embeddings are automatically persisted to disk so they survive restarts.

### Option B: Manual Setup

**1. Backend**

Navigate to the backend directory:

```bash
cd backend
```

Install backend dependencies:

```bash
pip install -r requirements.txt
```

*(Optional) Configure Local Security:* 
To avoid pasting your API key in the frontend, you can securely configure the backend. Rename `backend/.env.example` to `backend/.env` and paste your key inside.

Start the FastAPI server:

```bash
uvicorn main:app --reload
```

The backend will run on `http://localhost:8000`.

**2. Frontend**

Open a new terminal window and navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the Vite development server:

```bash
npm run dev
```

Open your browser to `http://localhost:5173`.

## Usage

1.  **Ingest Data:** Paste a complex text or article into the "Ingest Knowledge" section and click "Build Knowledge Graph". The backend will use Gemini to extract entities and relationships, storing them in ChromaDB and NetworkX.
2.  **Query:** Set your desired **Traversal Depth** (1-3 hops) to control how far the system searches for logically connected concepts, then ask a question.
3.  **Visualize & Verify:** The UI will display the answer, render the specific subgraph used, and show **Context Pruning Metrics** (demonstrating how many tokens were actually sent to the LLM vs the whole database).

### Troubleshooting
*   **"Internal Server Error" during ingestion (429 RESOURCE_EXHAUSTED):** If you switch the model to `gemini-2.5-pro` in the UI settings, you may hit the strict rate limits of the free tier. Switch back to `gemini-2.5-flash` or set up billing in your Google Cloud project.

## Benchmarks: Standard RAG vs GraphRAG

To empirically demonstrate the value of GraphRAG, we have included an automated benchmarking script that runs 3 complex multi-hop scenarios. It queries the same dataset using both Standard RAG (Depth 0) and GraphRAG (Depth 2) and compares the retrieved context and answers.

You can run the benchmarks yourself against your local backend instance:

```bash
export GEMINI_API_KEY="your_api_key_here"
python3 benchmarks/run_benchmarks.py
```

### Example Benchmark Output

```text
==================================================
GraphRAG Empirical Benchmarks
==================================================

1. Ingesting test paragraphs into Knowledge Graph...
  -> Ingesting scenario 1: Supply Chain Impact...
  -> Ingesting scenario 2: Corporate Mergers...
  -> Ingesting scenario 3: Medical Research...

2. Running Queries (Standard RAG vs GraphRAG)...

SCENARIO: Supply Chain Impact
QUERY: How does a strike at the Lithium mine affect the production of the new EV model?

  [Standard RAG - Depth 0] - Retrieved 2 entities
  Answer: I don't have enough context to connect the mine to the EV model.

  [GraphRAG - Depth 2] - Retrieved 5 entities
  Answer: The strike at the Salar de Atacama Lithium Mine halts operations, which stops the supply of high-grade lithium carbonate to ElectroChem Industries. Without this material, ElectroChem cannot supply the next-generation solid-state battery packs to Apex Motors, which will delay or halt the production of the "Apex Nova EV".

--------------------------------------------------

SCENARIO: Corporate Mergers
QUERY: Who is the CEO of the parent company of WhatsApp?

  [Standard RAG - Depth 0] - Retrieved 1 entities
  Answer: The context does not mention the parent company of WhatsApp.

  [GraphRAG - Depth 2] - Retrieved 4 entities
  Answer: Mark Zuckerberg is the CEO of Meta Platforms Inc., which is the parent company of WhatsApp (having acquired it as Facebook Inc. and later rebranded).
```
