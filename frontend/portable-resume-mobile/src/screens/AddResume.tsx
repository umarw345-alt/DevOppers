import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, BackHandler, Pressable, ScrollView, Text, View } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import { C, Field, Pill, Screen, T } from '../theme';
import { EMPTY_ENTRY, Entry, Resume, USE_SAMPLE_DATA, errorMessage, extractResume } from '../api';

function Entries({ title, items, onChange }: { title: string; items: Entry[]; onChange: (e: Entry[]) => void }) {
  const up = (i: number, p: Partial<Entry>) => onChange(items.map((e, j) => (j === i ? { ...e, ...p } : e)));
  return (
    <View>
      <Text style={T.h2}>{title}</Text>
      {items.map((e, i) => (
        <View key={i} style={T.card}>
          <Field label="Organization" value={e.organization} onChangeText={(v) => up(i, { organization: v })} />
          <Field label="Title" value={e.title} onChangeText={(v) => up(i, { title: v })} />
          <View style={{ flexDirection: 'row', gap: 10 }}>
            <View style={{ flex: 1 }}><Field label="Start (2024-06)" value={e.start} autoCapitalize="none" onChangeText={(v) => up(i, { start: v })} /></View>
            <View style={{ flex: 1 }}><Field label="End (blank = now)" value={e.end} autoCapitalize="none" onChangeText={(v) => up(i, { end: v })} /></View>
          </View>
          <Field label="Details (one per line)" multiline value={e.bullets} onChangeText={(v) => up(i, { bullets: v })} />
          <Pressable onPress={() => onChange(items.filter((_, j) => j !== i))}><Text style={{ color: C.red }}>Remove</Text></Pressable>
        </View>
      ))}
      <Pressable onPress={() => onChange([...items, { ...EMPTY_ENTRY }])}><Text style={[T.mono, { marginBottom: 8 }]}>+ ADD</Text></Pressable>
    </View>
  );
}

export default function AddResume({ initialResume, accessToken, onBack, onContinue }: { initialResume: Resume | null; accessToken?: string | null; onBack: (r: Resume | null) => void; onContinue: (r: Resume) => void }) {
  const [file, setFile] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [r, setR] = useState<Resume | null>(initialResume);
  const set = (p: Partial<Resume>) => r && setR({ ...r, ...p });

  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => { onBack(r); return true; });
    return () => sub.remove();
  }, [onBack, r]);
  const picking = useRef(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const pick = async () => {
    if (picking.current) return;
    picking.current = true; setBusy(true); setErr('');
    try {
      const res = await DocumentPicker.getDocumentAsync({ type: ['application/pdf', 'image/jpeg', 'image/png'], copyToCacheDirectory: true });
      if (res.canceled || !mounted.current) return;
      const f = res.assets?.[0];
      if (!f) throw new Error('No file was selected. Please try again.');
      if (f.size && f.size > 10 * 1024 * 1024) throw new Error('File is over 10 MB.');
      const next = await extractResume({ uri: f.uri, name: f.name, mimeType: f.mimeType, file: f.file }, accessToken);
      if (mounted.current) { setR(next); setFile(f.name); }
    } catch (e: unknown) { if (mounted.current) setErr(errorMessage(e)); }
    finally { picking.current = false; if (mounted.current) setBusy(false); }
  };

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ paddingBottom: 24 }} keyboardShouldPersistTaps="handled">
        <Text style={[T.h1, { fontSize: 26 }]}>ADD RESUME</Text>
        <Text style={T.h2}>1. UPLOAD YOUR RESUME</Text>
        <Pill label={`${file || 'CHOOSE PDF, JPEG OR PNG'}  📂`} onPress={pick} disabled={busy} />
        {busy && <View style={{ alignItems: 'center', marginTop: 20 }}><ActivityIndicator color="#fff" size="large" /><Text style={[T.mono, { marginTop: 8 }]}>Reading your resume…</Text></View>}
        {!!err && <Text style={{ color: '#FFB4B4', marginTop: 10 }}>{err}</Text>}
        {USE_SAMPLE_DATA && <Text style={[T.mono, { marginTop: 12 }]}>Demo: selecting a file loads an example resume. Replace the text with your own details.</Text>}
        <Text style={T.h2}>2. EDIT THE CONTENT</Text>
        {!r ? <Text style={[T.mono, { opacity: 0.6 }]}>The extracted text will appear here.</Text> : (
          <View>
            <View style={T.card}>
              <Field label="Name" value={r.name} onChangeText={(v) => set({ name: v })} />
              <Field label="Headline" value={r.headline} onChangeText={(v) => set({ headline: v })} maxLength={80} />
              <Field label="Email" value={r.email} autoCapitalize="none" keyboardType="email-address" onChangeText={(v) => set({ email: v })} />
              <Field label="Phone" value={r.phone} keyboardType="phone-pad" onChangeText={(v) => set({ phone: v })} />
              <Field label="Location" value={r.location} onChangeText={(v) => set({ location: v })} />
              <Field label="Summary" multiline value={r.summary} onChangeText={(v) => set({ summary: v })} />
              <Field label="Skills (comma separated)" value={r.skills} onChangeText={(v) => set({ skills: v })} />
            </View>
            <Entries title="Experience" items={r.experience} onChange={(experience) => set({ experience })} />
            <Entries title="Education" items={r.education} onChange={(education) => set({ education })} />
          </View>
        )}
      </ScrollView>
      <View style={{ flexDirection: 'row', gap: 12, paddingVertical: 14 }}>
        <Pill label="BACK" color="#33445F" onPress={() => onBack(r)} style={{ flex: 1 }} />
        <Pill label="CONTINUE" disabled={!r || !r.name.trim() || busy} onPress={() => r && onContinue(r)} style={{ flex: 1 }} />
      </View>
    </Screen>
  );
}
