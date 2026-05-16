import React, { useState, useEffect } from 'react';
import {
  saveWorkflow,
  fetchMissingCredentials,
  executeWorkflow
} from '../api/api.js';

export default function WorkflowResult({ data, onWorkflowSaved, currentGoal }) {
  const {
    analysis,
    research,
    selected_components,
    workflow,
    required_credentials,
    validation
  } = data;

  const [savedWorkflowId, setSavedWorkflowId] = useState(null);
  const [missingCreds, setMissingCreds] = useState([]);
  const [executing, setExecuting] = useState(false);

  const handleSave = async () => {
    try {
      // 🔥 Use the actual user goal, not the fallback "Unnamed workflow"
      const goal = currentGoal || "My workflow";
      const result = await saveWorkflow(goal, workflow, required_credentials);
      setSavedWorkflowId(result.id);
      const missing = await fetchMissingCredentials(result.id);
      setMissingCreds(missing);
      if (onWorkflowSaved) onWorkflowSaved(result);
    } catch (err) {
      alert("Failed to save workflow: " + err.message);
    }
  };

  useEffect(() => {
    if (savedWorkflowId) {
      fetchMissingCredentials(savedWorkflowId).then(setMissingCreds);
    }
  }, [savedWorkflowId]);

  const handleExecute = async () => {
    if (!savedWorkflowId) return;
    setExecuting(true);
    try {
      const result = await executeWorkflow(savedWorkflowId);
      alert("Workflow executed successfully! " + JSON.stringify(result));
    } catch (err) {
      alert("Execution failed: " + err.message);
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="result-container">
      <h2>📦 Generated Workflow</h2>

      {analysis && Object.keys(analysis).length > 0 && (
        <div className="section">
          <h3>🧩 Analysis</h3>
          <ul>
            {analysis.tasks?.map((t, i) => <li key={i}>{t}</li>)}
          </ul>
          {analysis.entities && Object.keys(analysis.entities).length > 0 && (
            <p><strong>Entities:</strong> {JSON.stringify(analysis.entities)}</p>
          )}
          {analysis.requirements?.length > 0 && (
            <p><strong>Requirements:</strong> {analysis.requirements.join(', ')}</p>
          )}
        </div>
      )}

      {research && research.research_notes?.length > 0 && (
        <div className="section">
          <h3>🔍 Research Notes</h3>
          <ul>
            {research.research_notes.map((note, i) => <li key={i}>{note}</li>)}
          </ul>
        </div>
      )}

      {selected_components?.length > 0 && (
        <div className="section">
          <h3>⚙️ Selected Components</h3>
          <div className="node-list">
            {selected_components.map((comp, i) => (
              <span className="node-chip" key={i}>{comp}</span>
            ))}
          </div>
        </div>
      )}

      {workflow && (
        <div className="section">
          <h3>🔗 Workflow Graph</h3>
          <div className="workflow-graph">
            <div>
              <strong>Nodes:</strong>
              <div className="node-list">
                {workflow.nodes?.map((n) => (
                  <span className="node-chip" key={n.id}>
                    {n.label} ({n.id})
                  </span>
                ))}
              </div>
            </div>
            <div>
              <strong>Edges:</strong>
              <div className="edge-list">
                {workflow.edges?.map((e, i) => (
                  <span className="edge-item" key={i}>
                    {e.source} → {e.target}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {validation && (
        <div className="section">
          <h3>✅ Validation</h3>
          {validation.is_valid ? (
            <p className="success">✔ Workflow is valid</p>
          ) : (
            <div className="validation-errors">
              {validation.errors?.map((err, i) => (
                <p className="error-message" key={i}>⚠ {err}</p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Save / Execute / Credentials Panel */}
      <div className="section">
        {!savedWorkflowId ? (
          <button className="generate-btn" onClick={handleSave}>
            💾 Save Workflow
          </button>
        ) : (
          <div>
            <p><strong>Workflow saved (ID: {savedWorkflowId})</strong></p>
            <div>
              <h3>🔐 Required Credentials</h3>
              {required_credentials?.length > 0 ? (
                <div>
                  {required_credentials.map((cred) => {
                    const envVar = cred.toUpperCase();
                    const missing = missingCreds.includes(envVar);
                    return (
                      <div key={cred} style={{ margin: '0.5rem 0' }}>
                        <span className="credential-chip">{cred}</span>
                        <span style={{ marginLeft: '1rem', color: missing ? 'red' : 'green' }}>
                          {missing ? `❌ Set ${envVar} in .env` : '✅ Set'}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p>No credentials required.</p>
              )}
            </div>
            <button
              className="generate-btn"
              onClick={handleExecute}
              disabled={executing || missingCreds.length > 0}
              style={{ marginTop: '1rem', opacity: missingCreds.length > 0 ? 0.5 : 1 }}
            >
              {executing ? 'Executing...' : '▶ Execute Workflow'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}