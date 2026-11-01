import React, { useState } from 'react';
import { Alert, FlatList, Modal, Platform, Pressable, Share, Text, View } from 'react-native';
import type { Resume } from '../api';
import { C, Pill, Screen, T } from '../theme';

export type Site = { id: string; name: string; template: string; url: string; resume?: Resume; theme?: { accent: string; font: string }; isDemo?: boolean };

export default function Menu({ sites, onAdd, onDelete }: { sites: Site[]; onAdd: () => void; onDelete: (id: string) => void }) {
  const [manage, setManage] = useState(false);
  const [sel, setSel] = useState<Site | null>(null);

  const confirmDelete = (s: Site) => Alert.alert('Delete site?', s.name, [{ text: 'Cancel', style: 'cancel' }, { text: 'Delete', style: 'destructive', onPress: () => onDelete(s.id) }]);
  const share = async () => {
    const site = sel;
    setSel(null);
    if (!site || site.isDemo || !/^https?:\/\//.test(site.url)) {
      Alert.alert('Not published yet', 'This portfolio is saved on this device. A shareable link will be available when publishing is connected.');
      return;
    }
    try { await Share.share({ message: site.url }); }
    catch { Alert.alert('Could not share', 'Please try again.'); }
  };
  const wallet = () => {
    setSel(null); // TODO: POST /passes/apple (iOS) or /passes/google (Android) once the pass service exists
    Alert.alert('Wallet', 'Wallet passes are coming soon. They need the backend pass service.');
  };

  return (
    <Screen>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text style={[T.h1, { fontSize: 26 }]}>MY PORTFOLIOS</Text>
        {sites.length > 0 && <Pill label={manage ? 'DONE' : 'MANAGE'} onPress={() => setManage(!manage)} style={{ paddingHorizontal: 16, minHeight: 36, paddingVertical: 8 }} />}
      </View>
      <FlatList
        data={sites} keyExtractor={(s) => s.id} contentContainerStyle={{ paddingTop: 22, paddingBottom: 110 }}
        ListEmptyComponent={<Text style={[T.mono, { textAlign: 'center', marginTop: 60 }]}>No sites yet. Tap + to add one.</Text>}
        renderItem={({ item }) => (
          <View style={[T.card, { flexDirection: 'row', alignItems: 'center' }]}>
            <View style={{ flex: 1 }}>
              <Text style={{ fontSize: 17, fontWeight: '600', color: C.ink }}>{item.name}</Text>
              <Text style={{ color: '#6C86AC', marginTop: 3 }}>{item.template} · {item.isDemo ? 'Local draft' : item.url}</Text>
            </View>
            {manage
              ? <Pressable onPress={() => confirmDelete(item)} hitSlop={12}><Text style={{ color: C.red, fontSize: 22 }}>✕</Text></Pressable>
              : <Pressable onPress={() => setSel(item)} hitSlop={12}><Text style={{ color: C.ink, fontSize: 26, fontWeight: '700' }}>⋯</Text></Pressable>}
          </View>
        )}
      />
      <Pressable onPress={onAdd} style={{ position: 'absolute', right: 22, bottom: 30, width: 62, height: 62, borderRadius: 31, backgroundColor: C.green, alignItems: 'center', justifyContent: 'center', elevation: 6 }}>
        <Text style={{ color: '#fff', fontSize: 36, marginTop: -2 }}>+</Text>
      </Pressable>
      <Modal transparent animationType="slide" visible={!!sel} onRequestClose={() => setSel(null)}>
        <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,.5)', justifyContent: 'flex-end' }} onPress={() => setSel(null)}>
          <View style={{ backgroundColor: '#0B1B33', padding: 20, paddingBottom: 36, borderTopLeftRadius: 20, borderTopRightRadius: 20, gap: 12 }}>
            <Text style={[T.mono, { opacity: 0.7 }]}>{sel?.name}</Text>
            <Pill label={Platform.OS === 'ios' ? 'ADD TO APPLE WALLET' : 'SAVE TO GOOGLE WALLET'} onPress={wallet} />
            <Pill label="SHARE LINK" onPress={share} />
            <Pill label="CANCEL" color="#33445F" onPress={() => setSel(null)} />
          </View>
        </Pressable>
      </Modal>
    </Screen>
  );
}
