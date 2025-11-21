const AUTH_KEY = 'auth';
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5050';

async function fetchWithAuth(path, options = {}) {
    const auth = getSavedAuth();
    if (!auth?.token) throw new Error('Not authenticated');
    
    const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
            ...options.headers,
            'Authorization': `Bearer ${auth.token}`,
            'Content-Type': 'application/json',
        },
    });
    if (!res.ok) {
        let detail = 'Request failed';
        try { const data = await res.json(); detail = data.detail || data.error || detail; } catch {}
        throw new Error(detail + ` (${res.status})`);
    }
    return res.json();
}

async function postJson(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!res.ok) {
        let message = 'Request failed';
        try {
            const data = await res.json();
            let detail = data?.detail ?? data?.error ?? data?.message;
            if (Array.isArray(detail)) {
                // FastAPI 422 validation errors: join messages
                const msgs = detail.map((d) => d?.msg || (typeof d === 'string' ? d : JSON.stringify(d)));
                message = msgs.join('; ');
            } else if (typeof detail === 'string') {
                message = detail;
            } else if (detail) {
                message = JSON.stringify(detail);
            }
        } catch {}
        throw new Error(`${message} (${res.status})`);
    }
    return res.json();
}

export async function register({ username, password }) {
    // backend expects { email, password }
    const data = await postJson('/auth/register', { email: username, password });
    localStorage.setItem(AUTH_KEY, JSON.stringify(data));
    return data; // { user, token }
}

export async function login({ username, password }) {
    const data = await postJson('/auth/login', { email: username, password });
    localStorage.setItem(AUTH_KEY, JSON.stringify(data));
    return data;
}

export function logout() {
    localStorage.removeItem(AUTH_KEY);
}

export function getSavedAuth() {
    try { return JSON.parse(localStorage.getItem(AUTH_KEY)); } catch { return null; }
}

export async function getPoints() {
    return fetchWithAuth('/points');
}

export async function redeemPoints() {
    return fetchWithAuth('/points/redeem', { method: 'POST' });
}