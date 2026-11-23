import React, { useMemo } from 'react';
import { ActivityIndicator, Linking, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, TextInputProps, View, ViewStyle, useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import QRCode from 'qrcode';

// One dark palette, solid colors only.
export const C = {
  bg: '#09090B',
  card: '#141417',
  line: '#27272A',
  text: '#FAFAFA',
  dim: '#A1A1AA',
  accent: '#2563EB',
  link: '#60A5FA',
  danger: '#F87171',
};

export const useWide = () => useWindowDimensions().width >= 900;

type PageProps = { children: React.ReactNode; left?: React.ReactNode; right?: React.ReactNode; footer?: React.ReactNode; width?: number; center?: boolean };

// Every screen: a top bar (left: logo or back, right: actions), scrolling content, optional bottom bar.
export function Page({ children, left = <Logo />, right, footer, width = 1120, center }: PageProps) {
  const insets = useSafeAreaInsets();
  return (
    <View style={[s.page, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
      <View style={s.bar}>
        <View style={[s.barInner, { maxWidth: width }]}>
          {left}
          <View style={T.row}>{right}</View>
        </View>
      </View>
      <ScrollView contentContainerStyle={[s.content, { maxWidth: width }, center && s.center]} keyboardShouldPersistTaps="handled">
        {children}
      </ScrollView>
      {footer && (
        <View style={[s.bar, s.footer]}>
          <View style={[s.barInner, { maxWidth: width, justifyContent: 'flex-end' }]}>{footer}</View>
        </View>
      )}
    </View>
  );
}

export function Logo({ onPress }: { onPress?: () => void }) {
  return (
    <Pressable accessibilityRole="link" accessibilityLabel="Portable Resume home" onPress={onPress} style={T.row}>
      <View style={s.mark}><Text style={s.markText}>P</Text></View>
      <Text style={{ color: C.text, fontSize: 16, fontWeight: '700' }}>Portable Resume</Text>
    </Pressable>
  );
}

export function Back({ onPress, label = 'Back' }: { onPress: () => void; label?: string }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [s.back, pressed && s.faded]}>
      <Text style={{ color: C.text, fontSize: 15, fontWeight: '600' }}>←  {label}</Text>
    </Pressable>
  );
}

type ButtonProps = { label: string; onPress: () => void; kind?: 'primary' | 'secondary' | 'ghost'; small?: boolean; loading?: boolean; disabled?: boolean; style?: ViewStyle };

export function Button({ label, onPress, kind = 'primary', small, loading, disabled, style }: ButtonProps) {
  const ink = kind === 'primary' ? C.bg : C.text;
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      disabled={disabled || loading}
      style={({ pressed }) => [s.button, s[kind], small && s.small, (disabled || pressed) && s.faded, style]}
    >
      {loading ? <ActivityIndicator color={ink} /> : <Text style={{ color: ink, fontSize: small ? 14 : 15, fontWeight: '600' }}>{label}</Text>}
    </Pressable>
  );
}

export function Chip({ label, on, danger, onPress }: { label: string; on?: boolean; danger?: boolean; onPress: () => void }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={[s.chip, on && s.chipOn]}>
      <Text style={{ color: on ? C.bg : danger ? C.danger : C.text, fontWeight: '600', fontSize: 14 }}>{label}</Text>
    </Pressable>
  );
}

export function Field({ label, ...input }: TextInputProps & { label: string }) {
  return (
    <View style={{ marginBottom: 14 }}>
      <Text style={T.label}>{label}</Text>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor="#71717A"
        autoCapitalize="none"
        {...input}
        style={[s.input, input.multiline && s.multiline]}
      />
    </View>
  );
}

// A real, scannable QR code drawn with plain views (one view per run of same-colored cells).
export function QR({ value, size = 132 }: { value: string; size?: number }) {
  const rows = useMemo(() => {
    const { modules } = QRCode.create(value, { errorCorrectionLevel: 'M' });
    return Array.from({ length: modules.size }, (_, y) => {
      const runs: [boolean, number][] = [];
      for (let x = 0; x < modules.size; x++) {
        const dark = !!modules.get(y, x);
        const last = runs[runs.length - 1];
        if (last && last[0] === dark) last[1]++;
        else runs.push([dark, 1]);
      }
      return runs;
    });
  }, [value]);
  const cell = Math.floor(size / rows.length);
  return (
    <View accessibilityLabel={`QR code for ${value}`}>
      {rows.map((runs, y) => (
        <View key={y} style={{ flexDirection: 'row', height: cell }}>
          {runs.map(([dark, n], i) => <View key={i} style={{ width: n * cell, backgroundColor: dark ? '#000000' : '#FFFFFF' }} />)}
        </View>
      ))}
    </View>
  );
}

// Which wallets to offer: iPhones get Apple, Android gets Google, desktop browsers get both.
export function wallets(): ('apple' | 'google')[] {
  if (Platform.OS === 'ios') return ['apple'];
  if (Platform.OS === 'android') return ['google'];
  const agent = (globalThis as { navigator?: { userAgent?: string } }).navigator?.userAgent ?? '';
  if (/iPhone|iPad|iPod/.test(agent)) return ['apple'];
  if (/Android/.test(agent)) return ['google'];
  return ['apple', 'google'];
}

// "Add to ... Wallet" buttons for a published portfolio at `url`.
export function WalletButtons({ url, small }: { url: string; small?: boolean }) {
  return (
    <>
      {wallets().map((wallet) => wallet === 'apple'
        ? <Button key="apple" small={small} label="Add to Apple Wallet" onPress={() => Linking.openURL(`${url}/pass.pkpass`)} />
        : <Button key="google" small={small} label="Add to Google Wallet" onPress={() => Linking.openURL(`${url}/google-wallet`)} />)}
    </>
  );
}

// What the Wallet card looks like; the QR code opens the portfolio.
export function WalletCard({ name, headline, color, url }: { name: string; headline?: string; color: string; url: string }) {
  const n = parseInt(color.slice(1), 16);
  const ink = ((n >> 16) * 299 + ((n >> 8) & 255) * 587 + (n & 255) * 114) / 1000 > 150 ? '#000000' : '#FFFFFF';
  return (
    <View style={[s.wallet, { backgroundColor: color }]}>
      <Text style={{ color: ink, fontSize: 15, fontWeight: '700' }}>Portable Resume</Text>
      <Text style={[s.walletLabel, { color: ink, marginTop: 28 }]}>NAME</Text>
      <Text style={{ color: ink, fontSize: 26, fontWeight: '700' }}>{name || 'Your Name'}</Text>
      {!!headline && <Text style={[s.walletLabel, { color: ink, marginTop: 14 }]}>TITLE</Text>}
      {!!headline && <Text style={{ color: ink, fontSize: 15 }}>{headline}</Text>}
      <View style={s.qrBox}>
        <QR value={url} />
        <Text style={{ color: '#000000', fontSize: 11, marginTop: 6 }}>Scan for my portfolio</Text>
      </View>
    </View>
  );
}

export const STEPS = [
  ['Upload your resume', 'A PDF or a photo. We read it and fill everything in for you.'],
  ['Check it and publish', 'Fix anything, choose a design, and get your own link.'],
  ['Add it to your Wallet', 'Apple Wallet or Google Wallet. Show the card at a career fair; recruiters scan it with their camera.'],
];

export function Steps({ active }: { active?: number }) {
  const wide = useWide();
  return (
    <View style={{ flexDirection: wide ? 'row' : 'column', gap: 12 }}>
      {STEPS.map(([title, detail], i) => (
        <View key={title} style={[T.card, { flex: 1, marginBottom: 0 }, i === active && { borderColor: C.accent }]}>
          <View style={[s.num, i === active && { backgroundColor: C.accent }]}>
            <Text style={{ color: C.text, fontWeight: '700' }}>{i + 1}</Text>
          </View>
          <Text style={[T.body, { fontWeight: '700', fontSize: 16 }]}>{title}</Text>
          <Text style={T.dim}>{detail}</Text>
        </View>
      ))}
    </View>
  );
}

// Text and layout styles shared by every screen.
export const T = StyleSheet.create({
  title: { color: C.text, fontSize: 32, fontWeight: '700', letterSpacing: -0.6 },
  h2: { color: C.text, fontSize: 20, fontWeight: '700', marginTop: 32, marginBottom: 12 },
  overline: { color: C.link, fontSize: 13, fontWeight: '700', letterSpacing: 0.8, marginBottom: 8 },
  body: { color: C.text, fontSize: 15, lineHeight: 22 },
  dim: { color: C.dim, fontSize: 15, lineHeight: 22 },
  label: { color: C.text, fontSize: 14, fontWeight: '600', marginBottom: 6 },
  error: { color: C.danger, fontSize: 14, marginTop: 12 },
  card: { backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: 14, padding: 20, marginBottom: 12, gap: 8 },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, alignItems: 'center' },
});

const s = StyleSheet.create({
  page: { flex: 1, backgroundColor: C.bg },
  bar: { borderBottomWidth: 1, borderColor: C.line, paddingHorizontal: 20 },
  barInner: { width: '100%', alignSelf: 'center', minHeight: 64, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 },
  footer: { borderBottomWidth: 0, borderTopWidth: 1 },
  content: { width: '100%', alignSelf: 'center', paddingHorizontal: 20, paddingTop: 32, paddingBottom: 64 },
  center: { flexGrow: 1, justifyContent: 'center' },
  mark: { width: 28, height: 28, borderRadius: 7, backgroundColor: C.accent, alignItems: 'center', justifyContent: 'center' },
  markText: { color: '#FFFFFF', fontWeight: '800', fontSize: 15 },
  back: { minHeight: 40, justifyContent: 'center', paddingRight: 8 },
  button: { minHeight: 46, borderRadius: 10, paddingHorizontal: 20, alignItems: 'center', justifyContent: 'center' },
  small: { minHeight: 36, paddingHorizontal: 14, borderRadius: 8 },
  primary: { backgroundColor: C.text },
  secondary: { borderWidth: 1, borderColor: C.line, backgroundColor: C.card },
  ghost: {},
  faded: { opacity: 0.6 },
  chip: { minHeight: 36, paddingHorizontal: 14, borderRadius: 18, justifyContent: 'center', borderWidth: 1, borderColor: C.line, backgroundColor: C.card },
  chipOn: { backgroundColor: C.text, borderColor: C.text },
  input: { minHeight: 46, borderRadius: 10, borderWidth: 1, borderColor: C.line, backgroundColor: C.card, color: C.text, fontSize: 16, paddingHorizontal: 14, paddingVertical: 11 },
  multiline: { minHeight: 100, textAlignVertical: 'top' },
  wallet: { width: '100%', maxWidth: 340, alignSelf: 'center', borderRadius: 20, padding: 22 },
  walletLabel: { fontSize: 11, fontWeight: '700', letterSpacing: 1, opacity: 0.8 },
  qrBox: { alignSelf: 'center', alignItems: 'center', backgroundColor: '#FFFFFF', borderRadius: 12, padding: 12, marginTop: 28 },
  num: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center', backgroundColor: C.line, marginBottom: 6 },
});
