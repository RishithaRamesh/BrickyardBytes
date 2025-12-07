const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5050';

function getAuth() {
  try {
    return JSON.parse(localStorage.getItem('auth'));
  } catch {
    return null;
  }
}

async function fetchWithAuth(path, options = {}) {
  const auth = getAuth();
  if (!auth?.token) throw new Error('Not authenticated');
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${auth.token}`,
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
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

export async function getPeakForecast() {
  return fetchWithAuth('/analytics/peak-forecast');
}
