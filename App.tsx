/**
 * Sample React Native App
 * https://github.com/facebook/react-native
 *
 * @format
 */

import { useState } from 'react';
import { StatusBar } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import AuthScreen from './src/screens/AuthScreen';
import LoginScreen from './src/screens/LoginScreen';
import RegisterScreen from './src/screens/RegisterScreen';

type Screen = 'login' | 'register' | 'authenticated';

function App() {
  const [screen, setScreen] = useState<Screen>('login');
  const [authenticatedEmail, setAuthenticatedEmail] = useState('');

  const showAuthenticated = (email: string) => {
    setAuthenticatedEmail(email);
    setScreen('authenticated');
  };

  return (
    <SafeAreaProvider>
      <StatusBar barStyle="light-content" />
      {screen === 'login' ? (
        <LoginScreen onLogin={showAuthenticated} onRegisterPress={() => setScreen('register')} />
      ) : screen === 'register' ? (
        <RegisterScreen onLoginPress={() => setScreen('login')} onRegister={showAuthenticated} />
      ) : (
        <AuthScreen email={authenticatedEmail} onLogout={() => setScreen('login')} />
      )}
    </SafeAreaProvider>
  );
}

export default App;
