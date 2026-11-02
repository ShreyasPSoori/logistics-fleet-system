const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
let token = localStorage.getItem('bea_token') || '';

export function setToken(value) {
  token = value;
  if (value) localStorage.setItem('bea_token', value);
  else localStorage.removeItem('bea_token');
}

export async function request(path, options = {}) {
  const headers = { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API}${path}`, { ...options, headers });
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.detail || `Request failed (${response.status})`);
  return data;
}

export async function login(email, password) {
  const form = new URLSearchParams({ username: email, password });
  const response = await fetch(`${API}/auth/token`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: form });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || 'Could not sign in');
  setToken(data.access_token);
  return data;
}
