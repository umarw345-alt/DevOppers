import React, { useState } from 'react';
import { Platform, Pressable, Text, View } from 'react-native';
import { startGoogleSignIn } from '../auth/GoogleAuth';
import { Back, Button, C, Field, Page, T, WalletCard, useWide } from '../theme';

type Props = {
  mode: 'login' | 'register';
  error?: string | null;
  isLoading: boolean;
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (email: string, password: string) => Promise<void>;
  onSwitch: () => void;
  onBack: () => void;
};

export default function Auth({ mode: startMode, error, isLoading, onLogin, onRegister, onSwitch, onBack }: Props) {
  const wide = useWide();
  const [mode, setMode] = useState(startMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [hint, setHint] = useState('');
  const [googleLoading, setGoogleLoading] = useState(false);
  const registering = mode === 'register';

  const submit = () => {
    if (!email.includes('@')) return setHint('Enter your email.');
    if (password.length < 8) return setHint('Passwords are at least 8 characters.');
    setHint('');
    (registering ? onRegister : onLogin)(email.trim(), password).catch(() => undefined);
  };

  const toggle = () => {
    setMode(registering ? 'login' : 'register');
    setHint('');
    onSwitch();
  };

  const continueWithGoogle = () => {
    setHint('');
    setGoogleLoading(true);
    try {
      startGoogleSignIn();
    } catch {
      setGoogleLoading(false);
      setHint('Google sign-in is unavailable right now. Please try again.');
    }
  };

  const form = (
    <View style={{ width: '100%', maxWidth: 420, alignSelf: 'center' }}>
      <View style={[T.card, { padding: 28 }]}>
        <Text style={[T.title, { fontSize: 28 }]}>{registering ? 'Create your account' : 'Log in'}</Text>
        <Text style={[T.dim, { marginBottom: 16 }]}>
          {registering ? 'Free. Next, you upload your resume.' : 'Welcome back. Edit your page and get your Wallet card.'}
        </Text>

        <Field label="Email" value={email} onChangeText={setEmail} keyboardType="email-address" autoComplete="email" placeholder="you@sjsu.edu" />
        <Field
          label="Password"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoComplete={registering ? 'new-password' : 'current-password'}
          placeholder="At least 8 characters"
          onSubmitEditing={submit}
        />
        <Button label={registering ? 'Create account' : 'Log in'} onPress={submit} loading={isLoading} />
        {!!(hint || error) && <Text style={T.error}>{hint || error}</Text>}

        {Platform.OS === 'web' && (
          <>
            <View style={[T.row, { marginVertical: 18 }]}>
              <View style={{ flex: 1, height: 1, backgroundColor: C.line }} />
              <Text style={T.dim}>or</Text>
              <View style={{ flex: 1, height: 1, backgroundColor: C.line }} />
            </View>
            <Pressable
              accessibilityRole="button"
              onPress={continueWithGoogle}
              disabled={isLoading || googleLoading}
              style={({ pressed }) => [{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, minHeight: 46, borderRadius: 12, borderWidth: 1, borderColor: C.line, backgroundColor: C.card }, (pressed || googleLoading) && { opacity: 0.6 }]}
            >
              <Text style={{ color: '#4285F4', fontSize: 18, fontWeight: '800' }}>G</Text>
              <Text style={{ color: C.text, fontSize: 15, fontWeight: '600' }}>{googleLoading ? 'Opening Google…' : 'Continue with Google'}</Text>
            </Pressable>
          </>
        )}
      </View>

      <View style={[T.row, { justifyContent: 'center', marginTop: 12 }]}>
        <Text style={T.dim}>{registering ? 'Already have an account?' : 'New here?'}</Text>
        <Pressable accessibilityRole="button" onPress={toggle}>
          <Text style={{ color: C.link, fontWeight: '600', fontSize: 15 }}>{registering ? 'Log in' : 'Create an account'}</Text>
        </Pressable>
      </View>
    </View>
  );

  return (
    <Page left={<Back label="Home" onPress={onBack} />} center>
      {wide ? (
        <View style={{ flexDirection: 'row', gap: 48, alignItems: 'center' }}>
          <View style={{ flex: 1, backgroundColor: C.accent, borderRadius: 24, padding: 40, gap: 12 }}>
            <Text style={[T.title, { color: '#FFFFFF', fontSize: 34 }]}>Your resume,{'\n'}one scan away.</Text>
            <Text style={{ color: '#E0E3FF', fontSize: 16, lineHeight: 24, marginBottom: 20 }}>
              One upload gives you a portfolio website and a Wallet card recruiters can scan.
            </Text>
            <View style={{ width: 240 }}>
              <WalletCard name="Maya Patel" headline="SWE Student" color="#1C1B19" url="https://devoppers.vercel.app/maya-patel" compact />
            </View>
          </View>
          <View style={{ flex: 1 }}>{form}</View>
        </View>
      ) : form}
    </Page>
  );
}
