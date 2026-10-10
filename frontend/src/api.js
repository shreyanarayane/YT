export const API_BASE_URL = __API_BASE_URL__.replace(/\/+$/, '');

export async function api(path, { token, method = 'GET', body } = {}) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new Error(`Can't reach the API at ${API_BASE_URL}. Check that the backend is running and the URL is correct.`);
  }

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || `Request failed (${response.status})`);
  }
  return payload;
}

export function mediaUrl(path) {
  if (!path) return '';
  return path.startsWith('http') ? path : `${API_BASE_URL}${path}`;
}
