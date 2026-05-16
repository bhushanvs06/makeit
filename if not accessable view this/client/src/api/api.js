// Base URL for backend
const BASE_URL = 'http://localhost:8000';

export async function fetchComponents() {
  const response = await fetch(`${BASE_URL}/components`);
  return response.json();
}

export async function generateWorkflow(goal) {
  const response = await fetch(`${BASE_URL}/generate-workflow`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ goal }),
  });
  if (!response.ok) {
    throw new Error(`HTTP error ${response.status}`);
  }
  return response.json();
}

// WebSocket helper
export function connectLogsWebSocket(onMessage, onOpen, onError, onClose) {
  const socket = new WebSocket('ws://localhost:8000/ws/logs');

  socket.onopen = () => {
    if (onOpen) onOpen();
  };

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  };

  socket.onerror = (error) => {
    if (onError) onError(error);
  };

  socket.onclose = () => {
    if (onClose) onClose();
  };

  return socket;
}
export async function saveWorkflow(goal, workflowGraph, requiredCredentials) {
  const response = await fetch(`${BASE_URL}/workflows/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      goal,
      workflow_graph: workflowGraph,
      required_credentials: requiredCredentials
    }),
  });
  return response.json();
}
export async function fetchWorkflows() {
  const response = await fetch(`${BASE_URL}/workflows/`);
  return response.json();
}

export async function executeWorkflow(id) {
  const response = await fetch(`${BASE_URL}/workflows/${id}/execute`, {
    method: 'POST'
  });
  return response.json();
}

export async function fetchMissingCredentials(workflowId) {
  const response = await fetch(`${BASE_URL}/workflows/${workflowId}/required-credentials`);
  return response.json();
}

export async function fetchCredentialsInfo() {
  const response = await fetch(`${BASE_URL}/credentials-info`);
  return response.json();
}

export async function getSettings() {
  const response = await fetch(`${BASE_URL}/settings`);
  return response.json();
}

export async function updateSettings(settings) {
  const response = await fetch(`${BASE_URL}/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  return response.json();
}