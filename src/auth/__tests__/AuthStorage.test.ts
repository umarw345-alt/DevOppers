import * as SecureStore from 'expo-secure-store';
import { clearTokens, getTokens, saveTokens } from '../AuthStorage';

jest.mock('expo-secure-store', () => ({
  setItemAsync: jest.fn(),
  getItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

describe('secure authentication storage', () => {
  beforeEach(() => jest.clearAllMocks());

  it('stores and retrieves only the raw client tokens', async () => {
    jest.mocked(SecureStore.getItemAsync)
      .mockResolvedValueOnce('access-token')
      .mockResolvedValueOnce('refresh-token');

    await saveTokens({ accessToken: 'access-token', refreshToken: 'refresh-token' });
    await expect(getTokens()).resolves.toEqual({ accessToken: 'access-token', refreshToken: 'refresh-token' });
    expect(SecureStore.setItemAsync).toHaveBeenCalledTimes(2);
  });

  it('deletes both tokens during logout cleanup', async () => {
    await clearTokens();
    expect(SecureStore.deleteItemAsync).toHaveBeenNthCalledWith(1, 'auth.access_token');
    expect(SecureStore.deleteItemAsync).toHaveBeenNthCalledWith(2, 'auth.refresh_token');
  });
});
