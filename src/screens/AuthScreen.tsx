import React, { useCallback, useEffect, useRef } from 'react';
import { Pressable, Text, View } from 'react-native';
import { authStyles } from './authStyles';

type AuthScreenProps = {
  email: string;
  onLogout: () => Promise<void>;
  onInput: () => void;
  isLoading: boolean;
  error?: string;
};

const AuthScreen = ({ email, onLogout, onInput, isLoading, error }: AuthScreenProps) => {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const resetInactivityTimer = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(onInput, 3 * 60 * 1000);
  }, [onInput]);

  useEffect(() => {
    resetInactivityTimer();
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [resetInactivityTimer]);

  return (
    <View onTouchStart={resetInactivityTimer} style={[authStyles.screen, authStyles.content]}>
      <View style={authStyles.card}>
        <Text style={authStyles.successTitle}>AUTHENTICATED</Text>
        <Text style={[authStyles.helper, authStyles.successHelper]}>You are signed in as {email}.</Text>
        {error ? <Text style={authStyles.error}>{error}</Text> : null}
        <Pressable accessibilityRole="button" disabled={isLoading} onPress={onLogout} style={[authStyles.primaryButton, isLoading ? authStyles.disabledButton : undefined]}>
          <Text style={authStyles.primaryButtonText}>{isLoading ? 'LOGGING OUT…' : 'LOG OUT'}</Text>
        </Pressable>
      </View>
    </View>
  );
};

export default AuthScreen;
