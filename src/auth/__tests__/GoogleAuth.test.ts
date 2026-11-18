import { getGoogleSignInUrl, startGoogleSignIn } from '../GoogleAuth';

describe('Google sign-in navigation', () => {
  const previousApiUrl = process.env.EXPO_PUBLIC_API_BASE_URL;

  beforeEach(() => {
    process.env.EXPO_PUBLIC_API_BASE_URL = 'http://localhost:8000';
  });

  afterEach(() => {
    if (previousApiUrl === undefined) delete process.env.EXPO_PUBLIC_API_BASE_URL;
    else process.env.EXPO_PUBLIC_API_BASE_URL = previousApiUrl;
  });

  it('builds the server-side OIDC start URL', () => {
    expect(getGoogleSignInUrl()).toBe('http://localhost:8000/v1/auth/google/start');
  });

  it('navigates to FastAPI without exposing a token to the client', () => {
    const navigate = jest.fn();

    startGoogleSignIn(navigate);

    expect(navigate).toHaveBeenCalledWith('http://localhost:8000/v1/auth/google/start');
    expect(navigate).not.toHaveBeenCalledWith(expect.stringContaining('token='));
  });
});
