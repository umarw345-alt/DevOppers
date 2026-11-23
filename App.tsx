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

// After a failed Google sign-in the server sends the browser back here with ?auth_error=<message>.
function takeAuthError(): string | null {
  if (Platform.OS !== 'web') return null;
  const w = globalThis as any;
  const message = new URLSearchParams(w.location.search).get('auth_error');
  if (message) w.history.replaceState(null, '', w.location.pathname);
  return message;
}

function App() {
  const { status, user, isLoading, error, accessToken, login, register, logout, recordInput, clearError } = useAuth();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [googleError, setGoogleError] = useState(takeAuthError);
  const [authMode, setAuthMode] = useState<'login' | 'register' | null>(googleError ? 'login' : null); // null = landing page
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
      ? <Auth key={authMode} mode={authMode} error={googleError ?? error} isLoading={isLoading} onLogin={login} onRegister={register} onSwitch={() => { setGoogleError(null); clearError(); }} onBack={() => { setGoogleError(null); clearError(); setAuthMode(null); }} />
      : <Landing onSignUp={() => setAuthMode('register')} onLogIn={() => setAuthMode('login')} />
  ) : (
    // Touch on phones, mouse/pen clicks on the web.
    <View style={{ flex: 1 }} onTouchStart={onTouch} onPointerDown={onTouch}>
      {draft
        ? <Editor token={accessToken} draft={draft} onClose={() => setDraft(null)} />
        : <Home token={accessToken} email={user?.email} onOpen={setDraft} onLogout={() => { setDraft(null); setAuthMode(null); logout(); }} />}
    </View>
  );

  return (
    <SafeAreaProvider initialMetrics={initialWindowMetrics}>
      <StatusBar barStyle="dark-content" />
      {content}
    </SafeAreaProvider>
  );
}

export default App;
