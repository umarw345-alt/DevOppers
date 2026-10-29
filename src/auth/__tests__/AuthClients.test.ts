import { login, logout, refresh, register } from '../AuthClients';

describe('authentication client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('sends registration credentials and returns the auth response', async () => {
    const response = {
      user: { id: 'user-1', email: 'user@example.com' },
      access_token: 'access-token',
      refresh_token: 'refresh-token',
    };
    globalThis.fetch = jest.fn().mockResolvedValue({ ok: true, status: 201, json: async () => response }) as jest.Mock;

    await expect(register('user@example.com', 'password123')).resolves.toEqual(response);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://10.0.2.2:8080/v1/auth/register',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ email: 'user@example.com', password: 'password123' }),
      }),
    );
  });

  it('surfaces invalid credentials as an authentication error', async () => {
    globalThis.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Invalid email or password' }),
    }) as jest.Mock;

    await expect(login('user@example.com', 'wrongpass')).rejects.toMatchObject({
      message: 'Invalid email or password',
      kind: 'authentication',
      status: 401,
    });
  });

  it('rotates refresh tokens into the Secure Store shape', async () => {
    globalThis.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ access_token: 'new-access', refresh_token: 'new-refresh' }),
    }) as jest.Mock;

    await expect(refresh('old-refresh')).resolves.toEqual({
      accessToken: 'new-access',
      refreshToken: 'new-refresh',
    });
  });

  it('sends the access token when logging out', async () => {
    globalThis.fetch = jest.fn().mockResolvedValue({ ok: true, status: 204 }) as jest.Mock;

    await logout('access-token');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://10.0.2.2:8080/v1/auth/logout',
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer access-token' }) }),
    );
  });
});
