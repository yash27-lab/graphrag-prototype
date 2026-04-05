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

### 1. Backend

Navigate to the backend directory:

```bash
cd backend
```

Activate the virtual environment:

```bash
source venv/bin/activate
```

Install backend dependencies:

```bash
pip install fastapi uvicorn networkx chromadb pydantic google-genai fastapi-cors python-dotenv
```

*(Optional) Configure Local Security:* 
To avoid pasting your API key in the frontend, you can securely configure the backend. Rename `backend/.env.example` to `backend/.env` and paste your key inside.

Start the FastAPI server:

```bash
uvicorn main:app --reload
```

The backend will run on `http://localhost:8000`.

### 2. Frontend

Open a new terminal window and navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies (if not already installed):

```bash
npm install
```

Start the Vite development server:

```bash
npm run dev
```

Open your browser to the URL provided by Vite (usually `http://localhost:5173`).

## Usage

1.  **Ingest Data:** Paste a complex text or article into the "Ingest Knowledge" section and click "Build Knowledge Graph". The backend will use Gemini to extract entities and relationships, storing them in ChromaDB and NetworkX.
2.  **Query:** Set your desired **Traversal Depth** (1-3 hops) to control how far the system searches for logically connected concepts, then ask a question.
3.  **Visualize & Verify:** The UI will display the answer, render the specific subgraph used, and show **Context Pruning Metrics** (demonstrating how many tokens were actually sent to the LLM vs the whole database).
