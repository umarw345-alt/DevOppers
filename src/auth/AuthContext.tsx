import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { AppState, Platform } from 'react-native';

import {
  AuthClientError,
  AuthUser,
  login as loginRequest,
  logout as logoutRequest,
  recordInput as recordInputRequest,
  refresh,
  register as registerRequest,
} from './AuthClients';
import { clearTokens, getTokens, saveTokens } from './AuthStorage';

export type AuthStatus = 'loading' | 'signed_out' | 'signed_in';

type AuthContextValue = {
  status: AuthStatus;
  user: AuthUser | null;
  accessToken: string | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  refreshSession: () => Promise<void>;
  logout: () => Promise<void>;
  recordInput: () => Promise<void>;
  clearError: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const REFRESH_EVERY_MS = 10 * 60 * 1000;

function getErrorMessage(reason: unknown): string {
  if (reason instanceof AuthClientError) return reason.message;
  return 'Something went wrong. Please try again.';
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const signedIn = useRef(false);
  signedIn.current = status === 'signed_in';

  const refreshSession = useCallback(async () => {
    const isWeb = Platform.OS === 'web';

    try {
      const tokens = isWeb ? null : await getTokens();

      if (!isWeb && !tokens) {
        setStatus('signed_out');
        return;
      }

      const nextSession = await refresh(tokens?.refreshToken);
      if (isWeb) {
        setAccessToken(null);
        setUser(nextSession.user ?? null);
      } else if (nextSession.tokens) {
        await saveTokens(nextSession.tokens);
        setAccessToken(nextSession.tokens.accessToken);
        setUser((current) => current ?? { id: '', email: 'Returning user' });
      } else {
        throw new Error('Refresh response did not contain tokens.');
      }

      setStatus('signed_in');
      setError(null);
    } catch (reason) {
      // A dropped connection shouldn't sign out someone who is already in; the next renewal tries again.
      if (signedIn.current && reason instanceof AuthClientError && reason.kind === 'network') return;
      if (isWeb) {
        setUser(null);
        setError(reason instanceof AuthClientError && reason.status === 401 ? null : getErrorMessage(reason));
      } else {
        await clearTokens();
        setError(getErrorMessage(reason));
      }
      setAccessToken(null);
      setStatus('signed_out');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshSession().catch(() => undefined);
  }, [refreshSession]);

  // Access tokens last ACCESS_TOKEN_TTL_MINUTES (15 by default), so renew them before they run out,
  // and again when the app comes back to the foreground (timers pause in the background).
  // The server still ends the session after AFK_TIMEOUT_MINUTES without input.
  useEffect(() => {
    if (status !== 'signed_in') return;
    const timer = setInterval(() => refreshSession().catch(() => undefined), REFRESH_EVERY_MS);
    const subscription = AppState.addEventListener('change', (state) => {
      if (state === 'active') refreshSession().catch(() => undefined);
    });
    return () => {
      clearInterval(timer);
      subscription.remove();
    };
  }, [status, refreshSession]);

  const authenticate = useCallback(async (request: () => ReturnType<typeof loginRequest>) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await request();
      if (Platform.OS !== 'web') {
        if (!response.access_token || !response.refresh_token) {
          throw new Error('Authentication response did not contain tokens.');
        }
        await saveTokens({ accessToken: response.access_token, refreshToken: response.refresh_token });
        setAccessToken(response.access_token);
      } else {
        setAccessToken(null);
      }
      setUser(response.user);
      setStatus('signed_in');
    } catch (reason) {
      setStatus('signed_out');
      setError(getErrorMessage(reason));
      throw reason;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = useCallback(
    (email: string, password: string) => authenticate(() => loginRequest(email, password)),
    [authenticate],
  );

  const register = useCallback(
    (email: string, password: string) => authenticate(() => registerRequest(email, password)),
    [authenticate],
  );

  const logout = useCallback(async () => {
    setIsLoading(true);
    try {
      await logoutRequest(accessToken ?? undefined);
    } catch {
      // Local token cleanup remains mandatory if the server is unavailable.
    } finally {
      if (Platform.OS !== 'web') await clearTokens();
      setAccessToken(null);
      setUser(null);
      setError(null);
      setStatus('signed_out');
      setIsLoading(false);
    }
  }, [accessToken]);

  const recordInput = useCallback(async () => {
    if (Platform.OS !== 'web' && !accessToken) return;

    try {
      await recordInputRequest(accessToken ?? undefined);
    } catch {
      // The access token may just have run out; renewing signs the user out only if the session really ended.
      await refreshSession();
    }
  }, [accessToken, refreshSession]);

  return (
    <AuthContext.Provider
      value={{
        status,
        user,
        accessToken,
        isLoading,
        error,
        login,
        register,
        refreshSession,
        logout,
        recordInput,
        clearError: () => setError(null),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}
