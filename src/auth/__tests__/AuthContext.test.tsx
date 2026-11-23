import React from 'react';
import ReactTestRenderer from 'react-test-renderer';

import { AuthProvider, useAuth } from '../AuthContext';
import { getItemAsync } from 'expo-secure-store';

type Auth = ReturnType<typeof useAuth>;

function Probe({ onRender }: { onRender: (auth: Auth) => void }) {
  onRender(useAuth());
  return null;
}

const refreshCalls = () =>
  (globalThis.fetch as jest.Mock).mock.calls.filter(([url]) => String(url).endsWith('/v1/auth/refresh')).length;

describe('AuthProvider session renewal', () => {
  let latest: Auth;

  beforeEach(() => {
    jest.useFakeTimers();
    // A phone with saved tokens, so the provider starts signed in.
    (getItemAsync as jest.Mock).mockResolvedValue('stored-token');
    globalThis.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ access_token: 'a2', refresh_token: 'r2' }),
    }) as jest.Mock;
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  async function renderSignedIn() {
    await ReactTestRenderer.act(async () => {
      ReactTestRenderer.create(
        <AuthProvider>
          <Probe onRender={(auth) => { latest = auth; }} />
        </AuthProvider>,
      );
    });
    expect(latest.status).toBe('signed_in');
  }

  it('renews the session before the 15-minute access token runs out', async () => {
    await renderSignedIn();
    expect(refreshCalls()).toBe(1);

    await ReactTestRenderer.act(async () => {
      jest.advanceTimersByTime(10 * 60 * 1000);
    });

    expect(refreshCalls()).toBe(2);
    expect(latest.status).toBe('signed_in');
  });

  it('stays signed in when a renewal hits a network error', async () => {
    await renderSignedIn();
    (globalThis.fetch as jest.Mock).mockRejectedValueOnce(new TypeError('Network request failed'));

    await ReactTestRenderer.act(async () => {
      jest.advanceTimersByTime(10 * 60 * 1000);
    });

    expect(latest.status).toBe('signed_in');
  });

  it('signs out when the server says the session ended', async () => {
    await renderSignedIn();
    (globalThis.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Session expired' }),
    });

    await ReactTestRenderer.act(async () => {
      jest.advanceTimersByTime(10 * 60 * 1000);
    });

    expect(latest.status).toBe('signed_out');
  });
});
