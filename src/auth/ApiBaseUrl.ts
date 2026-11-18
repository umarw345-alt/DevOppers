import { Platform } from 'react-native';

declare const process: { env: { EXPO_PUBLIC_API_BASE_URL?: string } };

export function getApiBaseUrl(): string {
  const configured = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
  if (configured) return configured.replace(/\/$/, '');

  if (Platform.OS === 'web') {
    const browser = globalThis as typeof globalThis & { location?: { origin?: string } };
    if (browser.location?.origin) return browser.location.origin;
    return 'http://localhost:8000';
  }

  return 'http://10.0.2.2:8000';
}
