import React, { useState } from 'react';
import { ScrollView, Text, View, Pressable } from 'react-native';
import { C, Field, Pill, Screen, T } from '../theme';
import { auth, clearSession, errorMessage } from '../api';

export default function Landing({ onDone }: { onDone: () => void }) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [pw, setPw] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const submit = async () => {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()) || !pw || (mode === 'register' && pw.length < 8)) { setErr(mode === 'register' ? 'Enter a valid email and a password of 8+ characters.' : 'Enter a valid email and password.'); return; }
    setBusy(true); setErr('');
    try {
      const signedIn = await auth(mode, email.trim().toLowerCase(), pw);
      if (signedIn) onDone();
      else { setMode('login'); setPw(''); setErr('Account created. Log in to continue; check your email if verification is required.'); }
    }
    catch (e: unknown) { setErr(errorMessage(e)); }
    finally { setBusy(false); }
  };

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: 'space-between', paddingBottom: 36 }} keyboardShouldPersistTaps="handled">
        <Text style={T.h1}>PORTABLE{'\n'}RESUME</Text>
        <View style={{ alignItems: 'center' }}>
          <Text style={T.tag}>Make serving your portfolios ergonomic.</Text>
          {!open ? <Pill label="LOGIN/SIGN UP" onPress={() => setOpen(true)} /> : (
            <View style={[T.card, { width: '100%', borderWidth: 2, borderColor: '#7FB8F0' }]}>
              <Field label="Email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" autoComplete="email" />
              <Field label="Password" value={pw} onChangeText={setPw} autoCapitalize="none" secureTextEntry />
              {!!err && <Text style={{ color: C.red, marginBottom: 8 }}>{err}</Text>}
              <Pill label={mode === 'login' ? 'LOG IN' : 'CREATE ACCOUNT'} onPress={submit} loading={busy} />
              <Pressable disabled={busy} onPress={() => { setMode(mode === 'login' ? 'register' : 'login'); setErr(''); }}>
                <Text style={{ color: C.blue, textAlign: 'center', marginTop: 12 }}>{mode === 'login' ? 'New here? Sign up' : 'Have an account? Log in'}</Text>
              </Pressable>
              <Pressable disabled={busy} onPress={() => { clearSession(); onDone(); }}><Text style={{ color: '#6C86AC', textAlign: 'center', marginTop: 10 }}>Skip (demo mode)</Text></Pressable>
            </View>
          )}
        </View>
      </ScrollView>
    </Screen>
  );
}
