import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Moon, Sun } from 'lucide-react';
import './App.css';
import { GraphVisualization } from './components/GraphVisualization';

const API_URL = 'http://localhost:8000';

function App() {
  const [ingestText, setIngestText] = useState('');
  const [queryText, setQueryText] = useState('');
  const [ingestStatus, setIngestStatus] = useState('');
  const [isIngesting, setIsIngesting] = useState(false);
  
  const [response, setResponse] = useState('');
  const [graphData, setGraphData] = useState<any>(null);
  const [isQuerying, setIsQuerying] = useState(false);
  const [error, setError] = useState('');
  const [depth, setDepth] = useState(1);
  const [metrics, setMetrics] = useState<any>(null);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme as 'light' | 'dark');
    document.documentElement.setAttribute('data-theme', savedTheme);
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  const handleIngest = async () => {
    if (!ingestText.trim()) return;
    setIsIngesting(true);
    setIngestStatus('Extracting entities & relationships...');
    setError('');
    
    try {
      const res = await axios.post(`${API_URL}/ingest`, { text: ingestText });
      setIngestStatus(`Success! Extracted ${res.data.entities_count} entities and ${res.data.relationships_count} relationships.`);
      setIngestText('');
      if (res.data.graph) {
        setGraphData(res.data.graph);
        setResponse('Knowledge Graph successfully updated! You can now query it or visualize the full structure.');
        setMetrics(null);
      }
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to ingest data. Is the backend running and API key set?');
      setIngestStatus('');
    } finally {
      setIsIngesting(false);
    }
  };

  const handleQuery = async () => {
    if (!queryText.trim()) return;
    setIsQuerying(true);
    setResponse('Thinking & traversing graph...');
    setError('');
    setMetrics(null);

    try {
      const res = await axios.post(`${API_URL}/query`, { query: queryText, depth });
      setResponse(res.data.answer);
      setGraphData(res.data.graph);
      if (res.data.metrics) {
        setMetrics(res.data.metrics);
      }
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to query data.');
      setResponse('');
    } finally {
      setIsQuerying(false);
    }
  };

  return (
    <div className="app-container">
      <div className="sidebar">
        <div className="header">
          <div className="header-top" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h1>GraphRAG Prototype</h1>
            <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
              {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
            </button>
          </div>
          <p>Powered by Neo4j/NetworkX & Gemini</p>
        </div>

        <div className="ingest-section">
          <h2>1. Ingest Knowledge</h2>
          <textarea 
            placeholder="Paste text here to build the graph..."
            value={ingestText}
            onChange={(e) => setIngestText(e.target.value)}
            disabled={isIngesting}
          />
          <button onClick={handleIngest} disabled={isIngesting || !ingestText.trim()}>
            {isIngesting ? 'Ingesting...' : 'Build Knowledge Graph'}
          </button>
          {ingestStatus && <div className="status-message">{ingestStatus}</div>}
        </div>

        <div className="chat-section" style={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
          <h2>2. Query Graph</h2>
          <div className="controls-row">
            <label>Traversal Depth: {depth} {depth === 1 ? 'hop' : 'hops'}</label>
            <input 
              type="range" 
              min="1" 
              max="3" 
              value={depth} 
              onChange={(e) => setDepth(Number(e.target.value))} 
              disabled={isQuerying}
            />
          </div>
          <input 
            type="text" 
            placeholder="Ask a question..."
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
            disabled={isQuerying}
          />
          <button onClick={handleQuery} disabled={isQuerying || !queryText.trim()}>
            {isQuerying ? 'Searching...' : 'Search'}
          </button>
          
          <h2 style={{ marginTop: '15px' }}>Response</h2>
          <div className="response-box">
            {error ? <span className="error-message">{error}</span> : response}
            {metrics && !isQuerying && (
              <div className="metrics-box">
                <strong>Context Pruning Metrics:</strong><br/>
                Nodes retrieved: {metrics.nodes_retrieved}<br/>
                Estimated tokens sent to LLM: ~{metrics.estimated_tokens}<br/>
                <em>(Filtered from millions of possible tokens down to exactly what matters)</em>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="main-content">
        {graphData && graphData.nodes?.length > 0 && (
          <div className="graph-overlay">
            <h3>Retrieved Context Graph</h3>
            <p>Showing {graphData.nodes.length} entities & {graphData.links.length} connections</p>
          </div>
        )}
        <GraphVisualization data={graphData} theme={theme} />
      </div>
    </div>
  );
}

export default App;
