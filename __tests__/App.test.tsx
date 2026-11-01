/**
 * @format
 */

import React from 'react';
import ReactTestRenderer from 'react-test-renderer';
import App from '../App';
import { AuthProvider } from '../src/auth/AuthContext';

test('renders correctly', async () => {
  await ReactTestRenderer.act(() => {
    ReactTestRenderer.create(
      <AuthProvider>
        <App />
      </AuthProvider>,
    );
  });
});
