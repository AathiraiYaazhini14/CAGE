/**
 * CAGE Security Operations API Client
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

let onUnauthorizedCallback = null;

export function setUnauthorizedHandler(callback) {
  onUnauthorizedCallback = callback;
}

export function getAuthToken() {
  return localStorage.getItem('cage_jwt_token') || '';
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem('cage_jwt_token', token);
  } else {
    localStorage.removeItem('cage_jwt_token');
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getAuthToken();

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const config = {
    ...options,
    headers,
  };

  try {
    const res = await fetch(url, config);

    if (res.status === 401) {
      setAuthToken(null);
      if (onUnauthorizedCallback) {
        onUnauthorizedCallback();
      }
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'Authentication required');
    }

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Request failed with status ${res.status}`);
    }

    // Check if CSV or raw
    if (headers['Accept'] === 'text/csv' || endpoint.endsWith('.csv')) {
      return res.text();
    }

    return await res.json();
  } catch (err) {
    throw err;
  }
}

export const api = {
  // Auth
  auth: {
    signup: (name, email, password) =>
      request('/auth/signup', {
        method: 'POST',
        body: JSON.stringify({ name, email, password }),
      }),
    login: (email, password) =>
      request('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    me: () => request('/auth/me'),
  },

  // Stats
  stats: {
    get: (range = '30d') => request(`/stats?range=${encodeURIComponent(range)}`),
  },

  // Logs
  logs: {
    list: ({ limit = 50, offset = 0, range, verdict, category, source_type, q } = {}) => {
      const params = new URLSearchParams({
        limit: String(limit),
        offset: String(offset),
        paged: 'true',
      });
      if (range) params.append('range', range);
      if (verdict && verdict !== 'all') params.append('verdict', verdict);
      if (category && category !== 'all') params.append('category', category);
      if (source_type && source_type !== 'all') params.append('source_type', source_type);
      if (q && q.trim()) params.append('q', q.trim());

      return request(`/logs?${params.toString()}`);
    },
    get: (id) => request(`/logs/${id}`),
    getExportUrl: ({ range, verdict, category, source_type, q } = {}) => {
      const params = new URLSearchParams();
      if (range) params.append('range', range);
      if (verdict && verdict !== 'all') params.append('verdict', verdict);
      if (category && category !== 'all') params.append('category', category);
      if (source_type && source_type !== 'all') params.append('source_type', source_type);
      if (q && q.trim()) params.append('q', q.trim());

      return `${API_BASE_URL}/logs/export.csv?${params.toString()}`;
    },
    exportCsv: async (params) => {
      const token = getAuthToken();
      const exportUrl = api.logs.getExportUrl(params);
      const res = await fetch(exportUrl, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (!res.ok) throw new Error('Failed to export CSV');
      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = `cage_threat_logs_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(blobUrl);
    },
  },

  // Demo RAG Chat
  demo: {
    chat: (message, protection = true) =>
      request('/demo/chat', {
        method: 'POST',
        body: JSON.stringify({
          message,
          protection,
        }),
      }),
  },

  // Quick Inspection Scan
  scan: {
    inspect: (text, source_type = 'user_input') =>
      request('/scan', {
        method: 'POST',
        body: JSON.stringify({ text, source_type }),
      }),
  },

  // API Keys (Isolated strictly per user account)
  keys: {
    list: () => request('/api-keys'),
    create: ({ name, environment, scope }) =>
      request('/api-keys', {
        method: 'POST',
        body: JSON.stringify({ name, environment, scope }),
      }),
    revoke: (id) =>
      request(`/api-keys/${encodeURIComponent(id)}`, {
        method: 'DELETE',
      }),
  },
};

