import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Platform, StatusBar, View } from 'react-native';
import { initialWindowMetrics, SafeAreaProvider } from 'react-native-safe-area-context';

import { useAuth } from './src/auth/AuthContext';
import type { Draft } from './src/api';
import { C } from './src/theme';
import Auth from './src/screens/Auth';
import Editor from './src/screens/Editor';
import Home from './src/screens/Home';
import Landing from './src/screens/Landing';

function App() {
  const { status, user, isLoading, error, accessToken, login, register, logout, recordInput, clearError } = useAuth();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [authMode, setAuthMode] = useState<'login' | 'register' | null>(null); // null = landing page
  const lastInput = useRef(0);

  // On web, the browser's back button leaves a sub-screen (log in, editor) instead of leaving the site.
  const inSubScreen = !!draft || !!authMode;
  useEffect(() => {
    if (Platform.OS !== 'web' || !inSubScreen) return;
    const w = globalThis as any;
    w.history.pushState(null, '');
    const back = () => { setDraft(null); setAuthMode(null); };
    w.addEventListener('popstate', back);
    return () => w.removeEventListener('popstate', back);
  }, [inSubScreen]);

  // Tell the server the user is still here (at most once a minute) so the idle timeout doesn't log them out.
  const onTouch = () => {
    if (Date.now() - lastInput.current < 60_000) return;
    lastInput.current = Date.now();
    recordInput().catch(() => undefined);
  };

  const content = status === 'loading' ? (
    <View style={{ flex: 1, backgroundColor: C.bg, justifyContent: 'center' }}>
      <ActivityIndicator color={C.accent} size="large" />
    </View>
  ) : status === 'signed_out' ? (
    authMode
      ? <Auth key={authMode} mode={authMode} error={error} isLoading={isLoading} onLogin={login} onRegister={register} onSwitch={clearError} onBack={() => { clearError(); setAuthMode(null); }} />
      : <Landing onSignUp={() => setAuthMode('register')} onLogIn={() => setAuthMode('login')} />
  ) : (
    <View style={{ flex: 1 }} onTouchStart={onTouch}>
      {draft
        ? <Editor token={accessToken} draft={draft} onClose={() => setDraft(null)} />
        : <Home token={accessToken} email={user?.email} onOpen={setDraft} onLogout={() => { setDraft(null); setAuthMode(null); logout(); }} />}
    </View>
  );

  return (
    <SafeAreaProvider initialMetrics={initialWindowMetrics}>
      <StatusBar barStyle="light-content" />
      {content}
    </SafeAreaProvider>
  );
}

export default App;
