import { getSavedAuth } from './authServices';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5050';

async function handleResponse(res) {
  if (!res.ok) {
    let message = 'Request failed';
    try {
      const data = await res.json();
      message = data?.detail || data?.error || data?.message || message;
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(`${message} (${res.status})`);
  }
  return res.json();
}

export async function getPeakForecast() {
  const auth = getSavedAuth();
  const headers = { 'Content-Type': 'application/json' };
  if (auth?.token) {
    headers['Authorization'] = `Bearer ${auth.token}`;
  }
  const res = await fetch(`${API_BASE}/analytics/peak-forecast`, {
    method: 'GET',
    headers,
  });
  return handleResponse(res);
}
