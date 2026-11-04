/**
 * @format
 */

import { registerRootComponent } from 'expo';
import { AuthProvider } from './src/auth/AuthContext';
import App from './App';

function Root() {
    return (
        <AuthProvider>
            <App />
        </AuthProvider>
    );
}

registerRootComponent(Root);
