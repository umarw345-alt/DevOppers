import { getApiBaseUrl } from './ApiBaseUrl';

/** The browser starts the server-side OIDC flow; Google tokens stay server-side. */
export function getGoogleSignInUrl(): string {
  return `${getApiBaseUrl()}/v1/auth/google/start`;
}

export function startGoogleSignIn(navigate: (url: string) => void = (url) => {
  const browser = globalThis as typeof globalThis & { location?: { assign: (target: string) => void } };
  if (!browser.location) throw new Error('Browser navigation is unavailable.');
  browser.location.assign(url);
}): void {
  navigate(getGoogleSignInUrl());
}
