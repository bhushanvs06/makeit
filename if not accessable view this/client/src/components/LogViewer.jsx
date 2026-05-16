import React, { useEffect, useRef } from 'react';

export default function LogViewer({ logs }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="log-viewer">
      <h3>🔄 Agent Activity</h3>
      {logs.length === 0 ? (
        <p style={{ color: '#94a3b8' }}>No logs yet. Enter a goal to see the agents in action.</p>
      ) : (
        logs.map((entry, i) => (
          <div className="log-entry" key={i}>
            <span className="log-agent">{entry.agent}</span>
            <span>{entry.message}</span>
          </div>
        ))
      )}
      <div ref={bottomRef} />
    </div>
  );
}