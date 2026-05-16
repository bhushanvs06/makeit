import React, { useState, useRef, useCallback } from 'react';
import './index.css';
import './App.css';
import HeroScreen from './components/HeroScreen.jsx';
import AgentTheater from './components/AgentTheater.jsx';
import WorkflowCanvas from './components/WorkflowCanvas.jsx';
import LibraryScreen from './components/LibraryScreen.jsx';
import NavBar from './components/NavBar.jsx';
import { generateWorkflow, connectLogsWebSocket, getSettings, updateSettings } from './api/api.js';

// Phases: 'hero' | 'theater' | 'canvas' | 'library'
export default function App() {
  const [phase, setPhase] = useState('hero');
  const [goal, setGoal] = useState('');
  const [logs, setLogs] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [waEnabled, setWaEnabled] = useState(false);
  const wsRef = useRef(null);

  React.useEffect(() => {
    getSettings().then(d => setWaEnabled(d.whatsapp_listener_enabled)).catch(() => {});
  }, []);

  const handleGoalSubmit = useCallback(async (submittedGoal) => {
    setGoal(submittedGoal);
    setLogs([]);
    setResult(null);
    setLoading(true);
    setPhase('theater');

    if (wsRef.current) wsRef.current.close();
    const socket = connectLogsWebSocket(
      (data) => setLogs(prev => [...prev, data]),
      null, null, null
    );
    wsRef.current = socket;

    try {
      const wfResult = await generateWorkflow(submittedGoal);
      setResult(wfResult);
      setPhase('canvas');
    } catch (err) {
      setLogs(prev => [...prev, { agent: 'Error', message: err.message }]);
      setPhase('canvas');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleToggleWa = async () => {
    const val = !waEnabled;
    setWaEnabled(val);
    await updateSettings({ whatsapp_listener_enabled: val });
  };

  return (
    <>
      <NavBar
        phase={phase}
        onGoHome={() => setPhase('hero')}
        onGoLibrary={() => setPhase('library')}
        onGoCanvas={() => result && setPhase('canvas')}
        waEnabled={waEnabled}
        onToggleWa={handleToggleWa}
        hasResult={!!result}
      />

      {phase === 'hero' && (
        <div className="phase">
          <HeroScreen onSubmit={handleGoalSubmit} loading={loading} />
        </div>
      )}
      {phase === 'theater' && (
        <div className="phase">
          <AgentTheater logs={logs} goal={goal} loading={loading} />
        </div>
      )}
      {phase === 'canvas' && (
        <div className="phase" style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
          <WorkflowCanvas
            data={result}
            goal={goal}
            loading={loading}
            logs={logs}
            onGoLibrary={() => setPhase('library')}
          />
        </div>
      )}
      {phase === 'library' && (
        <div className="phase" style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
          <LibraryScreen 
            onGoHome={() => setPhase('hero')}
            onViewWorkflow={(wf) => {
              setResult({
                workflow: wf.workflow_graph,
                required_credentials: wf.required_credentials || [],
              });
              setGoal(wf.goal || 'Unnamed Workflow');
              setPhase('canvas');
            }}
          />
        </div>
      )}
    </>
  );
}