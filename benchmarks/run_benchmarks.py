"""Empirical comparison of standard RAG (depth 0) vs GraphRAG (depth 2).

Runs three multi-hop scenarios against a locally running backend. The
knowledge base is reset first so results are reproducible. Uses only the
standard library; requires GEMINI_API_KEY (env or backend/.env).

Usage:
    python3 benchmarks/run_benchmarks.py
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

API_URL = os.environ.get("GRAPHRAG_API_URL", "http://localhost:8000")
MODEL = "gemini-2.5-flash"

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY and os.path.exists("backend/.env"):
    with open("backend/.env") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                API_KEY = line.strip().split("=", 1)[1].strip("\"'")

SCENARIOS = [
    {
        "name": "Supply Chain Impact",
        "text": "The Salar de Atacama Lithium Mine has recently announced an indefinite strike due to labor disputes, completely halting operations. This facility is the sole provider of high-grade lithium carbonate to ElectroChem Industries, a major battery manufacturer based in Nevada.\n\nElectroChem Industries holds an exclusive contract to supply next-generation solid-state battery packs to Apex Motors. Apex Motors is currently ramping up production for their highly anticipated flagship vehicle, the \"Apex Nova EV\", which relies entirely on these specific solid-state battery packs.",
        "query": "How does a strike at the Lithium mine affect the production of the new EV model?",
    },
    {
        "name": "Corporate Mergers",
        "text": "WhatsApp, the ubiquitous messaging application known for its end-to-end encryption, was founded by Jan Koum and Brian Acton. In 2014, the messaging platform was acquired by Facebook Inc. in a landmark deal worth $19 billion.\n\nYears after a series of high-profile acquisitions, Facebook Inc. underwent a massive corporate restructuring and rebranded itself as Meta Platforms Inc. to reflect its new focus on the metaverse. Mark Zuckerberg, who originally founded the social network, remains the CEO of Meta Platforms Inc.",
        "query": "Who is the CEO of the parent company of WhatsApp?",
    },
    {
        "name": "Medical Research",
        "text": "Neuro-Degenerative Syndrome X (NDS-X) is a rare genetic disorder characterized by the rapid breakdown of motor neurons. Recent clinical trials have shown that the experimental drug \"Lumira-200\" is highly effective in treating the symptoms of NDS-X and slowing its progression.\n\nPharmacological studies reveal that \"Lumira-200\" functions primarily by acting as a potent inhibitor of the enzyme Kinase-Delta. Biochemical mapping further demonstrates that Kinase-Delta is a critical regulatory component within the broader Apoptosis-Alpha protein pathway.",
        "query": "What protein pathway is targeted by the drug treating Disease X?",
    },
]


def request(method, endpoint, data=None):
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    req = urllib.request.Request(
        f"{API_URL}/{endpoint}",
        data=json.dumps(data).encode("utf-8") if data is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"API error on {method} /{endpoint}: {exc.code} {body}")
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"Cannot reach the backend at {API_URL} ({exc.reason}).")
        print("Start it first: cd backend && uvicorn main:app")
        sys.exit(1)


def describe(result):
    metrics = result.get("metrics") or {}
    seeds = ", ".join(metrics.get("seed_entities", [])) or "none"
    return (
        f"entities={metrics.get('nodes_retrieved', 0)} "
        f"relationships={metrics.get('edges_retrieved', 0)} "
        f"context_tokens~{metrics.get('estimated_tokens', 0)} "
        f"(entry points: {seeds})"
    )


def run_benchmarks():
    print("=" * 50)
    print("GraphRAG Empirical Benchmarks")
    print("=" * 50 + "\n")

    print("0. Resetting knowledge base for a reproducible run...")
    request("DELETE", "graph")

    print("1. Ingesting test paragraphs into the knowledge graph...")
    for i, scenario in enumerate(SCENARIOS, start=1):
        print(f"  -> Ingesting scenario {i}: {scenario['name']}...")
        request("POST", "ingest", {"text": scenario["text"], "model": MODEL})
        time.sleep(3)  # stay under free-tier rate limits

    print("\n2. Running queries (standard RAG vs GraphRAG)...\n")
    for scenario in SCENARIOS:
        print(f"SCENARIO: {scenario['name']}")
        print(f"QUERY: {scenario['query']}\n")

        baseline = request(
            "POST", "query", {"query": scenario["query"], "depth": 0, "model": MODEL}
        )
        print(f"  [Standard RAG - depth 0] {describe(baseline)}")
        print(f"  Answer: {baseline.get('answer', 'No answer').strip()}\n")

        graphrag = request(
            "POST", "query", {"query": scenario["query"], "depth": 2, "model": MODEL}
        )
        print(f"  [GraphRAG - depth 2] {describe(graphrag)}")
        print(f"  Answer: {graphrag.get('answer', 'No answer').strip()}\n")
        print("-" * 50 + "\n")


if __name__ == "__main__":
    run_benchmarks()
