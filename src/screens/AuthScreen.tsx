import React from 'react';
import { Pressable, Text, View } from 'react-native';
import { authStyles } from './authStyles';

type AuthScreenProps = {
  email: string;
  onLogout: () => void;
};

const AuthScreen = ({ email, onLogout }: AuthScreenProps) => (
  <View style={[authStyles.screen, authStyles.content]}>
    <View style={authStyles.card}>
      <Text style={authStyles.successTitle}>AUTHENTICATED</Text>
      <Text style={[authStyles.helper, authStyles.successHelper]}>You are signed in as {email}.</Text>
      <Pressable accessibilityRole="button" onPress={onLogout} style={authStyles.primaryButton}>
        <Text style={authStyles.primaryButtonText}>LOG OUT</Text>
      </Pressable>
    </View>
  </View>
);

export default AuthScreen;
