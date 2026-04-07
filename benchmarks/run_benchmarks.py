import json
import urllib.request
import time
import sys

import os

API_URL = "http://localhost:8000"

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY and os.path.exists("backend/.env"):
    with open("backend/.env") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                API_KEY = line.strip().split("=", 1)[1].strip('"\'')

def get_headers():
    headers = {'Content-Type': 'application/json'}
    if API_KEY:
        headers['x-api-key'] = API_KEY
    return headers

SCENARIOS = [
    {
        "name": "Supply Chain Impact",
        "text": "The Salar de Atacama Lithium Mine has recently announced an indefinite strike due to labor disputes, completely halting operations. This facility is the sole provider of high-grade lithium carbonate to ElectroChem Industries, a major battery manufacturer based in Nevada.\n\nElectroChem Industries holds an exclusive contract to supply next-generation solid-state battery packs to Apex Motors. Apex Motors is currently ramping up production for their highly anticipated flagship vehicle, the \"Apex Nova EV\", which relies entirely on these specific solid-state battery packs.",
        "query": "How does a strike at the Lithium mine affect the production of the new EV model?"
    },
    {
        "name": "Corporate Mergers",
        "text": "WhatsApp, the ubiquitous messaging application known for its end-to-end encryption, was founded by Jan Koum and Brian Acton. In 2014, the messaging platform was acquired by Facebook Inc. in a landmark deal worth $19 billion.\n\nYears after a series of high-profile acquisitions, Facebook Inc. underwent a massive corporate restructuring and rebranded itself as Meta Platforms Inc. to reflect its new focus on the metaverse. Mark Zuckerberg, who originally founded the social network, remains the CEO of Meta Platforms Inc.",
        "query": "Who is the CEO of the parent company of WhatsApp?"
    },
    {
        "name": "Medical Research",
        "text": "Neuro-Degenerative Syndrome X (NDS-X) is a rare genetic disorder characterized by the rapid breakdown of motor neurons. Recent clinical trials have shown that the experimental drug \"Lumira-200\" is highly effective in treating the symptoms of NDS-X and slowing its progression.\n\nPharmacological studies reveal that \"Lumira-200\" functions primarily by acting as a potent inhibitor of the enzyme Kinase-Delta. Biochemical mapping further demonstrates that Kinase-Delta is a critical regulatory component within the broader Apoptosis-Alpha protein pathway.",
        "query": "What protein pathway is targeted by the drug treating Disease X?"
    }
]

def post_json(endpoint, data):
    req = urllib.request.Request(
        f"{API_URL}/{endpoint}",
        data=json.dumps(data).encode('utf-8'),
        headers=get_headers()
    )
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"API Error: {e}")
        sys.exit(1)

def run_benchmarks():
    print("==================================================")
    print("GraphRAG Empirical Benchmarks")
    print("==================================================\n")
    
    print("1. Ingesting test paragraphs into Knowledge Graph...")
    for i, scene in enumerate(SCENARIOS):
        print(f"  -> Ingesting scenario {i+1}: {scene['name']}...")
        post_json("ingest", {"text": scene['text'], "model": "gemini-2.5-flash"})
        time.sleep(3) # Avoid hitting API rate limits

    print("\n2. Running Queries (Standard RAG vs GraphRAG)...\n")
    
    for scene in SCENARIOS:
        print(f"SCENARIO: {scene['name']}")
        print(f"QUERY: {scene['query']}\n")
        
        # Standard RAG (Depth 0)
        res_0 = post_json("query", {"query": scene['query'], "depth": 0, "model": "gemini-2.5-flash"})
        nodes_0 = res_0.get('metrics', {}).get('nodes_retrieved', 0)
        ans_0 = res_0.get('answer', 'No answer')
        
        print(f"  [Standard RAG - Depth 0] - Retrieved {nodes_0} entities")
        print(f"  Answer: {ans_0}\n")
        
        # GraphRAG (Depth 2)
        res_2 = post_json("query", {"query": scene['query'], "depth": 2, "model": "gemini-2.5-flash"})
        nodes_2 = res_2.get('metrics', {}).get('nodes_retrieved', 0)
        ans_2 = res_2.get('answer', 'No answer')
        
        print(f"  [GraphRAG - Depth 2] - Retrieved {nodes_2} entities")
        print(f"  Answer: {ans_2}\n")
        print("-" * 50 + "\n")

if __name__ == "__main__":
    run_benchmarks()
