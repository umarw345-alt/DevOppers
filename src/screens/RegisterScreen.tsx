import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { authColors, authStyles } from './authStyles';

type RegisterScreenProps = {
  onRegister: (email: string, password: string) => void;
  onLoginPress: () => void;
};

const RegisterScreen = ({ onRegister, onLoginPress }: RegisterScreenProps) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');

  const submit = () => {
    const normalizedEmail = email.trim().toLowerCase();
    if (!normalizedEmail.includes('@')) {
      setError('Enter a valid email address.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setError('');
    onRegister(normalizedEmail, password);
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={authStyles.screen}>
      <ScrollView contentContainerStyle={authStyles.content} keyboardShouldPersistTaps="handled">
        <View style={authStyles.brand}>
          <Text style={authStyles.title}>PORTABLE RESUME</Text>
          <Text style={authStyles.slogan}>Create your account and carry your portfolio with you.</Text>
        </View>
        <View style={authStyles.card}>
          <Text style={authStyles.label}>Email</Text>
          <TextInput accessibilityLabel="Registration email" autoCapitalize="none" autoComplete="email" keyboardType="email-address" onChangeText={setEmail} placeholder="example@example.com" placeholderTextColor={authColors.muted} style={[authStyles.input, error ? authStyles.inputError : undefined]} textContentType="emailAddress" value={email} />
          <Text style={authStyles.label}>Password</Text>
          <TextInput accessibilityLabel="Registration password" autoCapitalize="none" autoComplete="new-password" onChangeText={setPassword} placeholder="At least 8 characters" placeholderTextColor={authColors.muted} secureTextEntry style={[authStyles.input, error ? authStyles.inputError : undefined]} textContentType="newPassword" value={password} />
          <Text style={authStyles.label}>Confirm password</Text>
          <TextInput accessibilityLabel="Confirm registration password" autoCapitalize="none" autoComplete="new-password" onChangeText={setConfirmPassword} placeholder="Repeat your password" placeholderTextColor={authColors.muted} secureTextEntry style={[authStyles.input, error ? authStyles.inputError : undefined]} textContentType="newPassword" value={confirmPassword} />
          {error ? <Text style={authStyles.error}>{error}</Text> : null}
          <Pressable accessibilityRole="button" onPress={submit} style={authStyles.primaryButton}><Text style={authStyles.primaryButtonText}>CREATE ACCOUNT</Text></Pressable>
          <Pressable accessibilityRole="button" onPress={onLoginPress} style={authStyles.secondaryAction}><Text style={authStyles.secondaryActionText}>Already have an account? Log in</Text></Pressable>
          <Text style={authStyles.helper}>Your password is hashed by the authentication service.</Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

export default RegisterScreen;
