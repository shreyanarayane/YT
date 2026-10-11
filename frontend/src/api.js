export const API_BASE_URL = __API_BASE_URL__.replace(/\/+$/, '');

export async function api(path, { token, method = 'GET', body } = {}) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  const maxAttempts = method === 'GET' ? 3 : 1;
  let lastError;
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      response = await fetch(`${API_BASE_URL}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      break;
    } catch (error) {
      lastError = error;
      if (attempt + 1 < maxAttempts) {
        await new Promise(resolve => window.setTimeout(resolve, 800 * (attempt + 1)));
      }
    }
  }
  if (!response) {
    const retryHint = method === 'GET' ? 'The service may be waking from idle; check its /health endpoint and try again.' : 'Check that the backend is running and the URL is correct.';
    throw new Error(`Can't reach the API at ${API_BASE_URL}. ${retryHint}${lastError ? ` (${lastError.message})` : ''}`);
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
