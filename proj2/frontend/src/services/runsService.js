const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5050';

function getAuth() {
  try { return JSON.parse(localStorage.getItem('auth')); } catch { return null; }
}

async function fetchWithAuth(path, options = {}) {
  const auth = getAuth();
  if (!auth?.token) throw new Error('Not authenticated');
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Authorization': `Bearer ${auth.token}`,
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    let detail = 'Request failed';
    try {
      const data = await res.json();
      const d = data?.detail ?? data?.error ?? detail;
      detail = typeof d === 'string' ? d : JSON.stringify(d);
    } catch {}
    throw new Error(`${detail} (${res.status})`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export async function createRun({ restaurant, drop_point, eta, capacity = 5 }) {
  return fetchWithAuth('/runs', {
    method: 'POST',
    body: JSON.stringify({ restaurant, drop_point, eta, capacity })
  });
}

export async function listAvailableRuns() {
  return fetchWithAuth('/runs/available');
}

export async function listMyRuns() {
  return fetchWithAuth('/runs/mine');
}

export async function getRunById(runId) {
  return fetchWithAuth(`/runs/id/${runId}`, { method: 'GET' });
}

export async function listAllRuns() {
  return fetchWithAuth('/runs');
}

export async function joinRun(runId, { items, amount }) {
  return fetchWithAuth(`/runs/${runId}/orders`, {
    method: 'POST',
    body: JSON.stringify({ items, amount })
  });
}

export async function unjoinRun(runId) {
  return fetchWithAuth(`/runs/${runId}/orders/me`, { method: 'DELETE' });
}

export async function completeRun(runId) {
  return fetchWithAuth(`/runs/${runId}/complete`, { method: 'PUT' });
}

export async function cancelRun(runId) {
  return fetchWithAuth(`/runs/${runId}/cancel`, { method: 'PUT' });
}

export async function listJoinedRuns() {
  return fetchWithAuth('/runs/joined');
}

export async function listMyRunsHistory() {
  return fetchWithAuth('/runs/mine/history');
}

export async function listJoinedRunsHistory() {
  return fetchWithAuth('/runs/joined/history');
}

export async function removeOrder(runId, orderId) {
  return fetchWithAuth(`/runs/${runId}/orders/${orderId}`, { method: 'DELETE' });
}

export async function verifyOrderPin(runId, orderId, pin) {
  return fetchWithAuth(`/runs/${runId}/orders/${orderId}/verify-pin`, {
    method: 'POST',
    body: JSON.stringify({ pin })
  });
}
