# Login Authenticator

A React Native and Expo mobile authentication client backed by KrakenD, FastAPI, and PostgreSQL.

## Architecture

```text
React Native / Expo
        |
KrakenD gateway :8080
        |
FastAPI authentication service :5000
        |
PostgreSQL :5432
```

The client stores only raw access and refresh tokens in `expo-secure-store`. FastAPI stores Argon2id password hashes and refresh-token hashes in PostgreSQL.

## Prerequisites

- Node.js and npm
- Docker Desktop with the Linux engine running
- A modern web browser for the primary web app
- Android Studio and an Android emulator for optional Android development
- Xcode and CocoaPods for optional iOS development

## Start the backend

Create a local environment file from `.env.example` and ensure development RS256 keys exist in the ignored `secrets/` directory:

```powershell
Copy-Item .env.example .env
```

Do not commit `.env`, private keys, or database data.

Start PostgreSQL, run the Alembic migration job, FastAPI, and KrakenD:

```powershell
docker compose up --build -d
docker compose ps
```

The migration container is a one-shot job. `Exited (0)` means the migration completed successfully.

Verify the gateway:

```powershell
Invoke-RestMethod http://localhost:8080/health
```

Expected response:

```text
status
------
ok
```

View service logs when troubleshooting:

```powershell
docker compose logs -f auth-service
docker compose logs -f krakend
```

Stop the backend stack:

```powershell
docker compose down
```

## Run the web app

The web client reaches the local gateway through `localhost`. Keep these values in `.env`:

```env
EXPO_PUBLIC_API_BASE_URL=http://localhost:8080
CORS_ALLOWED_ORIGINS=http://localhost:8081,http://127.0.0.1:8081
```

Install JavaScript dependencies:

```powershell
npm install
```

Start the Expo web development server:

```powershell
npm run web
```

Expo will open the web app in a browser. If it does not open automatically, visit the URL shown in the terminal, usually `http://localhost:8081`.

The browser origin must be listed in `CORS_ALLOWED_ORIGINS`. Do not use `*` when authentication requests are enabled.

To create a production web bundle:

```powershell
npx expo export --platform web
```

The exported files are written to `dist/` and can be served by a static web host. The deployed web origin and API URL must be configured for the deployment environment.

## Run the optional Android app

The Android emulator must be connected through ADB before launching the app:

```powershell
adb devices
```

For the Android emulator, override the browser API URL with the host-machine address:

```powershell
$env:EXPO_PUBLIC_API_BASE_URL="http://10.0.2.2:8080"
npx expo run:android --device Medium_Phone
```

Start Expo for JavaScript development and Fast Refresh:

```powershell
npx expo start --dev-client --android
```

Start Expo for JavaScript development and Fast Refresh:

```powershell
npx expo start --dev-client --android
```

Use the project emulator rather than `Fire_TV_Emulation` unless Fire TV is specifically being tested.

## Run the iOS app

Install native dependencies after the first clone or after native dependency changes:

```sh
bundle install
bundle exec pod install
```

Then build the iOS app:

```sh
npx expo run:ios
```

## Tests and validation

```powershell
node_modules\.bin\tsc.cmd --noEmit
cmd /c npm.cmd test -- --runInBand
cmd /c npm.cmd run lint
.venv\Scripts\python.exe -m pytest backend\tests -q
```

## Authentication endpoints

KrakenD forwards these routes to FastAPI:

```text
POST /v1/auth/register
POST /v1/auth/login
POST /v1/auth/refresh
POST /v1/auth/logout
POST /v1/auth/input
```

## Troubleshooting

If the Android app opens the wrong target, check connected devices:

```powershell
adb devices -l
```

If port `8081` is already in use by another Metro server, stop the old server and restart with a clean cache:

```powershell
npx expo start --clear --port 8081
```

If the gateway cannot be reached, confirm Docker Desktop is running, KrakenD is listening on port `8080`, and the Android emulator is using `10.0.2.2` rather than `localhost`.

# DevOppers
