/** Auth service: API calls for authentication endpoints. */

import { apiFetch } from '../utils/api';
import type { AuthResponse, LoginRequest, RegisterRequest, User } from '../types/auth';

export async function login(data: LoginRequest): Promise<AuthResponse> {
  return apiFetch<AuthResponse>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function register(data: RegisterRequest): Promise<AuthResponse> {
  return apiFetch<AuthResponse>('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function logout(): Promise<void> {
  await apiFetch<void>('/api/v1/auth/logout', {
    method: 'POST',
  });
}

export async function getMe(): Promise<User> {
  return apiFetch<User>('/api/v1/auth/me');
}

export function initiateGoogleLogin(): void {
  // Redirect to backend's Google OAuth endpoint
  // The backend will redirect to Google, then back to the frontend callback
  const apiBase = import.meta.env.VITE_API_BASE || '';
  window.location.href = `${apiBase}/api/v1/auth/google`;
}