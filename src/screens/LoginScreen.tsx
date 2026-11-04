import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { authColors, authStyles } from './authStyles';

type LoginScreenProps = {
  onLogin: (email: string, password: string) => Promise<void>;
  onRegisterPress: () => void;
  isLoading: boolean;
  error?: string;
};

const LoginScreen = ({ onLogin, onRegisterPress, isLoading, error: serverError }: LoginScreenProps) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const submit = () => {
    const normalizedEmail = email.trim().toLowerCase();
    if (!normalizedEmail.includes('@') || password.length < 8) {
      setError('Enter a valid email and a password with at least 8 characters.');
      return;
    }
    setError('');
    onLogin(normalizedEmail, password).catch(() => undefined);
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={authStyles.screen}>
      <ScrollView contentContainerStyle={authStyles.content} keyboardShouldPersistTaps="handled">
        <View style={authStyles.brand}>
          <Text style={authStyles.title}>PORTABLE RESUME</Text>
          <Text style={authStyles.slogan}>Make serving your portfolios ergonomic.</Text>
        </View>
        <View style={authStyles.card}>
          <Text style={authStyles.label}>Email</Text>
          <TextInput accessibilityLabel="Email" autoCapitalize="none" autoComplete="email" keyboardType="email-address" onChangeText={setEmail} placeholder="example@example.com" placeholderTextColor={authColors.muted} style={[authStyles.input, error ? authStyles.inputError : undefined]} textContentType="emailAddress" value={email} />
          <Text style={authStyles.label}>Password</Text>
          <TextInput accessibilityLabel="Password" autoCapitalize="none" autoComplete="password" onChangeText={setPassword} placeholder="Your password here" placeholderTextColor={authColors.muted} secureTextEntry style={[authStyles.input, error ? authStyles.inputError : undefined]} textContentType="password" value={password} />
          {error || serverError ? <Text style={authStyles.error}>{error || serverError}</Text> : null}
          <Pressable accessibilityRole="button" disabled={isLoading} onPress={submit} style={[authStyles.primaryButton, isLoading ? authStyles.disabledButton : undefined]}><Text style={authStyles.primaryButtonText}>{isLoading ? 'SIGNING IN…' : 'LOGIN'}</Text></Pressable>
          <Pressable accessibilityRole="button" onPress={() => {}} style={authStyles.secondaryAction}><Text style={authStyles.secondaryActionText}>Forgot username or password?</Text></Pressable>
          <Pressable accessibilityRole="button" onPress={onRegisterPress} style={authStyles.secondaryAction}><Text style={authStyles.secondaryActionText}>Create an account</Text></Pressable>
          <Text style={authStyles.helper}>Your credentials are sent securely through the authentication service.</Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

export default LoginScreen;
