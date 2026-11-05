# Login Authenticator Architecture

## Purpose

This project provides email-based registration and login for a React Native
application. The mobile client never connects directly to PostgreSQL. Requests
pass through KrakenD to the FastAPI authentication service, which owns identity,
password, session, and token operations.

The system is organized like a building:

- React Native is the front desk where a person submits a request.
- KrakenD is the reception desk that directs traffic to the correct office.
- FastAPI is the identity office that checks credentials and issues documents.
- PostgreSQL is the locked records room.
- Docker Compose is the building manager that starts the offices in order.
- Alembic is the records-room renovation log that changes the database safely.

## System flow

```text
React Native / Expo client
        |
        | HTTPS JSON requests
        v
KrakenD gateway :8080
        |
        | internal Docker network
        v
FastAPI authentication service :5000
        |
        | SQLAlchemy connection pool and transactions
        v
PostgreSQL :5432
```

The client receives only access and refresh tokens. Database credentials,
Argon2id configuration, JWT keys, and PostgreSQL details remain server-side.

## Components

### React Native and Expo

The client provides registration, login, logout, refresh, and input-idle
behavior. `expo-secure-store` stores the access JWT and raw refresh token in
device-protected storage. AsyncStorage is not used for credentials or tokens.

Analogy: Secure Store is a locked wallet on the user’s device. The app can use
what is inside, but it does not leave the wallet on a public desk.

### KrakenD

KrakenD is the public API gateway. It owns the client-facing HTTP boundary and
forwards approved routes to FastAPI. It does not connect to PostgreSQL and does
not receive database credentials.

Analogy: KrakenD is a receptionist. It knows which office to call, but it does
not enter the records room or handle the records itself.

### FastAPI authentication service

FastAPI owns authentication behavior:

- validates request shape and email/password input
- hashes and verifies passwords with Argon2id
- creates and verifies RS256 access JWTs
- generates cryptographically random refresh tokens
- stores only refresh-token hashes
- rotates single-use refresh tokens
- revokes token families after refresh-token reuse
- tracks server-side `last_activity_at`
- applies login rate limiting
- performs parameterized SQL transactions through SQLAlchemy

Analogy: FastAPI is the identity office. It checks a person’s credentials,
creates an official access document, and records which documents are active or
revoked.

### SQLAlchemy

SQLAlchemy provides the PostgreSQL engine, connection pooling, transaction
boundaries, and typed database models. The service uses explicit queries and
does not build SQL by concatenating user input.

Analogy: the connection pool is a fleet of reusable secure vehicles. Requests
borrow a vehicle, complete their database trip, and return it instead of
creating a new vehicle for every request.

### PostgreSQL

PostgreSQL stores durable identity and session records.

`users`:

- `id`
- `email` (unique)
- `password_hash`
- `created_at`

`sessions`:

- `id`
- `user_id`
- `refresh_token_hash` (unique)
- `token_family_id`
- `expires_at`
- `revoked_at`
- `created_at`
- `used_at`
- `last_activity_at`

Analogy: PostgreSQL is a locked records room. It stores fingerprints of
refresh tokens, not the usable tokens themselves.

### Alembic

Alembic stores schema changes as ordered migration files. Migrations run after
PostgreSQL becomes healthy and before FastAPI starts accepting requests.

Analogy: Alembic is a renovation log. Each change is numbered, repeatable,
and recorded so every environment can reach the same database layout.

### Docker Compose

Docker Compose runs:

- PostgreSQL
- the Alembic migration job
- the FastAPI authentication service
- KrakenD

The migration job depends on PostgreSQL health. FastAPI depends on successful
migrations. KrakenD depends on FastAPI.

## Authentication lifecycle

### Registration

1. The client sends an email and password to `POST /v1/auth/register`.
2. FastAPI normalizes the email and validates the request.
3. FastAPI hashes the password with Argon2id.
4. FastAPI creates the user and an initial session in one transaction.
5. FastAPI returns a short-lived access JWT and a raw refresh token.
6. PostgreSQL stores the password hash and refresh-token hash only.

### Login

1. FastAPI finds the user by normalized email.
2. Argon2id verifies the submitted password against the stored hash.
3. FastAPI creates a new session and token family.
4. FastAPI returns the access JWT and raw refresh token.

Failed login responses remain generic so they do not reveal whether an email
exists.

### Access JWT

The FastAPI private RS256 key signs the access JWT. The public key verifies it.
The JWT contains issuer, audience, subject, session ID, token ID, issued-at,
expiration, and token type claims.

Access tokens expire after 15 minutes. They are signed for authenticity and
tamper detection; they are not encrypted containers for private data.

### Refresh-token rotation

1. The client sends the raw refresh token to `POST /v1/auth/refresh`.
2. FastAPI hashes it and searches for the matching session.
3. FastAPI rejects expired or revoked sessions.
4. FastAPI marks the old token as used and revoked.
5. FastAPI creates a replacement token in the same token family.
6. FastAPI returns a new access JWT and raw refresh token.

If a previously used refresh token appears again, FastAPI revokes every session
with the same `token_family_id`. This limits the damage of token theft and
forces re-authentication.

### Input-idle enforcement

The client sends `POST /v1/auth/input` only after real user interaction and
no more than once per five-minute throttle window. It sends no text contents.
FastAPI records the timestamp using the server clock in `last_activity_at`.

No input signal is sent merely because five minutes passed. If the user is
inactive for more than the configured 30-minute AFK period, refresh and other
session-sensitive operations are rejected. The client may also navigate to
the login screen locally for immediate user feedback.

## API surface

```text
POST /v1/auth/register
POST /v1/auth/login
POST /v1/auth/refresh
POST /v1/auth/logout
POST /v1/auth/input
GET  /health
```

## RS256 key storage

Local development uses ignored files such as:

```text
secrets/jwt-private.pem
secrets/jwt-public.pem
```

FastAPI mounts the private key read-only and uses it to sign tokens. The keys are
not committed to Git and are never included in the React Native bundle.

Production supplies the private key through deployment secret storage, Docker
Secrets, Kubernetes Secrets, or a cloud secret manager. The production FastAPI
container receives the key at runtime. Key rotation can temporarily support
both old and new public keys while old access tokens expire.

## Verification and testing

The project should verify:

- duplicate registration
- invalid credentials
- Argon2id password verification
- expired and malformed JWTs
- expired and revoked sessions
- refresh-token rotation
- refresh-token reuse and family revocation
- AFK input timeout
- login rate limiting
- absence of passwords, hashes, tokens, and secrets in logs
- Alembic upgrade and downgrade behavior
- KrakenD-to-FastAPI health routing
