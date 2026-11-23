import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Linking, Text, View } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import { Draft, EMPTY_RESUME, Portfolio, TEMPLATES, deletePortfolio, extractResume, listPortfolios } from '../api';
import { Button, C, Page, Steps, T, WalletButtons, useWide } from '../theme';

const READING = ['Reading your resume…', 'Finding your experience…', 'Organizing your skills…', 'Almost done…'];
const initials = (name: string) => name.split(/\s+/).map((word) => word[0]).join('').slice(0, 2).toUpperCase();
const blank: Draft = { resume: EMPTY_RESUME, template_id: 'modern', theme: {} };

type Props = { token: string | null; email?: string; onOpen: (draft: Draft) => void; onLogout: () => void };

export default function Home({ token, email, onOpen, onLogout }: Props) {
  const wide = useWide();
  const [portfolios, setPortfolios] = useState<Portfolio[] | null>(null);
  const [error, setError] = useState('');
  const [reading, setReading] = useState(-1); // index into READING while Claude reads the file
  const [confirmDelete, setConfirmDelete] = useState('');

  useEffect(() => {
    listPortfolios(token).then(setPortfolios).catch((e) => { setPortfolios([]); setError(e.message); });
  }, [token]);

  const busy = reading >= 0;
  useEffect(() => {
    if (!busy) return;
    const timer = setInterval(() => setReading((i) => Math.min(i + 1, READING.length - 1)), 2500);
    return () => clearInterval(timer);
  }, [busy]);

  const upload = async () => {
    setError('');
    const picked = await DocumentPicker.getDocumentAsync({ type: ['application/pdf', 'image/jpeg', 'image/png'] });
    const file = picked.assets?.[0];
    if (picked.canceled || !file) return;
    if (file.size && file.size > 4 * 1024 * 1024) return setError('That file is over 4 MB. Try a smaller PDF or a photo.');
    setReading(0);
    try {
      onOpen({ ...blank, resume: await extractResume(file, token) });
    } catch (e: any) {
      setError(`${e.message} You can also type it in with "Start blank".`);
    } finally {
      setReading(-1);
    }
  };

  const remove = async (slug: string) => {
    if (confirmDelete !== slug) return setConfirmDelete(slug); // first tap arms, second tap deletes
    try {
      await deletePortfolio(token, slug);
      setPortfolios((list) => list!.filter((p) => p.slug !== slug));
    } catch (e: any) {
      setError(e.message);
    }
    setConfirmDelete('');
  };

  const actions = busy ? (
    <View style={[T.card, T.row, { marginTop: 20 }]}>
      <ActivityIndicator color={C.link} />
      <Text style={T.body}>{READING[reading]}</Text>
    </View>
  ) : (
    <View style={[T.row, { marginTop: 20 }]}>
      <Button label="Upload resume" onPress={upload} />
      <Button label="Start blank" kind="secondary" onPress={() => onOpen(blank)} />
    </View>
  );

  return (
    <Page
      right={<>
        {wide && !!email && <Text style={[T.dim, { fontSize: 14 }]}>{email}</Text>}
        <Button label="Log out" kind="secondary" small onPress={onLogout} />
      </>}
    >
      {portfolios === null && <ActivityIndicator color={C.link} />}

      {portfolios?.length === 0 && (
        <>
          <Text style={T.title}>Let's make your card</Text>
          <Text style={[T.dim, { marginBottom: 24 }]}>Three steps, about a minute.</Text>
          <Steps active={0} />
          {actions}
          <Text style={[T.dim, { marginTop: 12, fontSize: 14 }]}>PDF, JPG or PNG, up to 4 MB. No resume handy? Start blank and type it in.</Text>
        </>
      )}

      {!!portfolios?.length && (
        <>
          <View style={{ flexDirection: wide ? 'row' : 'column', justifyContent: 'space-between', alignItems: wide ? 'flex-end' : 'flex-start', gap: 4 }}>
            <View>
              <Text style={T.overline}>DASHBOARD</Text>
              <Text style={T.title}>Your portfolios</Text>
              <Text style={T.dim}>Share the link, or add the card to Apple Wallet or Google Wallet for career fairs.</Text>
            </View>
            {actions}
          </View>
          <View style={{ flexDirection: wide ? 'row' : 'column', flexWrap: 'wrap', gap: 16, marginTop: 32 }}>
            {portfolios.map((p) => (
              <View key={p.slug} style={[T.card, { marginBottom: 0, padding: 0, overflow: 'hidden', flexBasis: wide ? '48%' : 'auto', flexGrow: wide ? 0 : 1 }]}>
                <View style={{ height: 64, backgroundColor: p.theme.accent ?? TEMPLATES[p.template_id] }} />
                <View style={{ padding: 22, paddingTop: 0, gap: 6 }}>
                  <View style={{ width: 52, height: 52, borderRadius: 14, marginTop: -26, backgroundColor: C.card, borderWidth: 1, borderColor: C.line, alignItems: 'center', justifyContent: 'center' }}>
                    <Text style={{ color: C.text, fontWeight: '700', fontSize: 17 }}>{initials(p.resume.name)}</Text>
                  </View>
                  <Text style={[T.body, { fontSize: 18, fontWeight: '700', marginTop: 6 }]}>{p.resume.name}</Text>
                  {!!p.resume.headline && <Text style={T.dim}>{p.resume.headline}</Text>}
                  <Text selectable style={{ color: C.link, fontSize: 14 }}>{p.url}</Text>
                  <View style={[T.row, { marginTop: 10 }]}>
                    <WalletButtons small url={p.url} />
                    <Button small kind="secondary" label="View site" onPress={() => Linking.openURL(p.url)} />
                    <Button small kind="secondary" label="Edit" onPress={() => onOpen(p)} />
                    <Button small kind="ghost" label={confirmDelete === p.slug ? 'Tap again to delete' : 'Delete'} onPress={() => remove(p.slug)} />
                  </View>
                </View>
              </View>
            ))}
          </View>
        </>
      )}

      {!!error && <Text style={T.error}>{error}</Text>}
    </Page>
  );
}
