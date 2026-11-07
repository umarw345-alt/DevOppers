# Portable Resume — corrected copy

This is a complete Expo project based on the original seven source files. The screen designs are retained. Dependency versions and a package lock are included so installation is repeatable.

## Run on Windows

1. Extract this zip. You can put its `portable-resume-mobile-fixed` folder inside your existing `DevOppers/frontend` folder, alongside any existing app.
2. Open the extracted folder in VS Code. In its terminal (the folder containing `package.json`), run:

```powershell
npm ci
npx expo start
```

3. Open a compatible Expo Go on your phone, keep the phone and computer on the same Wi-Fi, and scan the QR code. On iPhone, scan using Camera; on Android, use Expo Go.
4. Tap LOGIN/SIGN UP, then Skip (demo mode).

This project uses Expo SDK 58. Your Expo Go must support SDK 58. If it reports an SDK mismatch, capture the exact error before changing dependency versions. Tested with Node 24.22.1 and npm 11.9.0; dependency installation needs internet access.

You do not need to run create-expo-app first. Keep the original folder as a backup. Do not copy node_modules from another project.

## What changed

- Back from Templates restores your edited resume; returning to the menu also keeps the unsaved editor draft during that app session.
- Android hardware Back follows the editor/template navigation.
- Added/deleted portfolios survive app restarts. Resume content, accent and font are saved along with the local portfolio record.
- Storage operations are serialized. A failed save keeps the editor open for retry. A failed delete keeps the list. Unreadable saved data is not silently overwritten.
- File picker errors are caught. Concurrent picks are blocked; canceling or failing a replacement upload preserves existing text.
- Login requires an access token. Registration that succeeds without a token returns to login.
- Templates are validated, deduplicated, and fall back to defaults on HTTP errors or bad responses.
- Preview changes clear old content, reject empty responses, and ignore obsolete responses.
- API requests time out after 15 seconds. Authenticated template/preview requests carry the bearer token.
- Removed incompatible StatusBar properties; added safe-area padding and wrapping color/font controls.
- Share explains that local drafts are unpublished instead of sharing fake URLs.

## Connect the backends later

Copy `.env.example` to `.env` and replace both addresses with your computer's LAN IP and actual service ports:

```dotenv
EXPO_PUBLIC_AUTH_URL=http://192.168.1.100:8080
EXPO_PUBLIC_API_URL=http://192.168.1.100:8000
```

The addresses above are examples. On a physical phone, localhost refers to the phone. The servers must listen on a network-accessible interface and your firewall must allow the relevant ports. Restart Expo after configuring the file.

The original endpoint assumptions remain: `/v1/auth/login`, `/v1/auth/register`, `/resume/upload`, `/portfolio/templates`, and `/portfolio/preview`. They have not been verified against your teammates' backend code. Check request/response schemas before enabling real uploads. `USE_SAMPLE_DATA` in `src/api.ts` stays `true` until that integration is ready.

## Current limits

- Selecting a file loads an example resume; it does not extract the actual file yet. The screen labels this clearly.
- Preview requires the portfolio backend; offline demo editing and local saving still work.
- Portfolios are local device drafts, not published websites. Cloud sync, reopening saved portfolios for editing, Wallet passes, AI generation, and project editing remain unfinished.
- Local saved portfolios use AsyncStorage, which is not encrypted or separated by login account. They contain the resume details entered. This is a prototype for a single device/user, not a production account storage system.
- Login tokens stay in memory and are cleared on restart. Secure persistent login is not implemented.
- Unsaved editor text survives navigation during a session, but only portfolios saved with ADD TO MY LIST survive a full restart.
- Web/browser support is not configured; this package targets Android and iOS.

## Verification

```powershell
npm run typecheck
npm test
npx expo export --platform all --output-dir dist
```

The regression tests mock native APIs, device storage and server responses. They check navigation, data persistence, failure paths and API handling; they do not verify native rendering or real backend integration. React's test renderer prints a deprecation notice, which does not indicate a failed test.

See TEST_RESULTS.md for the checks completed on the delivered version.
