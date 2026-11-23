# Google Wallet setup

The app can add a student's portfolio card to **Google Wallet** (Android), next to the
existing Apple Wallet card (iPhone). The code is done; this guide covers the one-time
account setup it needs. Plan on about 30 minutes.

Google Wallet cards are **free** to issue: no developer fee, no per-card charge. If a
console ever asks you to add billing, stop and check before going further.

## How it works

1. A student taps **Add to Google Wallet** in the app. That opens
   `https://<site>/<name>/google-wallet` on our server.
2. The server builds the card (name, title, accent color, and a QR code that opens the
   portfolio) and signs it with a Google Cloud **service-account key**.
3. The server redirects to `https://pay.google.com/gp/v/save/<signed card>`, where Google
   shows "Add to Google Wallet". Our server never calls Google's API itself.

Until the two settings below exist, the button answers **503 "Google Wallet isn't set up
on this server."** and everything else keeps working.

| Setting | What it is |
| --- | --- |
| `GOOGLE_WALLET_ISSUER_ID` | The issuer ID from the Google Pay & Wallet Console (a long number). |
| `GOOGLE_WALLET_KEY_PATH` (local) or `GOOGLE_WALLET_KEY_B64` (Vercel) | The service account's JSON key, as a file path or base64 text. |

Code: `backend/portfolio/google_wallet.py` (builds and signs the card) and the
`/{slug}/google-wallet` route in `backend/portfolio/routes.py`.

## Before you start

- Use a **personal Gmail account**. School and work Google accounts often block
  downloading service-account keys (an organization policy), and you'd get stuck at step 2.
- Use the **same** Google account in both consoles below.
- The menu names come from Google's docs and may have moved slightly.

## 1. Create the issuer account (about 10 minutes)

1. Go to the [Google Pay & Wallet Console](https://pay.google.com/business/console) and sign in.
2. Create a business profile. For a class project, a business name like
   **Portable Resume** is enough.
3. In the left menu, open **Google Wallet API** and accept the terms.
4. Copy the **Issuer ID** shown on that page. This is `GOOGLE_WALLET_ISSUER_ID`.

## 2. Create a service account and its key (about 10 minutes)

1. Go to the [Google Cloud console](https://console.cloud.google.com/) and create a new
   project, e.g. `portable-resume-wallet`.
2. Open **APIs & Services → Library**, search for **Google Wallet API**, and click **Enable**.
3. Open **IAM & Admin → Service Accounts → Create service account**. Name it e.g.
   `wallet-issuer`. Skip the optional role and access steps.
4. Open the new service account, go to **Keys → Add key → Create new key → JSON**.
   A `.json` file downloads.
5. Save it in the repo as **`secrets/google-wallet.json`**. The `secrets/` folder is
   git-ignored. Never commit this file, paste it in chat, or share it: anyone with it
   can issue cards as us.
6. Copy the service account's email. It ends in `.iam.gserviceaccount.com` and is the
   `client_email` value inside the JSON.

## 3. Let the service account issue cards

1. Back in the [Google Pay & Wallet Console](https://pay.google.com/business/console),
   open **Users**.
2. Invite the service account's email from step 2.6 with the **Developer** role.

## 4. Add the demo phones as testers

New issuer accounts start in **demo mode**:

- Only the issuer account's own users and **test accounts** can save cards.
- Every card's title shows **[TEST ONLY]**.

In the Wallet Console, under **Google Wallet API**, add the Google account signed in on
every Android phone you'll demo with as a test account. For a class demo that's all you
need. To let anyone save cards, see "Going public" below.

## 5. Try it locally

1. Add these lines to the repo's `.env` (copy `.env.example` first if you have no `.env`):

   ```env
   GOOGLE_WALLET_ISSUER_ID=<issuer ID from step 1>
   GOOGLE_WALLET_KEY_PATH=../secrets/google-wallet.json
   ```

2. Restart the API (`docker compose up -d --build api`, or restart `uv run fastapi dev main.py`).
3. Publish a portfolio, then open `http://localhost:8000/<name>/google-wallet` in a browser
   signed in to a tester account. You should land on Google's "Add to Google Wallet" page.
   - The logo is left off locally, because Google can only download it over HTTPS.
   - To try it on the phone itself, set `PUBLIC_BASE_URL` to your computer's LAN address
     (e.g. `http://192.168.1.20:8000`) so the QR code works from the phone.

## 6. Turn it on in Vercel

1. Turn the key file into a single line of text. In PowerShell, from the repo root:

   ```powershell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("secrets\google-wallet.json")) | Set-Clipboard
   ```

   (macOS/Linux: `base64 -i secrets/google-wallet.json | tr -d '\n' | pbcopy`)

2. In the Vercel project, open **Settings → Environment Variables** and add, for Production
   (and Preview if you want it on preview deployments too):
   - `GOOGLE_WALLET_KEY_B64`: paste the copied text.
   - `GOOGLE_WALLET_ISSUER_ID`: the issuer ID.
3. Redeploy. `main.py` writes the key to a temporary file at startup, the same way it
   handles the Apple certificates.
4. Check it: on an Android phone signed in to a tester account, publish a portfolio and
   tap **Add to Google Wallet**. The card should show the name, title, accent color,
   logo and QR code, and scanning the QR code should open the portfolio.

## Troubleshooting

| What you see | Likely cause |
| --- | --- |
| 503 "Google Wallet isn't set up" | `GOOGLE_WALLET_ISSUER_ID` or the key is missing, or the key file isn't valid JSON. On Vercel, redeploy after adding variables. |
| Google's page says something went wrong, or that you can't save the card | The service account wasn't invited as **Developer** (step 3), or the phone's Google account isn't a tester (step 4). |
| Google says the issuer or class is invalid | The issuer ID doesn't match the console the service account was invited to. |
| Card has no logo | Expected on `localhost`. On Vercel, check that `https://<site>/google-wallet-logo.png` opens. |
| Card shows an old name or color | A saved card keeps what it had when saved. Remove it from Google Wallet and add it again. The QR code always opens the current page. |

If Google's page shows an error message, it usually says exactly what's wrong.

## Going public (optional)

To let anyone save cards, without the **[TEST ONLY]** label, click **Request publishing
access** in the Wallet Console under **Google Wallet API**. Google needs a complete
business profile and at least one card template (Google calls it a "class"; ours is
created the first time anyone saves a card). Google reviews the request; there's no
published turnaround time. It isn't needed for the class demo.

## Known limits

- The logo is the small 58×58 Apple pass icon (`backend/portfolio/pass_icon.png`).
  Google recommends 660×660, so it may look soft until someone makes a bigger one.
- Saved cards don't update when the portfolio's name or color changes (see Troubleshooting).
