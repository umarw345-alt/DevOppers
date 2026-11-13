# Wallet Pass Architecture

## Purpose

This feature lets an authenticated user turn a published portfolio website into
a wallet card. The card contains a QR code that opens the portfolio's public
static-site URL.

The wallet feature does not publish the portfolio. The portfolio publishing
system owns the artifact and its public URL; the wallet system consumes that
published result.

## Important provider difference

Apple Wallet and Google Wallet do not use the same pass format:

- Apple Wallet receives a signed `.pkpass` package. The server creates a
  `pass.json`, barcode data, assets, a manifest, and an Apple certificate
  signature.
- Google Wallet receives a signed JWT that contains a Google Generic Class and
  Generic Object. The server returns an Add to Google Wallet URL.

The phrase "signed wallet token" therefore means a Google Wallet issuance JWT,
not the application's login JWT. Neither wallet artifact replaces the
application's access or refresh-token system.

## End-to-end flow

```text
Portfolio editor
      |
      | publish
      v
Portfolio publishing service
      |
      | public_url + artifact_version
      v
POST /v1/wallet/passes/{platform}
      |
      | authenticate user and verify portfolio ownership
      v
Wallet service
      |
      | canonical QR value = public portfolio URL
      |
      +--> Apple provider --> signed .pkpass bytes
      |
      +--> Google provider --> signed Add-to-Google-Wallet URL
      v
React Native / web client
      |
      +--> download/open Apple pass
      +--> open Google Wallet save link
      v
Apple Wallet or Google Wallet
```

## Portfolio link contract

The wallet service requires a published portfolio artifact with:

- `portfolio_id`
- `public_url`
- immutable `artifact_version`
- an ownership relationship to the authenticated user

If the portfolio has not been published, the endpoint returns `409` rather
than creating a card with a temporary or private URL.

The QR value should be a stable public URL, for example:

```text
https://portfolio.example.com/p/jane-doe
```

It must not contain access tokens, refresh tokens, database credentials, or
private profile data. A short redirect URL may be used later if link rotation
or analytics is required.

## Database record

`wallet_passes` records issuance metadata:

- `id`
- `user_id`
- `portfolio_id`
- `platform` (`apple` or `google`)
- `provider_object_id`
- `artifact_version`
- `public_url`
- `qr_value_hash`
- `status` (`issued`, `revoked`, or `failed`)
- `created_at`
- `updated_at`
- `revoked_at`

`portfolio_id` is not a foreign key yet because the portfolio persistence
component has not landed. It should become a foreign key when the portfolio
table and publishing workflow are finalized.

The database does not store Apple private certificates, Google service-account
private keys, raw refresh tokens, or unnecessary long-lived Google JWTs.

## Provider interface

`backend/wallets/providers.py` defines the shared provider contract:

1. The API validates the authenticated user and portfolio artifact.
2. It creates a `WalletPassRequest`.
3. The selected provider creates a `WalletPassResult`.
4. The API persists issuance metadata and returns the platform-specific result.

Fake providers can be used in tests before Apple or Google credentials exist.

## Planned API

```text
POST /v1/wallet/passes/apple
POST /v1/wallet/passes/google
GET  /v1/wallet/passes
DELETE /v1/wallet/passes/{id}
```

Expected result shapes:

Apple:

```json
{
  "platform": "apple",
  "content_type": "application/vnd.apple.pkpass",
  "filename": "portfolio-card.pkpass"
}
```

Google:

```json
{
  "platform": "google",
  "add_to_wallet_url": "https://pay.google.com/gp/v/save/<signed-jwt>"
}
```

The raw Google signing key and Apple certificate never leave the backend.

## Security boundaries

- Require authentication and portfolio ownership for issuance.
- Use HTTPS for public URLs and wallet downloads.
- Keep Apple certificates and Google service-account keys in deployment secret
  storage.
- Never put provider private keys in Expo variables or the mobile bundle.
- Do not put application authentication tokens in QR codes.
- Hash the QR value for issuance metadata and idempotency checks.
- Do not log pass bytes, JWTs, QR values, certificate contents, or keys.
- Rate-limit pass creation to prevent provider abuse.
- Revoke or regenerate a pass when its portfolio is unpublished or its public
  URL changes.

## Implementation phases

1. Add the `wallet_passes` migration and provider interfaces.
2. Add fake providers and API contract tests.
3. Connect the portfolio publishing record and public URL.
4. Implement Google Generic Pass issuance.
5. Implement Apple `.pkpass` generation and signing.
6. Add web buttons and native handoff behavior.
7. Add revocation, updates, and optional Apple pass web-service support.
