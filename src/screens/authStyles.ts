import { StyleSheet } from 'react-native';

export const authColors = {
  blue: '#2f83cf',
  deepBlue: '#0b3974',
  white: '#ffffff',
  ink: '#17304f',
  muted: '#667085',
  field: '#f7f9fc',
  border: '#c9d2df',
  danger: '#b42318',
};

export const authStyles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: authColors.deepBlue },
  content: { flexGrow: 1, justifyContent: 'center', paddingHorizontal: 24, paddingVertical: 36 },
  brand: { alignItems: 'center', marginBottom: 24 },
  title: { color: authColors.white, fontSize: 36, fontWeight: '300', letterSpacing: 1.5, textAlign: 'center' },
  successTitle: { color: authColors.ink, fontSize: 28, fontWeight: '300', letterSpacing: 1.5, textAlign: 'center' },
  slogan: { color: authColors.white, fontSize: 17, lineHeight: 22, marginTop: 10, maxWidth: 290, textAlign: 'center' },
  card: { alignSelf: 'center', backgroundColor: authColors.white, borderRadius: 12, maxWidth: 440, padding: 22, width: '100%' },
  label: { color: authColors.ink, fontSize: 13, fontWeight: '700', marginBottom: 6, marginTop: 12 },
  input: { backgroundColor: authColors.field, borderColor: authColors.border, borderRadius: 7, borderWidth: 1, color: authColors.ink, fontSize: 16, minHeight: 48, paddingHorizontal: 13 },
  inputError: { borderColor: authColors.danger },
  error: { color: authColors.danger, fontSize: 13, marginTop: 8 },
  primaryButton: { alignItems: 'center', backgroundColor: authColors.blue, borderRadius: 18, justifyContent: 'center', marginTop: 20, minHeight: 44 },
  primaryButtonText: { color: authColors.white, fontSize: 14, fontWeight: '800', letterSpacing: 0.8 },
  secondaryAction: { alignItems: 'center', marginTop: 18 },
  secondaryActionText: { color: authColors.blue, fontSize: 14, fontWeight: '700' },
  helper: { color: authColors.muted, fontSize: 12, marginTop: 16, textAlign: 'center' },
  successHelper: { color: authColors.ink },
});
