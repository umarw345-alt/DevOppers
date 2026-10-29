import type { StoredTokens } from './AuthStorage';

declare const process: { env: { EXPO_PUBLIC_API_BASE_URL?: string } };

const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://10.0.2.2:8080';

export type AuthUser = { id: string; email: string };

export type AuthResponse = {
  access_token: string;
  refresh_token: string;
  user: AuthUser;
};

type RefreshResponse = {
  access_token: string;
  refresh_token: string;
};

export type AuthClientErrorKind = 'authentication' | 'network' | 'server';

export class AuthClientError extends Error {
  constructor(
    message: string,
    public readonly kind: AuthClientErrorKind,
    public readonly status?: number,
  ) {
    super(message);
    this.name = 'AuthClientError';
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...(init.headers ?? {}),
      },
    });
  } catch {
    throw new AuthClientError('Unable to reach the authentication service.', 'network');
  }

  if (!response.ok) {
    let detail = 'The authentication request could not be completed.';
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') detail = body.detail;
    } catch {
      // Keep the safe fallback message when the gateway returns no JSON body.
    }

    const kind: AuthClientErrorKind = response.status === 401 || response.status === 409 || response.status === 429
      ? 'authentication'
      : 'server';
    throw new AuthClientError(detail, kind, response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function register(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>('/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function login(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>('/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function refresh(refreshToken: string): Promise<StoredTokens> {
  return request<RefreshResponse>('/v1/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  }).then((response) => ({
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
  }));
}

export function logout(accessToken: string): Promise<void> {
  return request<void>('/v1/auth/logout', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export function recordInput(accessToken: string): Promise<void> {
  return request<void>('/v1/auth/input', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
