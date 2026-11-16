import React, { useEffect, useState } from 'react';
import { Linking, Platform, Pressable, Text, View, useWindowDimensions } from 'react-native';
import { WebView } from 'react-native-webview';
import { Draft, EMPTY_ENTRY, Entry, Portfolio, Resume, TEMPLATES, previewHtml, savePortfolio, slugify } from '../api';
import { Back, Button, C, Chip, Field, Page, T, WalletCard, useWide } from '../theme';

const ACCENTS = ['#1e3a8a', '#8b2e2e', '#0f766e', '#6d28d9', '#b45309', '#fbbf24'];
const HIDEABLE = [['contact.email', 'Email'], ['contact.phone', 'Phone'], ['contact.location', 'Location']];

// react-native-webview has no web version, so browsers get an iframe. sandbox="" blocks scripts.
function Preview({ html, height }: { html: string; height: number }) {
  if (Platform.OS === 'web') {
    return React.createElement('iframe', { srcDoc: html, sandbox: '', title: 'Preview', style: { border: 0, width: '100%', height, borderRadius: 12, background: '#fff' } });
  }
  return <WebView originWhitelist={['*']} source={{ html }} style={{ height, borderRadius: 12 }} />;
}

type Props = { token: string | null; draft: Draft; onClose: () => void };

export default function Editor({ token, draft, onClose }: Props) {
  const wide = useWide();
  const { height } = useWindowDimensions();
  const [resume, setResume] = useState(draft.resume);
  const [template, setTemplate] = useState(draft.template_id);
  const [accent, setAccent] = useState(draft.theme.accent);
  const [slug, setSlug] = useState(draft.slug ?? slugify(draft.resume.name));
  const [html, setHtml] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [published, setPublished] = useState<Portfolio | null>(null);
  const theme = accent ? { accent } : {};

  const set = (patch: Partial<Resume>) => setResume((r) => ({ ...r, ...patch }));
  const setEntry = (key: 'experience' | 'education', i: number, patch: Partial<Entry>) =>
    set({ [key]: resume[key].map((e, j) => (j === i ? { ...e, ...patch } : e)) });

  // Re-render the preview 0.5 s after the last change.
  useEffect(() => {
    if (!resume.name.trim()) return setHtml('');
    const timer = setTimeout(() => {
      previewHtml(resume, template, accent ? { accent } : {}).then((page) => { setHtml(page); setError(''); }).catch((e) => setError(e.message));
    }, 500);
    return () => clearTimeout(timer);
  }, [resume, template, accent]);

  const publish = async () => {
    if (!resume.name.trim()) return setError('Add your name first.');
    setSaving(true);
    try {
      setPublished(await savePortfolio(token, slug, { resume, template_id: template, theme }));
      setError('');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const entries = (key: 'experience' | 'education', title: string, place: string) => (
    <>
      <Text style={T.h2}>{title}</Text>
      {resume[key].map((e, i) => (
        <View key={i} style={T.card}>
          <Field label={place} value={e.organization} onChangeText={(v) => setEntry(key, i, { organization: v })} autoCapitalize="words" />
          <Field label="Title" value={e.title} onChangeText={(v) => setEntry(key, i, { title: v })} autoCapitalize="words" />
          <View style={T.row}>
            <View style={{ flex: 1 }}><Field label="Start" value={e.start} onChangeText={(v) => setEntry(key, i, { start: v })} placeholder="2024-06" /></View>
            <View style={{ flex: 1 }}><Field label="End" value={e.end} onChangeText={(v) => setEntry(key, i, { end: v })} placeholder="blank = Present" /></View>
          </View>
          <Field label="Highlights (one per line)" value={e.bullets} onChangeText={(v) => setEntry(key, i, { bullets: v })} multiline autoCapitalize="sentences" />
          <Chip label="Remove" danger onPress={() => set({ [key]: resume[key].filter((_, j) => j !== i) })} />
        </View>
      ))}
      <Chip label={`+ Add ${title.toLowerCase()}`} onPress={() => set({ [key]: [...resume[key], EMPTY_ENTRY] })} />
    </>
  );

  if (published) {
    return (
      <Page left={<Back label="Dashboard" onPress={onClose} />}>
        <View style={{ flexDirection: wide ? 'row' : 'column', gap: 48, alignItems: wide ? 'center' : 'stretch', paddingVertical: wide ? 32 : 0 }}>
          <View style={{ flex: wide ? 1 : undefined }}>
            <Text style={T.overline}>{draft.slug ? 'SAVED' : 'STEP 3 OF 3'}</Text>
            <Text style={T.title}>You're live. Now add your card.</Text>
            <Text style={[T.dim, { marginTop: 8 }]}>Your portfolio is at this link. Anyone can open it, no login needed.</Text>
            <View style={[T.card, { marginTop: 20 }]}>
              <Text selectable style={{ color: C.link, fontSize: 17, fontWeight: '600' }}>{published.url}</Text>
            </View>
            <View style={T.row}>
              <Button label="Add to Apple Wallet" onPress={() => Linking.openURL(`${published.url}/pass.pkpass`)} />
              <Button label="View site" kind="secondary" onPress={() => Linking.openURL(published.url)} />
              <Button label="Back to dashboard" kind="ghost" onPress={onClose} />
            </View>
            <Text style={[T.dim, { marginTop: 14, fontSize: 14 }]}>
              Open this on your iPhone in Safari to add the card. On a Mac, AirDrop the downloaded card to your phone. The QR code
              keeps working after you edit, so you never need a new card.
            </Text>
          </View>
          <View style={{ flex: wide ? 1 : undefined }}>
            <WalletCard name={resume.name} headline={resume.headline} color={accent ?? TEMPLATES[template]} url={published.url} />
          </View>
        </View>
      </Page>
    );
  }

  const form = (
    <>
      <Text style={T.overline}>{draft.slug ? 'EDIT' : 'STEP 2 OF 3'}</Text>
      <Text style={T.title}>{draft.slug ? 'Edit your portfolio' : 'Check your details'}</Text>
      <Text style={T.dim}>Fix anything we read wrong. The preview updates as you type.</Text>

      <Text style={T.h2}>Your link</Text>
      <Field
        label="devoppers.vercel.app/"
        value={slug}
        onChangeText={(v) => setSlug(slugify(v))}
        editable={!draft.slug}
        placeholder="your-name"
      />

      <Text style={T.h2}>About you</Text>
      <Field label="Full name" value={resume.name} onChangeText={(name) => { set({ name }); if (!draft.slug) setSlug(slugify(name)); }} autoCapitalize="words" />
      <Field label="Headline" value={resume.headline} onChangeText={(headline) => set({ headline })} placeholder="Software Engineering Student" autoCapitalize="sentences" />
      <Field label="Email" value={resume.email} onChangeText={(email) => set({ email })} keyboardType="email-address" />
      <Field label="Phone" value={resume.phone} onChangeText={(phone) => set({ phone })} keyboardType="phone-pad" />
      <Field label="Location" value={resume.location} onChangeText={(location) => set({ location })} autoCapitalize="words" />
      <Field label="Summary" value={resume.summary} onChangeText={(summary) => set({ summary })} multiline autoCapitalize="sentences" />
      <Field label="Skills (comma separated)" value={resume.skills} onChangeText={(skills) => set({ skills })} placeholder="Python, React, SQL" />
      <Text style={T.label}>Hide from your public page</Text>
      <View style={T.row}>
        {HIDEABLE.map(([field, label]) => {
          const hidden = resume.hidden.includes(field);
          return <Chip key={field} label={hidden ? `${label} hidden` : label} on={hidden} onPress={() => set({ hidden: hidden ? resume.hidden.filter((h) => h !== field) : [...resume.hidden, field] })} />;
        })}
      </View>

      {entries('experience', 'Experience', 'Company')}
      {entries('education', 'Education', 'School')}

      <Text style={T.h2}>Design</Text>
      <View style={T.row}>
        {Object.keys(TEMPLATES).map((t) => <Chip key={t} label={t[0].toUpperCase() + t.slice(1)} on={t === template} onPress={() => { setTemplate(t); setAccent(undefined); }} />)}
      </View>
      <Text style={[T.label, { marginTop: 16 }]}>Accent color</Text>
      <View style={T.row}>
        {ACCENTS.map((color) => (
          <Pressable
            key={color}
            accessibilityRole="button"
            accessibilityLabel={`Accent ${color}`}
            onPress={() => setAccent(color)}
            style={{ width: 36, height: 36, borderRadius: 18, backgroundColor: color, borderWidth: 3, borderColor: color === accent ? C.text : C.bg }}
          />
        ))}
      </View>
      {!!error && <Text style={T.error}>{error}</Text>}
    </>
  );

  const preview = html ? <Preview html={html} height={wide ? height - 140 : 560} /> : <Text style={T.dim}>Add your name to see a preview.</Text>;

  return (
    <Page
      left={<Back label="Dashboard" onPress={onClose} />}
      right={<Button small label={draft.slug ? 'Save changes' : 'Publish'} onPress={publish} loading={saving} />}
      width={1280}
    >
      {wide ? (
        <View style={{ flexDirection: 'row', gap: 40, alignItems: 'flex-start' }}>
          <View style={{ flex: 5 }}>{form}</View>
          <View style={{ flex: 6, position: 'sticky' as any, top: 0 }}>{preview}</View>
        </View>
      ) : (
        <>
          {form}
          <Text style={T.h2}>Preview</Text>
          {preview}
          <Button label={draft.slug ? 'Save changes' : 'Publish'} onPress={publish} loading={saving} style={{ marginTop: 20 }} />
        </>
      )}
    </Page>
  );
}
