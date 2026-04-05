import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Moon, Sun, Settings, X } from 'lucide-react';
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

  // Settings State
  const [showSettings, setShowSettings] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('gemini-2.5-flash');
  const [repulsion, setRepulsion] = useState(400);

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme as 'light' | 'dark');
    document.documentElement.setAttribute('data-theme', savedTheme);

    setApiKey(localStorage.getItem('apiKey') || '');
    setModel(localStorage.getItem('model') || 'gemini-2.5-flash');
    setRepulsion(Number(localStorage.getItem('repulsion')) || 400);
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  const handleSaveSettings = () => {
    localStorage.setItem('apiKey', apiKey);
    localStorage.setItem('model', model);
    localStorage.setItem('repulsion', repulsion.toString());
    setShowSettings(false);
  };

  const getHeaders = () => {
    if (apiKey.trim()) {
      return { 'x-api-key': apiKey.trim() };
    }
    return {};
  };

  const handleIngest = async () => {
    if (!ingestText.trim()) return;
    setIsIngesting(true);
    setIngestStatus('Extracting entities & relationships...');
    setError('');
    
    try {
      const res = await axios.post(`${API_URL}/ingest`, { text: ingestText, model }, { headers: getHeaders() });
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
      const res = await axios.post(`${API_URL}/query`, { query: queryText, depth, model }, { headers: getHeaders() });
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
            <div style={{ display: 'flex', gap: '8px' }}>
              <button className="icon-btn" onClick={() => setShowSettings(true)} aria-label="Settings">
                <Settings size={18} />
              </button>
              <button className="icon-btn" onClick={toggleTheme} aria-label="Toggle theme">
                {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
              </button>
            </div>
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
        <GraphVisualization data={graphData} theme={theme} repulsion={repulsion} />
      </div>

      {showSettings && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>Power Settings</h2>
              <button className="icon-btn" onClick={() => setShowSettings(false)}><X size={20} /></button>
            </div>
            
            <div className="setting-group">
              <label>Gemini API Key</label>
              <input 
                type="password" 
                placeholder="AIzaSy..." 
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
              <p className="setting-hint">If left blank, the backend's environment variable will be used.</p>
            </div>

            <div className="setting-group">
              <label>Extraction & Synthesis Model</label>
              <select value={model} onChange={(e) => setModel(e.target.value)}>
                <option value="gemini-2.5-flash">Gemini 2.5 Flash (Fast)</option>
                <option value="gemini-2.5-pro">Gemini 2.5 Pro (Deep Reasoning)</option>
              </select>
              <p className="setting-hint">Pro extracts significantly better graphs from complex documents.</p>
            </div>

            <div className="setting-group">
              <label>Graph Physics: Node Repulsion ({repulsion})</label>
              <input 
                type="range" 
                min="100" 
                max="1000" 
                step="50"
                value={repulsion} 
                onChange={(e) => setRepulsion(Number(e.target.value))} 
                style={{ width: '100%' }}
              />
              <p className="setting-hint">Increase this if your graph nodes are too clumped together.</p>
            </div>

            <button className="save-btn" onClick={handleSaveSettings}>Save & Close</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
