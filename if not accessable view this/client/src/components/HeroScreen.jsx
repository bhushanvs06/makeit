import React, { useState } from 'react';

const EXAMPLES = [
  'Send daily news digest to WhatsApp',
  'Schedule a Google Meet and email attendees',
  'Scrape top AI articles → Google Sheet',
  'Monitor Gmail and auto-reply with GPT',
];

export default function HeroScreen({ onSubmit, loading }) {
  const [value, setValue] = useState('');

  const submit = () => {
    if (value.trim() && !loading) onSubmit(value.trim());
  };

  return (
    <div className="hero-screen">
      <div className="hero-bg-grid" />
      <div className="hero-orb hero-orb-1" />
      <div className="hero-orb hero-orb-2" />
      <div className="hero-orb hero-orb-3" />

      <div className="hero-content">
        <div className="hero-badge">
          <span className="hero-badge-dot" />
          AI Workflow Architect
        </div>

        <h1 className="hero-title">
          Describe it.<br />
          <span className="grad">We build it.</span>
        </h1>

        <p className="hero-sub">
          Type your goal in plain English — our architect team of AI agents will design,
          validate, and wire your workflow automatically.
        </p>

        <div className="goal-input-wrap">
          <div className="goal-input-glass">
            <span style={{ fontSize: 20, flexShrink: 0 }}>✦</span>
            <input
              id="goal-input"
              type="text"
              placeholder="e.g. Send me a daily summary of top AI news on WhatsApp…"
              value={value}
              onChange={e => setValue(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && submit()}
              autoFocus
            />
            <button className="goal-submit-btn" onClick={submit} disabled={loading || !value.trim()}>
              {loading
                ? <><div className="spinner" /> Building…</>
                : <>Build Workflow →</>
              }
            </button>
          </div>

          <div className="hero-examples">
            {EXAMPLES.map((ex) => (
              <button key={ex} className="example-chip" onClick={() => setValue(ex)}>
                {ex}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Floating stats */}
      <div style={{
        position: 'absolute', bottom: 40,
        display: 'flex', gap: 40,
        animation: 'fadeUp 0.8s 0.6s ease both',
        opacity: 0,
        animationFillMode: 'forwards',
      }}>
        {[['⚡', 'Instant', 'Generation'], ['🔗', 'N8N-Style', 'Visual DAG'], ['🤖', 'Multi-Agent', 'Architecture']].map(([icon, l1, l2]) => (
          <div key={l1} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 28, marginBottom: 4 }}>{icon}</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-h)' }}>{l1}</div>
            <div style={{ fontSize: 12, color: 'var(--text)' }}>{l2}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
