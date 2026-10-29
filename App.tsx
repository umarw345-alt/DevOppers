/**
 * Sample React Native App
 * https://github.com/facebook/react-native
 *
 * @format
 */

import { useCallback, useEffect, useState } from 'react';
import { StatusBar } from 'react-native';
import { initialWindowMetrics, SafeAreaProvider } from 'react-native-safe-area-context';

import AuthScreen from './src/screens/AuthScreen';
import LoginScreen from './src/screens/LoginScreen';
import RegisterScreen from './src/screens/RegisterScreen';
import { AuthClientError, login, logout, recordInput, refresh, register } from './src/auth/AuthClients';
import { clearTokens, getTokens, saveTokens } from './src/auth/AuthStorage';

type Screen = 'login' | 'register' | 'authenticated';

function App() {
  const [screen, setScreen] = useState<Screen>('login');
  const [authenticatedEmail, setAuthenticatedEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const showAuthenticated = (email: string) => {
    setAuthenticatedEmail(email);
    setScreen('authenticated');
  };

  const displayError = (reason: unknown) => {
    if (reason instanceof AuthClientError) {
      setError(reason.message);
    } else {
      setError('Something went wrong. Please try again.');
    }
  };

  const authenticate = async (action: () => Promise<{ user: { email: string }; access_token: string; refresh_token: string }>) => {
    setIsLoading(true);
    setError('');
    try {
      const response = await action();
      await saveTokens({ accessToken: response.access_token, refreshToken: response.refresh_token });
      showAuthenticated(response.user.email);
    } catch (reason) {
      displayError(reason);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    const restoreSession = async () => {
      const tokens = await getTokens();
      if (!active || !tokens) return;
      setIsLoading(true);
      try {
        const nextTokens = await refresh(tokens.refreshToken);
        await saveTokens(nextTokens);
        if (active) {
          setAuthenticatedEmail('Returning user');
          setScreen('authenticated');
        }
      } catch {
        await clearTokens();
      } finally {
        if (active) setIsLoading(false);
      }
    };
    restoreSession().catch(() => undefined);
    return () => { active = false; };
  }, []);

  const handleInput = useCallback(async () => {
    const tokens = await getTokens();
    if (!tokens) return;
    try {
      await recordInput(tokens.accessToken);
    } catch {
      await clearTokens();
      setError('Your session has expired. Please sign in again.');
      setScreen('login');
    }
  }, []);

  const handleLogout = async () => {
    setIsLoading(true);
    const tokens = await getTokens();
    try {
      if (tokens) await logout(tokens.accessToken);
    } catch {
      // Local cleanup is still mandatory when the server cannot be reached.
    } finally {
      await clearTokens();
      setAuthenticatedEmail('');
      setError('');
      setScreen('login');
      setIsLoading(false);
    }
  };

  return (
    <SafeAreaProvider initialMetrics={initialWindowMetrics}>
      <StatusBar barStyle="light-content" />
      {screen === 'login' ? (
        <LoginScreen isLoading={isLoading} error={error} onLogin={(email, password) => authenticate(() => login(email, password))} onRegisterPress={() => { setError(''); setScreen('register'); }} />
      ) : screen === 'register' ? (
        <RegisterScreen isLoading={isLoading} error={error} onLoginPress={() => { setError(''); setScreen('login'); }} onRegister={(email, password) => authenticate(() => register(email, password))} />
      ) : (
        <AuthScreen email={authenticatedEmail} isLoading={isLoading} onInput={handleInput} onLogout={handleLogout} error={error} />
      )}
    </SafeAreaProvider>
  );
}

export default App;
