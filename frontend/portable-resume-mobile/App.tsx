import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Alert, Text } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import Landing from './src/screens/Landing';
import Menu, { Site } from './src/screens/Menu';
import AddResume from './src/screens/AddResume';
import Template from './src/screens/Template';
import { Resume, clearSession } from './src/api';
import { loadSites, saveSites } from './src/storage';
import { Pill, Screen, T } from './src/theme';

const EXAMPLES: Site[] = [
  { id: '1', name: 'Jordan Lee', template: 'modern', url: '', isDemo: true },
  { id: '2', name: 'Capstone Project Site', template: 'minimal', url: '', isDemo: true },
  { id: '3', name: 'Career Fair Page', template: 'dark', url: '', isDemo: true },
];

export default function App() {
  return <SafeAreaProvider><Content /></SafeAreaProvider>;
}
function Content() {
  const [screen, setScreen] = useState<'landing' | 'menu' | 'add' | 'template'>('landing');
  const [sites, setSites] = useState<Site[]>([]);
  const [resume, setResume] = useState<Resume | null>(null);
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [retry, setRetry] = useState(0);
  const currentSites = useRef<Site[]>([]);
  const writes = useRef<Promise<void>>(Promise.resolve());

  useEffect(() => {
    let live = true;
    setLoadError(false);
    loadSites(EXAMPLES).then((saved) => {
      if (live) { currentSites.current = saved; setSites(saved); setReady(true); }
    }).catch(() => { if (live) setLoadError(true); });
    return () => { live = false; };
  }, [retry]);

  // Serialize writes and update the list only after the device confirms saving.
  const updateSites = (change: (previous: Site[]) => Site[]): Promise<void> => {
    const next = writes.current.then(async () => {
      const updated = change(currentSites.current);
      await saveSites(updated);
      currentSites.current = updated;
      setSites(updated);
    });
    writes.current = next.catch(() => {});
    return next;
  };

  if (!ready) return <Screen>{loadError ? <>
    <Text style={T.h2}>Could not load saved portfolios. Please try again.</Text>
    <Pill label="RETRY" onPress={() => setRetry((n) => n + 1)} />
  </> : <ActivityIndicator color="#fff" size="large" />}</Screen>;
  if (screen === 'landing') return <Landing onDone={() => setScreen('menu')} />;
  if (screen === 'add') return <AddResume initialResume={resume} onBack={(r) => { setResume(r); setScreen('menu'); }} onContinue={(r) => { setResume(r); setScreen('template'); }} />;
  if (screen === 'template' && resume) return <Template resume={resume} onBack={() => setScreen('add')} onDone={async (s) => {
    await updateSites((previous) => [s, ...previous]);
    setResume(null); setScreen('menu');
  }} />;
  return <Menu sites={sites} onBack={() => { clearSession(); setResume(null); setScreen('landing'); }} onAdd={() => setScreen('add')} onDelete={(id) => {
    updateSites((previous) => previous.filter((s) => s.id !== id)).catch(() => Alert.alert('Could not delete', 'Your portfolios were kept. Please try again.'));
  }} />;
}
