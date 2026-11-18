import { getApiBaseUrl } from '../ApiBaseUrl';

describe('API base URL resolution', () => {
  const previousApiUrl = process.env.EXPO_PUBLIC_API_BASE_URL;

  afterEach(() => {
    if (previousApiUrl === undefined) delete process.env.EXPO_PUBLIC_API_BASE_URL;
    else process.env.EXPO_PUBLIC_API_BASE_URL = previousApiUrl;
  });

  it('uses the explicit Expo API URL when configured', () => {
    process.env.EXPO_PUBLIC_API_BASE_URL = 'http://localhost:8000/';
    expect(getApiBaseUrl()).toBe('http://localhost:8000');
  });
});
