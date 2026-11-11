import React, { useEffect, useRef, useState } from 'react';
import { Alert, BackHandler, Platform, Pressable, ScrollView, Text, View } from 'react-native';
import { WebView } from 'react-native-webview';
import { C, MONO, Pill, Screen, T } from '../theme';
import { DEFAULT_TPLS, Resume, Tpl, getTemplates, errorMessage, previewHtml } from '../api';
import type { Site } from './Menu';

// react-native-webview has no web version, so browsers get an iframe.
// sandbox="" blocks scripts in the preview; the generated site is plain HTML + CSS.
function Preview({ html, onError }: { html: string; onError: () => void }) {
  if (Platform.OS === 'web') {
    return React.createElement('iframe', {
      srcDoc: html, sandbox: '', title: 'Portfolio preview',
      style: { border: 0, width: '100%', height: '100%' },
    });
  }
  return <WebView originWhitelist={['*']} source={{ html }} nestedScrollEnabled onError={onError} />;
}

const ACCENTS = ['#1e3a8a', '#8b2e2e', '#0f766e', '#6d28d9', '#b45309', '#be123c'];
const FONTS = ['serif', 'sans', 'mono', 'display'];

export default function Template({ resume, onBack, onDone }: { resume: Resume; onBack: () => void; onDone: (s: Site) => Promise<void> }) {
  const [tpls, setTpls] = useState<Tpl[]>(DEFAULT_TPLS);
  const [sel, setSel] = useState(DEFAULT_TPLS[0].id);
  const [accent, setAccent] = useState<string>();
  const [font, setFont] = useState<string>();
  const [html, setHtml] = useState('');
  const [err, setErr] = useState('');

  const adding = useRef(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => { if (!saving) onBack(); return true; });
    return () => sub.remove();
  }, [onBack, saving]);
  useEffect(() => {
    let live = true;
    getTemplates().then((items) => {
      if (!live) return;
      setTpls(items);
      setSel((current) => items.some((item) => item.id === current) ? current : items[0].id);
    });
    return () => { live = false; };
  }, []);
  useEffect(() => {
    let live = true;
    setHtml(''); setErr(''); setLoading(true);
    const t = setTimeout(() => {
      previewHtml(resume, sel, { accent, font }).then((h) => live && (setHtml(h), setErr(''))).catch((e: unknown) => { if (live) { setHtml(''); setErr(errorMessage(e)); } }).finally(() => { if (live) setLoading(false); });
    }, 350);
    return () => { live = false; clearTimeout(t); };
  }, [sel, accent, font, resume]);

  // TODO: call POST /portfolio when the backend supports publishing.
  const add = async () => {
    if (adding.current) return;
    adding.current = true; setSaving(true);
    const selected = tpls.find((t) => t.id === sel) ?? DEFAULT_TPLS[0];
    try { await onDone({ id: `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`, name: resume.name || 'My site', template: sel,
      url: '', resume, theme: { accent: accent ?? selected.accent, font: font ?? selected.font }, isDemo: true }); }
    catch { setErr('Could not save on this device. Please try again.'); }
    finally { adding.current = false; setSaving(false); }
  };
  const chip = (on: boolean) => ({ paddingHorizontal: 14, paddingVertical: 8, borderRadius: 18, backgroundColor: on ? C.blue : 'rgba(255,255,255,.15)' });

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ paddingBottom: 20 }}>
        <Text style={[T.h1, { fontSize: 24 }]}>CHOOSE A PORTFOLIO TEMPLATE</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginTop: 18 }}>
          {tpls.map((t) => (
            <Pressable key={t.id} onPress={() => { setSel(t.id); setAccent(undefined); setFont(undefined); }} style={{ alignItems: 'center', marginRight: 14, padding: 10, borderRadius: 16, borderWidth: 2, borderColor: sel === t.id ? '#fff' : 'transparent' }}>
              <View style={{ width: 70, height: 70, borderRadius: 14, backgroundColor: t.accent }} />
              <Text style={[T.mono, { marginTop: 6, textTransform: 'uppercase' }]}>{t.id}</Text>
            </Pressable>
          ))}
        </ScrollView>
        <Text style={[T.mono, { marginTop: 14 }]}>ACCENT</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginTop: 8, alignItems: 'center' }}>
          {ACCENTS.map((a) => <Pressable key={a} onPress={() => setAccent(a)} style={{ width: 30, height: 30, borderRadius: 15, backgroundColor: a, borderWidth: accent === a ? 3 : 0, borderColor: '#fff' }} />)}
          <Pressable onPress={() => setAccent(undefined)}><Text style={[T.mono, { fontSize: 12 }]}>DEFAULT</Text></Pressable>
        </View>
        <Text style={[T.mono, { marginTop: 14 }]}>FONT</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
          {FONTS.map((f) => <Pressable key={f} onPress={() => setFont(f)} style={chip(font === f)}><Text style={{ color: '#fff', fontFamily: MONO }}>{f}</Text></Pressable>)}
        </View>
        {!!err && <Text style={{ color: '#FFB4B4', marginTop: 12 }}>{err}</Text>}
        <View style={{ height: 360, borderRadius: 16, overflow: 'hidden', backgroundColor: '#fff', marginTop: 14 }}>
          {html && !loading && !err ? <Preview html={html} onError={() => { setHtml(''); setErr('Could not display the preview.'); }} /> : <Text style={{ padding: 16, color: '#6C86AC' }}>{err ? 'No preview yet.' : 'Loading preview…'}</Text>}
        </View>
        <Text style={[T.mono, { marginTop: 12 }]}>Saved on this device. Publishing and shareable links are not available yet.</Text>
        <Pill label="GENERATE WITH AI" color="#33445F" style={{ marginTop: 14 }} onPress={() => Alert.alert('Coming soon', 'AI-generated designs are planned for later.')} />
      </ScrollView>
      <View style={{ flexDirection: 'row', gap: 12, paddingVertical: 14 }}>
        <Pill label="BACK" color="#33445F" onPress={onBack} disabled={saving} style={{ flex: 1 }} />
        <Pill label="ADD TO MY LIST" color={C.green} onPress={add} loading={saving} style={{ flex: 1.4 }} />
      </View>
    </Screen>
  );
}
