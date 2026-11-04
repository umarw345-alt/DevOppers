---

# Login Authentication Platform Context

The project is a mobile-focused app, developed for Apple and Android mobile devices.

We also want to port this to React Native Expo as it is currently a React Native project.

## PROJECT CONTEXT / System Architecture

The project scope is as follows:

React Native Client - holds signed JWT tokens and raw refresh tokens in Secure Storage
    ↓ POST auth/login
    ↓ POST auth/register
KrakenD
    ↓ forwards HTTPS POST request
FastAPI Authentication Service
    ├─ validates username/password
    ├─ hashes password with Argon2id
    ├─ sends parameterized INSERT query
    ├─ token creation
    ├─ token revocation
PostgreSQL - stores username, password_hash, hashed refresh tokens, user metadata

### Project flow:

The React Native client inputs text field to either register or login with username and password, sends a POST request through the KrakenD backend proxy to the FastAPI authentication service, which FastAPI uses to authenticate the request. The client should never directly access the authorization service. Both the client and KrakenD should never see database details; that is FastAPI's job. The FastAPI authentication service uses parameterized SQL queries and transactions for reads and writes. Only the access JWT and raw refresh tokens are returned to the client, PostgreSQL only stores the refresh-token hash.

Refresh tokens should be refreshed, invalidating the previous one when the old one is used for a new access token. The new refresh token is issued, fighting against theft and silent token replay.

Token revocation should happen when the user is AFK (away from keyboard) for more than 30 minutes. The client will ask if the user is still there 5 minutes before. If the revocation happens, the user is immediately sent back to the login screen. The AFK rule is tracked and enforced server-side.

To track, there should be a field last_activity_at that can track the AFK time.

Access tokens should expire after 15 minutes, refresh tokens after 1 day.

The same token cannot be used twice; token reuse will register as a reuse event and immediately revoke the token family. First time use will mark the token as used and any subsequent uses will immediately revoke the token family, so re-authentication of the user/clients of the token family is needed.

The token_family_id and used_at fields in the database will keep track of token reuse.

Rate limiting is a deferred requirement but basic logic detection before deployment is a plus.

Login should verify the password against the stored password hash. Refresh-token hashes are only used during refresh.


### PostgreSQL database (for now)
users
- id
- username/email UNIQUE
- password_hash
- created_at

sessions
- id
- user_id
- refresh_token_hash
- token_family_id
- expires_at
- revoked_at
- created_at
- used_at
- last_activity_at

The database secrets should never be revealed.


## Secrets

.env.example       committed with placeholders
.env               ignored
*.pem              ignored
database backups   ignored
JWT secrets        server-only
PostgreSQL secrets server-only

## JWT configuration:
Authentication service is responsible for generating and signing the token, which is given to the client (the audience) as a session token. The signing algorithm will be RS256 since it is asymmetric. The FastAPI service owns the private key and verification uses the public key. Neither of them belong in the React Native client's secret storage. Access JWTs expire after 15 minutes. Secure Store retains the access and refresh tokens until the client explicitly removes them or they are rejected by the server.

### Docker

Docker compose runs PostgreSQL, the FastAPI authentication service, and KrakenD. FastAPI receives the database and authentication configuration through environment variables. PostgreSQL credentials, JWT signing secrets, and gateway credentials must come from ignored `.env` files or deployment secret storage.

KrakenD configuration may be stored when it contains no secrets. Database migrations run against PostgreSQL container before the authentication service is used. Argon2id parameters are configurable through environment variables, but the service must provide safe defaults and never log passwords, hashes, tokens, or secret values.

The FastAPI service configuration stores the non-secret defaults but Docker environment variables override them.

ARGON2_MEMORY_COST
ARGON2_TIME_COST
ARGON2_PARALLELISM
ARGON2_HASH_LENGTH
ARGON2_SALT_LENGTH

To start, Docker Desktop is required to be installed and opened and a series of startup scripts from .\scripts folder will provide optional startup helpers. It should contain startup scripts runnable in the terminal. The folder is created but no files yet are to be created or implemented, only planned for now.

.\scripts\start-krakend.ps1
.\scripts\start-fastapi.ps1
.\scripts\start-postgres.ps1


#### Docker setup:
docker compose up --build
docker compose down
npm run db:migrate
npm run db:migrate:status
npm test
npm run lint
npm run test:auth
npm run test:integration


### Security tests

Add security tests for duplicate registration, invalid credentials, expired tokens, revoked tokens, refresh rotation, refresh-token reuse, malformed JWTs, and ensuring secrets never appear in logs.