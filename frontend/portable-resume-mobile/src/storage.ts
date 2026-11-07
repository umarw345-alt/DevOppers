import AsyncStorage from '@react-native-async-storage/async-storage';
import type { Site } from './screens/Menu';

const KEY = 'portable-resume:sites:v1';
export async function loadSites(defaults: Site[]): Promise<Site[]> {
  const raw = await AsyncStorage.getItem(KEY);
  if (raw === null) return defaults;
  const data: unknown = JSON.parse(raw);
  if (!Array.isArray(data) || !data.every((s) => s && typeof s.id === 'string' && typeof s.name === 'string' && typeof s.template === 'string' && typeof s.url === 'string')) {
    throw new Error('Saved portfolio data could not be read.');
  }
  return data as Site[];
}
export async function saveSites(sites: Site[]): Promise<void> {
  await AsyncStorage.setItem(KEY, JSON.stringify(sites));
}
