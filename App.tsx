import { useState } from 'react';
import { ActivityIndicator, StatusBar, Text, View } from 'react-native';
import { initialWindowMetrics, SafeAreaProvider } from 'react-native-safe-area-context';

import LoginScreen from './src/screens/LoginScreen';
import RegisterScreen from './src/screens/RegisterScreen';
import PortfolioHomeScreen from './src/screens/PortfolioHomeScreen';
import { useAuth } from './src/auth/AuthContext';
import { authColors, authStyles } from './src/screens/authStyles';

type Screen = 'login' | 'register';

function App() {
  const [screen, setScreen] = useState<Screen>('login');
  const { status, isLoading, error, login, register, logout, recordInput, clearError } = useAuth();

  const content = status === 'loading' ? (
    <View style={[authStyles.screen, authStyles.content]}>
      <ActivityIndicator color={authColors.white} size="large" />
      <Text style={authStyles.slogan}>Restoring your session…</Text>
    </View>
  ) : status === 'signed_in' ? (
    <PortfolioHomeScreen onInput={recordInput} onLogout={logout} />
  ) : screen === 'register' ? (
    <RegisterScreen
      error={error ?? undefined}
      isLoading={isLoading}
      onLoginPress={() => { clearError(); setScreen('login'); }}
      onRegister={register}
    />
  ) : (
    <LoginScreen
      error={error ?? undefined}
      isLoading={isLoading}
      onLogin={login}
      onRegisterPress={() => { clearError(); setScreen('register'); }}
    />
  );

  return (
    <SafeAreaProvider initialMetrics={initialWindowMetrics}>
      <StatusBar barStyle="light-content" />
      {content}
    </SafeAreaProvider>
  );
}

export default App;
