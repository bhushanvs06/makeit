import React, { useEffect, useRef, useState } from 'react';

const AGENTS = [
  {
    key: 'Analyst',
    label: 'Analyst',
    role: 'Goal Decomposition',
    icon: '🧠',
    colorA: '#a855f7',
    colorB: '#7c3aed',
    glow: 'rgba(168,85,247,0.4)',
    iconBg: 'rgba(168,85,247,0.15)',
    keywords: ['analys', 'goal', 'task', 'decom', 'understand'],
  },
  {
    key: 'Researcher',
    label: 'Researcher',
    role: 'Component Discovery',
    icon: '🔍',
    colorA: '#06b6d4',
    colorB: '#0891b2',
    glow: 'rgba(6,182,212,0.4)',
    iconBg: 'rgba(6,182,212,0.15)',
    keywords: ['research', 'component', 'discover', 'find', 'select'],
  },
  {
    key: 'Architect',
    label: 'Architect',
    role: 'Workflow Design',
    icon: '⚙️',
    colorA: '#f59e0b',
    colorB: '#d97706',
    glow: 'rgba(245,158,11,0.4)',
    iconBg: 'rgba(245,158,11,0.15)',
    keywords: ['architect', 'design', 'build', 'workflow', 'node', 'edge', 'graph', 'wire'],
  },
  {
    key: 'Validator',
    label: 'Validator',
    role: 'Quality Assurance',
    icon: '✅',
    colorA: '#10b981',
    colorB: '#059669',
    glow: 'rgba(16,185,129,0.4)',
    iconBg: 'rgba(16,185,129,0.15)',
    keywords: ['valid', 'check', 'verif', 'complete', 'done', 'finish'],
  },
];

function matchAgent(log) {
  const text = `${log.agent} ${log.message}`.toLowerCase();
  for (const a of AGENTS) {
    if (text.includes(a.key.toLowerCase())) return a.key;
    if (a.keywords.some(k => text.includes(k))) return a.key;
  }
  return null;
}

const TAG_COLORS = {
  Analyst:    { bg: 'rgba(168,85,247,0.15)', color: '#c084fc' },
  Researcher: { bg: 'rgba(6,182,212,0.15)',  color: '#67e8f9' },
  Architect:  { bg: 'rgba(245,158,11,0.15)', color: '#fcd34d' },
  Validator:  { bg: 'rgba(16,185,129,0.15)', color: '#6ee7b7' },
  Error:      { bg: 'rgba(239,68,68,0.15)',  color: '#fca5a5' },
  System:     { bg: 'rgba(100,116,139,0.15)',color: '#94a3b8' },
};

export default function AgentTheater({ logs, goal, loading }) {
  const [agentState, setAgentState] = useState({
    Analyst: { status: 'idle', progress: 0, lastMsg: '' },
    Researcher: { status: 'idle', progress: 0, lastMsg: '' },
    Architect: { status: 'idle', progress: 0, lastMsg: '' },
    Validator: { status: 'idle', progress: 0, lastMsg: '' },
  });
  const logEndRef = useRef(null);

  useEffect(() => {
    if (logs.length === 0) return;
    const last = logs[logs.length - 1];
    const matched = matchAgent(last);

    setAgentState(prev => {
      const next = { ...prev };

      // Reset any old 'active' to 'waiting' if a new one takes over
      if (matched) {
        for (const k of Object.keys(next)) {
          if (k !== matched && next[k].status === 'active') {
            next[k] = { ...next[k], status: 'done', progress: 100 };
          }
        }
        const cur = next[matched];
        next[matched] = {
          status: 'active',
          progress: Math.min((cur.progress || 0) + 20, 90),
          lastMsg: last.message.slice(0, 60),
        };
      }

      // If loading just ended, mark everything done
      if (!loading) {
        for (const k of Object.keys(next)) {
          if (next[k].status === 'active') {
            next[k] = { ...next[k], status: 'done', progress: 100 };
          }
        }
      }

      return next;
    });
  }, [logs, loading]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Auto-advance agents to give visual feedback even before logs come in
  useEffect(() => {
    if (!loading) return;
    const order = ['Analyst', 'Researcher', 'Architect', 'Validator'];
    let idx = 0;
    const interval = setInterval(() => {
      setAgentState(prev => {
        const next = { ...prev };
        if (idx > 0) {
          next[order[idx - 1]] = { ...next[order[idx - 1]], status: 'done', progress: 100 };
        }
        if (idx < order.length) {
          next[order[idx]] = { ...next[order[idx]], status: 'active', progress: Math.random() * 40 + 20 };
        }
        return next;
      });
      idx++;
      if (idx >= order.length) clearInterval(interval);
    }, 2500);
    return () => clearInterval(interval);
  }, [loading]);

  return (
    <div className="agent-theater">
      <h2 className="theater-title">
        {loading ? '🔮 Architect Team Assembling…' : '✅ Workflow Generated'}
      </h2>
      <p className="theater-sub">
        {loading
          ? `Building workflow for: "${goal}"`
          : 'All agents completed. Switching to canvas…'}
      </p>

      <div className="agents-grid">
        {AGENTS.map((agent, i) => {
          const state = agentState[agent.key];
          const isActive = state.status === 'active';
          const isDone = state.status === 'done';
          return (
            <div
              key={agent.key}
              className={`agent-card ${isActive ? 'active' : ''} ${isDone ? 'done' : ''}`}
              style={{
                '--card-color-a': agent.colorA,
                '--card-color-b': agent.colorB,
                '--card-glow': agent.glow,
                '--card-icon-bg': agent.iconBg,
                animationDelay: `${i * 0.12}s`,
              }}
            >
              <div className="agent-check">✓</div>
              <div className="agent-icon">
                <span>{agent.icon}</span>
                <div className="agent-icon-ring" />
              </div>
              <div className="agent-name">{agent.label}</div>
              <div className="agent-role">{agent.role}</div>
              <div className="agent-status-text">
                {isDone ? '✓ Complete'
                  : isActive ? (state.lastMsg || 'Processing…')
                  : 'Waiting…'}
              </div>
              <div className="agent-status-bar">
                <div
                  className="agent-status-fill"
                  style={{ width: `${state.progress}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Live log stream */}
      <div className="log-stream">
        {logs.length === 0 ? (
          <div style={{ color: 'var(--text)', fontSize: 13, textAlign: 'center', padding: '20px 0' }}>
            Waiting for agent signals…
          </div>
        ) : (
          logs.slice(-40).map((log, i) => {
            const tc = TAG_COLORS[log.agent] || TAG_COLORS.System;
            return (
              <div className="log-line" key={i}>
                <span className="log-agent-tag" style={{ background: tc.bg, color: tc.color }}>
                  {log.agent}
                </span>
                <span className="log-msg">{log.message}</span>
              </div>
            );
          })
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
}
