/** API fetch wrapper with cookie support and promise-based refresh lock.
 *
 * Uses relative paths (/api/v1/...) in development.
 * Vite dev server proxies /api to localhost:8000.
 * Production uses VITE_API_BASE for the full backend URL.
 */

const API_BASE = import.meta.env.VITE_API_BASE || '';

// Promise-based refresh lock to prevent concurrent refresh requests (MAJ-5 fix)
let refreshPromise: Promise<void> | null = null;

async function refreshAccessToken(): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    // Refresh failed — redirect to login
    window.location.href = '/login';
    throw new Error('Refresh token expired');
  }
}

export async function apiFetch<T = unknown>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  const fullUrl = url.startsWith('/') ? `${API_BASE}${url}` : url;

  const response = await fetch(fullUrl, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  // If 401, try to refresh the access token
  if (response.status === 401) {
    // Use promise-based refresh lock to prevent concurrent refreshes
    if (!refreshPromise) {
      refreshPromise = refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
    }

    try {
      await refreshPromise;
      // Retry the original request after successful refresh
      const retryResponse = await fetch(fullUrl, {
        ...options,
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      if (!retryResponse.ok) {
        throw new Error(`API error: ${retryResponse.status} ${retryResponse.statusText}`);
      }

      return retryResponse.json();
    } catch {
      // Refresh failed — redirect to login
      window.location.href = '/login';
      throw new Error('Session expired');
    }
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || `API error: ${response.status}`);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}