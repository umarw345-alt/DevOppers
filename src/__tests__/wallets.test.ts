import { Platform } from 'react-native';

import { wallets } from '../theme';

const original = Platform.OS;
const nav = globalThis as { navigator?: { userAgent?: string } };
const originalNavigator = nav.navigator;

function as(os: string, userAgent = '') {
  Object.defineProperty(Platform, 'OS', { value: os, configurable: true });
  Object.defineProperty(globalThis, 'navigator', { value: { userAgent }, configurable: true });
}

afterEach(() => {
  Object.defineProperty(Platform, 'OS', { value: original, configurable: true });
  Object.defineProperty(globalThis, 'navigator', { value: originalNavigator, configurable: true });
});

test('phone apps offer their own wallet', () => {
  as('ios');
  expect(wallets()).toEqual(['apple']);
  as('android');
  expect(wallets()).toEqual(['google']);
});

test('the web offers the wallet that matches the device', () => {
  as('web', 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)');
  expect(wallets()).toEqual(['apple']);
  as('web', 'Mozilla/5.0 (Linux; Android 15; Pixel 9)');
  expect(wallets()).toEqual(['google']);
  as('web', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)');
  expect(wallets()).toEqual(['apple', 'google']);
});
