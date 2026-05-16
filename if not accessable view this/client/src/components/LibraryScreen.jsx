import React, { useState, useEffect, useCallback } from 'react';
import { fetchWorkflows, executeWorkflow } from '../api/api.js';

const WF_ICONS = ['🔮', '⚡', '🤖', '🌐', '📧', '📊', '📱', '🔗', '📅', '🧠'];

function timeAgo(iso) {
  if (!iso) return 'Unknown';
  const d = new Date(iso);
  const diff = (Date.now() - d) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function LibraryScreen({ onGoHome, onViewWorkflow }) {
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [execStates, setExecStates] = useState({});
  const [execResults, setExecResults] = useState({});
  const [modalWf, setModalWf] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchWorkflows();
      setWorkflows(Array.isArray(data) ? data.reverse() : []);
    } catch {
      setWorkflows([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleExecute = async (wf) => {
    const id = wf.id;
    setExecStates(p => ({ ...p, [id]: 'running' }));
    try {
      const res = await executeWorkflow(id);
      setExecStates(p => ({ ...p, [id]: 'done' }));
      setExecResults(p => ({ ...p, [id]: res }));
      setModalWf({ wf, result: res });
    } catch (e) {
      setExecStates(p => ({ ...p, [id]: 'error' }));
      setExecResults(p => ({ ...p, [id]: { error: e.message } }));
      setModalWf({ wf, result: { error: e.message } });
    }
  };

  return (
    <div className="library-screen">
      <div className="library-header">
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
          <div>
            <h1 className="library-title">📚 Workflow Library</h1>
            <p className="library-sub">
              {loading ? 'Loading…' : `${workflows.length} saved workflow${workflows.length !== 1 ? 's' : ''} — click Execute to run any`}
            </p>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button
              onClick={load}
              style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border2)', borderRadius: 10, padding: '8px 16px', color: 'var(--text-h)', cursor: 'pointer', fontSize: 14 }}
            >
              🔄 Refresh
            </button>
            <button
              onClick={onGoHome}
              style={{ background: 'linear-gradient(135deg, #7c3aed, #a855f7)', border: 'none', borderRadius: 10, padding: '8px 20px', color: '#fff', cursor: 'pointer', fontSize: 14, fontWeight: 600 }}
            >
              + New Workflow
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '80px 0' }}>
          <div className="spinner" style={{ width: 40, height: 40, borderWidth: 4, borderTopColor: 'var(--accent2)' }} />
        </div>
      ) : workflows.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📭</div>
          <div className="empty-title">No saved workflows yet</div>
          <div className="empty-sub">Generate a workflow and save it to see it here.</div>
          <button onClick={onGoHome} style={{ marginTop: 24, background: 'linear-gradient(135deg, #7c3aed, #a855f7)', border: 'none', borderRadius: 12, padding: '12px 28px', color: '#fff', cursor: 'pointer', fontSize: 15, fontWeight: 600 }}>
            Create First Workflow
          </button>
        </div>
      ) : (
        <div className="workflows-grid">
          {workflows.map((wf, i) => {
            const id = wf.id;
            const state = execStates[id];
            const nodeCount = wf.workflow_graph?.nodes?.length || 0;
            const edgeCount = wf.workflow_graph?.edges?.length || 0;
            const icon = WF_ICONS[i % WF_ICONS.length];
            return (
              <div key={id} className="wf-card" style={{ animationDelay: `${i * 0.06}s` }}>
                <div className="wf-card-header">
                  <div className="wf-card-icon">{icon}</div>
                  <div className="wf-card-goal">{wf.goal || 'Unnamed Workflow'}</div>
                </div>
                <div className="wf-card-meta">
                  <span className="wf-meta-chip">📦 {nodeCount} nodes</span>
                  <span className="wf-meta-chip">🔗 {edgeCount} edges</span>
                  {(wf.required_credentials || []).slice(0, 2).map(c => (
                    <span key={c} className="wf-meta-chip">🔑 {c}</span>
                  ))}
                  {state === 'done' && <span className="wf-meta-chip" style={{ color: '#6ee7b7', borderColor: 'rgba(16,185,129,0.3)' }}>✅ Last run OK</span>}
                  {state === 'error' && <span className="wf-meta-chip" style={{ color: '#fca5a5', borderColor: 'rgba(239,68,68,0.3)' }}>❌ Last run failed</span>}
                </div>
                <div className="wf-card-footer">
                  <div className="wf-date">{timeAgo(wf.created_at)}</div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      className="wf-exec-btn"
                      style={{ background: 'rgba(255,255,255,0.08)', boxShadow: 'none' }}
                      onClick={() => onViewWorkflow(wf)}
                    >
                      👁 View
                    </button>
                    <button
                      className="wf-exec-btn"
                      onClick={() => handleExecute(wf)}
                      disabled={state === 'running'}
                    >
                      {state === 'running'
                        ? <><div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Running…</>
                        : '▶ Execute'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Result Modal */}
      {modalWf && (
        <div className="exec-result-modal" onClick={() => setModalWf(null)}>
          <div className="exec-modal-box" onClick={e => e.stopPropagation()}>
            <div className="exec-modal-title">
              {modalWf.result?.error ? '❌ Execution Failed' : '✅ Execution Complete'}
              <button className="exec-modal-close" onClick={() => setModalWf(null)}>×</button>
            </div>
            <p style={{ fontSize: 13, color: 'var(--text)', marginBottom: 16 }}>{modalWf.wf.goal}</p>
            <div className="exec-modal-output">
              {modalWf.result?.error
                ? modalWf.result.error
                : JSON.stringify(modalWf.result, null, 2)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
