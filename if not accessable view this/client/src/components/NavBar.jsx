import React from 'react';

export default function NavBar({ phase, onGoHome, onGoLibrary, onGoCanvas, waEnabled, onToggleWa, hasResult }) {
  return (
    <nav className="nav-bar">
      <button className="nav-logo" style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontFamily: 'var(--font2)', fontWeight: 700, fontSize: 22 }} onClick={onGoHome}>
        MakeIt ⚡
      </button>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        <button className={`nav-btn ${phase === 'hero' ? 'active' : ''}`} onClick={onGoHome}>
          🏠 Home
        </button>
        {hasResult && (
          <button className={`nav-btn ${phase === 'canvas' ? 'active' : ''}`} onClick={onGoCanvas}>
            ⚡ Canvas
          </button>
        )}
        <button className={`nav-btn ${phase === 'library' ? 'active' : ''}`} onClick={onGoLibrary}>
          📚 Library
        </button>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
          <div
            onClick={onToggleWa}
            style={{
              width: 40, height: 22,
              background: waEnabled ? 'rgba(124,58,237,0.8)' : 'rgba(255,255,255,0.1)',
              borderRadius: 11, position: 'relative', cursor: 'pointer',
              transition: 'background 0.3s',
              border: '1px solid rgba(255,255,255,0.15)',
            }}
          >
            <div style={{
              position: 'absolute', top: 2, left: waEnabled ? 20 : 2,
              width: 16, height: 16, borderRadius: 8,
              background: '#fff', transition: 'left 0.3s',
              boxShadow: '0 1px 4px rgba(0,0,0,0.3)',
            }} />
          </div>
          <span style={{ fontSize: 12, color: 'var(--text)', whiteSpace: 'nowrap' }}>
            {waEnabled ? '📱 WA On' : '📱 WA Off'}
          </span>
        </label>
      </div>
    </nav>
  );
}
