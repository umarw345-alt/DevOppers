# Portable Resume

A student uploads a resume, checks what was read from it, and publishes it as a
portfolio website at its own link (`<site>/<name>`, e.g. `devoppers.vercel.app/jerry`).
The Apple Wallet card's QR code opens that link, so a recruiter scans it with no app
and no login. Editing the portfolio later never needs a new card.

1. Log in or create an account (email + password).
2. **Upload resume** (PDF/JPG/PNG, read by Claude) or **Start blank**.
3. Fix the details, hide your phone/email/location if you like, pick a template and color.
4. **Publish**. Your page is live at the link shown.
5. On your iPhone, tap **Add to Apple Wallet**.

## Architecture

```text
React Native / Expo
        |
FastAPI backend :8000   (auth + portfolio, backend/main.py)
        |
PostgreSQL :5432        (reachable only from this computer)
```

Native clients store raw access and refresh tokens in `expo-secure-store`. The web client does not persist tokens in JavaScript storage: FastAPI sets HttpOnly access and refresh cookies, plus a readable CSRF companion cookie. FastAPI stores Argon2id password hashes and refresh-token hashes in PostgreSQL.

## Prerequisites

- Node.js and npm
- [uv](https://docs.astral.sh/uv/) for the Python backend
- Docker Desktop with the Linux engine running
- A modern web browser for the primary web app
- Android Studio and an Android emulator for optional Android development
- Xcode and CocoaPods for optional iOS development

## Start the backend

Create a local environment file from `.env.example`, then change `POSTGRES_PASSWORD` (and the two database URLs that contain it):

```powershell
Copy-Item .env.example .env
```

Create development RS256 keys in the ignored `secrets/` directory (one time):

```powershell
New-Item -ItemType Directory -Force secrets
cd backend
uv run python -c "from cryptography.hazmat.primitives.asymmetric import rsa; from cryptography.hazmat.primitives import serialization as s; k = rsa.generate_private_key(public_exponent=65537, key_size=2048); open('../secrets/jwt-private.pem','wb').write(k.private_bytes(s.Encoding.PEM, s.PrivateFormat.PKCS8, s.NoEncryption())); open('../secrets/jwt-public.pem','wb').write(k.public_key().public_bytes(s.Encoding.PEM, s.PublicFormat.SubjectPublicKeyInfo))"
cd ..
```

Do not commit `.env`, private keys, or database data.

**Option A: everything in Docker.** Starts PostgreSQL, runs the Alembic migration job, then starts the API:

```powershell
docker compose up --build -d
docker compose ps
```

Or use the guided scripts from the project root. `start-fastapi.ps1` waits for PostgreSQL, runs `alembic upgrade head`, starts the API only after migrations succeed, and checks `http://localhost:8000/health`:

```powershell
.\scripts\start-postgres.ps1
.\scripts\start-fastapi.ps1
```

The migration container is a one-shot job. `Exited (0)` means the migration completed successfully.

**Option B: database in Docker, API with uv (auto-reloads on code changes).**

```powershell
docker compose up -d postgres migrations
cd backend
uv sync
uv run fastapi dev main.py
```

The API reads `.env` from the project root.

Verify the API:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected response:

```text
status
------
ok
```

View service logs when troubleshooting:

```powershell
docker compose logs -f api
docker compose logs -f postgres
```

Stop the backend stack:

```powershell
docker compose down
```

## Apple Wallet setup

Passes are signed with your Apple Developer **Pass Type ID** certificate. Without it
everything else works and the Wallet button answers 503.

1. In Keychain Access, export the Pass Type ID certificate *with its private key* as
   `secrets/pass.p12` (put its password in `.env` as `PASS_P12_PASSWORD`).
2. Download Apple's [WWDR G4 certificate](https://www.apple.com/certificateauthority/AppleWWDRCAG4.cer)
   as `secrets/wwdr.cer`.
3. `docker compose up -d --build api`.

The pass type and team IDs are read from the certificate. To scan the QR code from a
phone, set `PUBLIC_BASE_URL` to an address the phone can reach (your computer's LAN IP,
e.g. `http://192.168.1.20:8000`, or a real domain later) and rebuild the API.

## Deploy

One Vercel project, rooted at the repository root, serves both halves on one address:

- `main.py` (root) is the FastAPI entry point; it loads the app from `backend/`.
- `vercel.json` runs `backend/build_web.py`, which builds the Expo web app into `public/`.
  The build leaves `EXPO_PUBLIC_API_BASE_URL` empty, so the web app calls whatever address
  it was served from. The same build works on any domain.
- Postgres is a free Neon database added through the Vercel Marketplace.

Connect the Vercel project to this GitHub repository so every push to `main` deploys to
production and every pull request gets a preview URL. Don't build `public/` locally or
commit it; Vercel builds it.

- **Migrations:** run `alembic upgrade head` from `backend/` with `DATABASE_URL` set to the
  Neon `DATABASE_URL_UNPOOLED` (from `vercel env pull`). Run it when you deploy code
  that needs a new migration. Migration history starts at `backend/migrations/versions/baseline.py`,
  which keeps the old last revision's ID, so databases that ran the older migrations need nothing.
  One that stopped before `005_portfolio_schema_compat` can't upgrade and is easiest to recreate.
- **Secrets** live in Vercel env vars, never in files. Key and certificate files are passed
  base64-encoded as `JWT_PRIVATE_KEY_B64`, `JWT_PUBLIC_KEY_B64`, `PASS_P12_B64` and
  `WWDR_CERT_B64`; `main.py` writes them to temp files at startup.
- **Other env vars:** `DATABASE_URL`, `ANTHROPIC_API_KEY`, `PASS_P12_PASSWORD`, and optionally
  `DAILY_UPLOAD_CAP` (site-wide resume reads per 24 hours, default 200). Google sign-in
  needs `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OIDC_STATE_SECRET`,
  `GOOGLE_REDIRECT_URI` (`https://<site>/v1/auth/google/callback`, also registered in the
  Google Cloud console) and `GOOGLE_FRONTEND_REDIRECT_URI` (`https://<site>`). Portfolio links
  use the site's own address and cookies are Secure on Vercel automatically, so
  `PUBLIC_BASE_URL` and `WEB_COOKIE_SECURE` aren't needed. `CORS_ALLOWED_ORIGINS` is only
  needed if the web app is served from a different address than the API.
- Vercel caps request bodies at 4.5 MB, so the app accepts resumes up to 4 MB.

## Run the web app

The web client reaches the local API through `localhost`. Keep these values in `.env`:

```env
EXPO_PUBLIC_API_BASE_URL=http://localhost:8000
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

On web, register and login establish the HttpOnly cookies. Refresh, logout, and the debounced input heartbeat send the cookie automatically and include the CSRF companion token. On Android and iOS, the existing Secure Store and bearer-token behavior remains in place.

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
$env:EXPO_PUBLIC_API_BASE_URL="http://10.0.2.2:8000"
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
cd backend; uv run pytest; cd ..
```

Run the full authentication integration tests against the running Docker services:

```powershell
.\scripts\test-integration.ps1
```

These tests send real requests to FastAPI and PostgreSQL. They are opt-in because Docker Desktop and the migrated database must be running first.

## Endpoints

FastAPI serves these routes on port `8000` (interactive docs at `/docs`):

```text
POST   /v1/auth/register | login | refresh | logout | input
POST   /resume/upload             resume file -> Resume JSON (login required)
GET    /portfolio/templates
POST   /portfolio/preview         Resume + design -> HTML, not saved
GET    /portfolios                your portfolios (login required)
PUT    /portfolios/{slug}         publish or update (login required)
DELETE /portfolios/{slug}         (login required)
GET    /{slug}                    public portfolio page
GET    /{slug}/pass.pkpass        Apple Wallet pass
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

If the API cannot be reached, confirm it is running on port `8000` (`docker compose ps` or the `uv run fastapi dev` terminal) and that the Android emulator is using `10.0.2.2` rather than `localhost`.

