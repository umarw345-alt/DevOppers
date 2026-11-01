import type { StoredTokens } from './AuthStorage';
import { Platform } from 'react-native';

declare const process: { env: { EXPO_PUBLIC_API_BASE_URL?: string } };

const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://10.0.2.2:8080';

export type AuthUser = { id: string; email: string };

export type AuthResponse = {
  access_token?: string;
  refresh_token?: string;
  user: AuthUser;
};

type RefreshResponse = {
  access_token: string;
  refresh_token: string;
};

type WebAuthResponse = { user: AuthUser };

export type RefreshResult = {
  tokens?: StoredTokens;
  user?: AuthUser;
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

function getWebCsrfToken(): string | undefined {
  const browser = (globalThis as typeof globalThis & { document?: { cookie: string } }).document;
  const cookie = browser?.cookie.split('; ').find((entry) => entry.startsWith('auth_csrf_token='));
  return cookie ? decodeURIComponent(cookie.slice('auth_csrf_token='.length)) : undefined;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const isWeb = Platform.OS === 'web';
  const csrfToken = isWeb ? getWebCsrfToken() : undefined;
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      credentials: isWeb ? 'include' : 'omit',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-Client-Platform': isWeb ? 'web' : 'native',
        ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
        ...(init.headers ?? {}),
      },
    });
  } catch {
    throw new AuthClientError('Unable to reach the authentication service.', 'network');
  }

  if (!response.ok) {
    let detail = 'The authentication request could not be completed.';
    if (response.status === 401) {
      detail = 'Username or password is incorrect. Please try again.';
    }
    else if (response.status === 429) {
      detail = 'Too many requests. Please try again.';
    }

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

export function refresh(refreshToken?: string): Promise<RefreshResult> {
  const isWeb = Platform.OS === 'web';
  return request<RefreshResponse | WebAuthResponse>('/v1/auth/refresh', {
    method: 'POST',
    ...(isWeb ? {} : { body: JSON.stringify({ refresh_token: refreshToken }) }),
  }).then((response) => {
    if ('access_token' in response && response.access_token && response.refresh_token) {
      return { tokens: { accessToken: response.access_token, refreshToken: response.refresh_token } };
    }
    return { user: (response as WebAuthResponse).user };
  });
}

export function logout(accessToken?: string): Promise<void> {
  const isWeb = Platform.OS === 'web';
  return request<void>('/v1/auth/logout', {
    method: 'POST',
    ...(isWeb || !accessToken ? {} : { headers: { Authorization: `Bearer ${accessToken}` } }),
  });
}

export function recordInput(accessToken?: string): Promise<void> {
  const isWeb = Platform.OS === 'web';
  return request<void>('/v1/auth/input', {
    method: 'POST',
    ...(isWeb || !accessToken ? {} : { headers: { Authorization: `Bearer ${accessToken}` } }),
  });
}
