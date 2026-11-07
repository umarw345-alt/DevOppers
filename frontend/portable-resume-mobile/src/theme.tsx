import React from 'react';
import { ActivityIndicator, Platform, Pressable, StatusBar, StyleSheet, Text, TextInput, TextInputProps, View, ViewStyle } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';

export const C = { blue: '#0A6CF0', off: '#6E86AA', green: '#1FB864', red: '#E5484D', ink: '#10203A' };
export const MONO = Platform.select({ ios: 'Menlo', default: 'monospace' });

// Canva scheme: sky blue -> bright blue -> black, full screen.
export function Screen({ children, style }: { children: React.ReactNode; style?: ViewStyle }) {
  const insets = useSafeAreaInsets();
  return (
    <LinearGradient colors={['#A9D8EE', '#1E69D6', '#000000']} locations={[0, 0.4, 0.75]} style={{ flex: 1 }}>
      <StatusBar barStyle="dark-content" />
      <View style={[{ flex: 1, paddingTop: insets.top + 12, paddingBottom: insets.bottom, paddingHorizontal: 22 }, style]}>{children}</View>
    </LinearGradient>
  );
}

export function Pill(p: { label: string; onPress?: () => void; disabled?: boolean; loading?: boolean; color?: string; style?: ViewStyle }) {
  return (
    <Pressable onPress={p.onPress} disabled={p.disabled || p.loading} style={[s.pill, { backgroundColor: p.disabled ? C.off : p.color ?? C.blue }, p.style]}>
      {p.loading ? <ActivityIndicator color="#fff" /> : <Text style={s.pillText}>{p.label}</Text>}
    </Pressable>
  );
}

export function Field({ label, ...p }: TextInputProps & { label: string }) {
  return (
    <View style={{ marginBottom: 10 }}>
      <Text style={s.label}>{label}</Text>
      <TextInput placeholderTextColor="#9AA9BF" {...p} style={[s.input, p.multiline && { minHeight: 84, textAlignVertical: 'top' }, p.style]} />
    </View>
  );
}

export const T = StyleSheet.create({
  h1: { color: '#fff', fontSize: 40, fontWeight: '300', letterSpacing: 1, textShadowColor: 'rgba(0,0,0,.25)', textShadowRadius: 6 },
  h2: { color: '#fff', fontSize: 20, fontWeight: '300', letterSpacing: 0.5, marginTop: 22, marginBottom: 10 },
  tag: { color: '#fff', fontSize: 24, textAlign: 'center', marginBottom: 18 },
  card: { backgroundColor: '#fff', borderRadius: 16, padding: 14, marginBottom: 12 },
  mono: { fontFamily: MONO, color: '#fff' },
});

const s = StyleSheet.create({
  pill: { borderRadius: 24, paddingVertical: 12, paddingHorizontal: 26, alignItems: 'center', justifyContent: 'center', minHeight: 44 },
  pillText: { color: '#fff', fontFamily: MONO, fontWeight: '600', letterSpacing: 1, fontSize: 14 },
  label: { fontFamily: MONO, fontSize: 11, color: '#4B5E7A', marginBottom: 4 },
  input: { borderWidth: 1, borderColor: '#B9C6D8', borderRadius: 10, paddingHorizontal: 10, paddingVertical: 8, fontSize: 15, color: C.ink, backgroundColor: '#fff' },
});
