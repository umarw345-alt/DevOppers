import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Alert, Text, View } from 'react-native';

import AddResume from '../../frontend/portable-resume-mobile/src/screens/AddResume';
import Menu, { Site } from '../../frontend/portable-resume-mobile/src/screens/Menu';
import Template from '../../frontend/portable-resume-mobile/src/screens/Template';
import { Resume } from '../../frontend/portable-resume-mobile/src/api';
import { loadSites, saveSites } from '../../frontend/portable-resume-mobile/src/storage';
import { Pill, Screen, T } from '../../frontend/portable-resume-mobile/src/theme';

const EXAMPLES: Site[] = [
  { id: '1', name: 'Jordan Lee', template: 'modern', url: '', isDemo: true },
  { id: '2', name: 'Capstone Project Site', template: 'minimal', url: '', isDemo: true },
  { id: '3', name: 'Career Fair Page', template: 'dark', url: '', isDemo: true },
];

type PortfolioHomeScreenProps = { onLogout: () => Promise<void>; onInput: () => void };

export default function PortfolioHomeScreen({ onLogout, onInput }: PortfolioHomeScreenProps) {
  const [screen, setScreen] = useState<'menu' | 'add' | 'template'>('menu');
  const [sites, setSites] = useState<Site[]>([]);
  const [resume, setResume] = useState<Resume | null>(null);
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [retry, setRetry] = useState(0);
  const currentSites = useRef<Site[]>([]);
  const writes = useRef<Promise<void>>(Promise.resolve());
  const activityTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let live = true;
    setLoadError(false);
    loadSites(EXAMPLES).then((saved) => {
      if (live) { currentSites.current = saved; setSites(saved); setReady(true); }
    }).catch(() => { if (live) setLoadError(true); });
    return () => { live = false; };
  }, [retry]);

  const resetActivityTimer = useCallback(() => {
    if (activityTimer.current) clearTimeout(activityTimer.current);
    activityTimer.current = setTimeout(() => { Promise.resolve(onInput()).catch(() => undefined); }, 3 * 60 * 1000);
  }, [onInput]);

  useEffect(() => {
    resetActivityTimer();
    return () => { if (activityTimer.current) clearTimeout(activityTimer.current); };
  }, [resetActivityTimer]);

  const updateSites = (change: (previous: Site[]) => Site[]): Promise<void> => {
    const next = writes.current.then(async () => {
      const updated = change(currentSites.current);
      await saveSites(updated);
      currentSites.current = updated;
      setSites(updated);
    });
    writes.current = next.catch(() => undefined);
    return next;
  };

  if (!ready) return <Screen>{loadError ? <>
    <Text style={T.h2}>Could not load saved portfolios. Please try again.</Text>
    <Pill label="RETRY" onPress={() => setRetry((n) => n + 1)} />
  </> : <ActivityIndicator color="#fff" size="large" />}</Screen>;
  if (screen === 'add') return <AddResume initialResume={resume} onBack={(r) => { setResume(r); setScreen('menu'); }} onContinue={(r) => { setResume(r); setScreen('template'); }} />;
  if (screen === 'template' && resume) return <Template resume={resume} onBack={() => setScreen('add')} onDone={async (site) => {
    await updateSites((previous) => [site, ...previous]);
    setResume(null); setScreen('menu');
  }} />;
  return <View onTouchStart={resetActivityTimer} style={{ flex: 1 }}>
    <Menu sites={sites} onBack={() => { onLogout().catch(() => undefined); }} onAdd={() => setScreen('add')} onDelete={(id) => {
      updateSites((previous) => previous.filter((site) => site.id !== id)).catch(() => Alert.alert('Could not delete', 'Your portfolios were kept. Please try again.'));
    }} />
  </View>;
}
