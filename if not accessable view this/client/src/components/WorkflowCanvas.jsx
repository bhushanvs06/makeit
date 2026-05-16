import React, { useCallback, useMemo, useEffect, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  MarkerType,
  BackgroundVariant,
  Handle,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { saveWorkflow, executeWorkflow, fetchMissingCredentials } from '../api/api.js';

/* ── Icon map ── */
const ICON_MAP = {
  web_search: '🌐', google_search: '🌐', serp: '🌐',
  gmail: '📧', email: '📧', mail: '📧',
  google_sheets: '📊', sheets: '📊', spreadsheet: '📊',
  whatsapp: '📱', whatsapp_sender: '📱', whatsapp_trigger: '📱',
  google_calendar: '📅', calendar: '📅', google_meet: '📹', meet: '📹',
  gemini: '🤖', openai: '🤖', ai: '🤖', llm: '🤖', chatgpt: '🤖',
  http: '🔗', webhook: '🔗', api: '🔗',
  code: '⚙️', transform: '⚙️', python: '⚙️',
  trigger: '⚡', start: '⚡', input: '⚡',
  output: '📤', result: '📤',
  filter: '🔀', router: '🔀', condition: '🔀',
  delay: '⏳', wait: '⏳',
};

function getIcon(node) {
  const id = (node.component_id || node.id || '').toLowerCase();
  const label = (node.label || '').toLowerCase();
  for (const [key, icon] of Object.entries(ICON_MAP)) {
    if (id.includes(key) || label.includes(key)) return icon;
  }
  return '📦';
}

/* ── Custom Node ── */
function CustomNode({ data }) {
  const activeClass = data.isActive ? ' active-exec' : '';
  return (
    <div className={`custom-node${activeClass}`} style={{ '--node-color': data.color || '#7c3aed' }}>
      <Handle type="target" position={Position.Left} style={{ width: 8, height: 8, background: '#a855f7', border: 'none' }} />
      {data.badge && <div className="custom-node-badge">{data.badge}</div>}
      <div className="custom-node-icon">{data.icon}</div>
      <div className="custom-node-label">{data.label}</div>
      {data.type && <div className="custom-node-type">{data.type}</div>}
      <Handle type="source" position={Position.Right} style={{ width: 8, height: 8, background: '#a855f7', border: 'none' }} />
    </div>
  );
}

const nodeTypes = { custom: CustomNode };

const NODE_COLORS = ['#7c3aed', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#6366f1'];

/* ── Layout: auto-arrange left-to-right ── */
function layoutNodes(rawNodes, rawEdges) {
  if (!rawNodes?.length) return { nodes: [], edges: [] };
  const levels = {};
  const edgeMap = {};
  rawEdges?.forEach(e => {
    (edgeMap[e.source] = edgeMap[e.source] || []).push(e.target);
  });
  const visited = new Set();
  const queue = [rawNodes[0].id];
  levels[rawNodes[0].id] = 0;
  while (queue.length) {
    const cur = queue.shift();
    if (visited.has(cur)) continue;
    visited.add(cur);
    (edgeMap[cur] || []).forEach(t => {
      if (levels[t] === undefined) levels[t] = (levels[cur] || 0) + 1;
      queue.push(t);
    });
  }
  rawNodes.forEach(n => { if (levels[n.id] === undefined) levels[n.id] = 0; });

  const levelCounts = {};
  const levelIdxs = {};
  rawNodes.forEach(n => {
    const lv = levels[n.id];
    levelCounts[lv] = (levelCounts[lv] || 0) + 1;
  });
  rawNodes.forEach(n => {
    const lv = levels[n.id];
    levelIdxs[lv] = (levelIdxs[lv] || 0);
    const count = levelCounts[lv];
    const yOffset = (count - 1) * 120 / 2;
    n._x = lv * 260 + 60;
    n._y = levelIdxs[lv] * 120 - yOffset + 240;
    levelIdxs[lv]++;
  });

  const nodes = rawNodes.map((n, i) => ({
    id: String(n.id),
    type: 'custom',
    position: { x: n._x || i * 260 + 60, y: n._y || 240 },
    data: {
      label: n.label || n.id,
      icon: getIcon(n),
      type: n.component_id || n.type || '',
      color: NODE_COLORS[i % NODE_COLORS.length],
      badge: i === 0 ? 'START' : undefined,
    },
  }));

  const edges = (rawEdges || []).map((e, i) => ({
    id: `e-${i}-${e.source}-${e.target}`,
    source: String(e.source),
    target: String(e.target),
    animated: true,
    style: { stroke: '#a855f7', strokeWidth: 2 },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 20,
      height: 20,
      color: '#a855f7',
    },
  }));

  return { nodes, edges };
}

export default function WorkflowCanvas({ data, goal, loading, logs, onGoLibrary }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [savedId, setSavedId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [missingCreds, setMissingCreds] = useState([]);
  const [execResult, setExecResult] = useState(null);
  const [nodeRevealIdx, setNodeRevealIdx] = useState(0);
  const [activeNodeId, setActiveNodeId] = useState(null);
  const wsRef = React.useRef(null);

  const { nodes: allNodes, edges: allEdges } = useMemo(() => {
    if (!data?.workflow) return { nodes: [], edges: [] };
    const layout = layoutNodes(data.workflow.nodes, data.workflow.edges);
    return layout;
  }, [data]);

  useEffect(() => {
    setNodes(nds => nds.map(n => ({
      ...n,
      data: { ...n.data, isActive: n.id === activeNodeId }
    })));
  }, [activeNodeId, setNodes]);

  // Initialize nodes and edges once
  useEffect(() => {
    if (allNodes.length > 0) {
      setNodes(allNodes);
      // slight delay for edges to allow nodes to pop in via CSS
      setTimeout(() => setEdges(allEdges), 300);
    } else {
      setNodes([]);
      setEdges([]);
    }
  }, [allNodes, allEdges, setNodes, setEdges]);

  const handleSave = async () => {
    if (!data?.workflow || saving) return;
    setSaving(true);
    try {
      const res = await saveWorkflow(goal, data.workflow, data.required_credentials || []);
      setSavedId(res.id);
      const missing = await fetchMissingCredentials(res.id);
      setMissingCreds(missing);
    } catch (e) {
      alert('Save failed: ' + e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleExecute = async () => {
    if (!savedId || executing) return;
    setExecuting(true);
    setExecResult(null);
    setActiveNodeId(null);

    // Listen to execution events via WS
    if (wsRef.current) wsRef.current.close();
    wsRef.current = new WebSocket('ws://localhost:8000/ws/logs');
    wsRef.current.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'node_start') {
          setActiveNodeId(msg.node_id);
        } else if (msg.type === 'node_finish') {
          setActiveNodeId(null);
        }
      } catch (e) {}
    };

    try {
      const res = await executeWorkflow(savedId);
      setExecResult(res);
    } catch (e) {
      setExecResult({ error: e.message });
    } finally {
      setExecuting(false);
      setActiveNodeId(null);
      if (wsRef.current) wsRef.current.close();
    }
  };

  if (!data && !loading) {
    return (
      <div className="workflow-screen">
        <div className="empty-state">
          <div className="empty-icon">⚡</div>
          <div className="empty-title">No workflow yet</div>
          <div className="empty-sub">Submit a goal from the home screen to generate one.</div>
        </div>
      </div>
    );
  }

  return (
    <div className="workflow-screen">
      <div className="workflow-header">
        <div>
          <div className="workflow-title">⚡ Workflow Canvas</div>
          <div className="workflow-goal-tag">"{goal}"</div>
        </div>
        <div className="workflow-actions">
          {/* Credential badges */}
          {savedId && (data?.required_credentials || []).map(c => {
            const env = c.toUpperCase();
            const missing = missingCreds.includes(env);
            return (
              <span key={c} className={`cred-badge ${missing ? 'cred-miss' : 'cred-ok'}`}>
                {missing ? '❌' : '✅'} {c}
              </span>
            );
          })}
          {!savedId ? (
            <button className="wf-btn wf-btn-save" onClick={handleSave} disabled={saving || !data?.workflow}>
              {saving ? <><div className="spinner" style={{ borderTopColor: 'var(--accent2)' }} /> Saving…</> : '💾 Save'}
            </button>
          ) : (
            <button
              className="wf-btn wf-btn-exec"
              onClick={handleExecute}
              disabled={executing || missingCreds.length > 0}
            >
              {executing ? <><div className="spinner" /> Running…</> : '▶ Execute'}
            </button>
          )}
          <button className="wf-btn" style={{ background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)', color: '#6ee7b7' }} onClick={onGoLibrary}>
            📚 Library
          </button>
        </div>
      </div>

      {/* Node/Edge info bar */}
      {data?.workflow && (
        <div style={{ padding: '12px 40px', display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          {[
            ['📦', `${data.workflow.nodes?.length || 0} Nodes`],
            ['🔗', `${data.workflow.edges?.length || 0} Edges`],
            [data?.validation?.is_valid ? '✅' : '⚠️', data?.validation?.is_valid ? 'Valid' : 'Check Validation'],
            ...(data?.selected_components?.slice(0, 3).map(c => ['⚙️', c]) || []),
          ].map(([icon, label], i) => (
            <div key={i} style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: '4px 12px',
              fontSize: 13,
              color: 'var(--text)',
              display: 'flex', alignItems: 'center', gap: 6,
            }}>
              {icon} {label}
            </div>
          ))}
        </div>
      )}

      <div className="canvas-area" style={{ height: '100%', minHeight: '600px', display: 'flex', flexDirection: 'column' }}>
        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 16, color: 'var(--text)' }}>
            <div className="spinner" style={{ width: 32, height: 32, borderWidth: 3, borderTopColor: 'var(--accent2)' }} />
            <span style={{ fontSize: 18 }}>Building workflow…</span>
          </div>
        ) : (
          <div style={{ flex: 1, width: '100%', height: '100%' }}>
            <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.3 }}
            minZoom={0.2}
            style={{ background: 'transparent' }}
          >
            <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="rgba(255,255,255,0.05)" />
            <Controls style={{ background: 'rgba(13,13,20,0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10 }} />
            <MiniMap
              style={{ background: 'rgba(13,13,20,0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10 }}
              nodeColor="#7c3aed"
              maskColor="rgba(0,0,0,0.5)"
            />
          </ReactFlow>
          </div>
        )}
      </div>

      {/* Execution Result Modal */}
      {execResult && (
        <div className="exec-result-modal" onClick={() => setExecResult(null)}>
          <div className="exec-modal-box" onClick={e => e.stopPropagation()}>
            <div className="exec-modal-title">
              {execResult.error ? '❌ Execution Failed' : '✅ Execution Complete'}
              <button className="exec-modal-close" onClick={() => setExecResult(null)}>×</button>
            </div>
            <div className="exec-modal-output">
              {execResult.error
                ? execResult.error
                : JSON.stringify(execResult, null, 2)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
