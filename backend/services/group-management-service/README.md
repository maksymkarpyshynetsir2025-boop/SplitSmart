# Group Management Service

Independent SplitSmart microservice for managing groups, memberships, roles, and
single-use invitations. It owns its PostgreSQL database and verifies JWTs
issued by the Authentication Service.

## Technology

- Python 3.13, FastAPI, Pydantic 2
- SQLAlchemy 2 async ORM and PostgreSQL 16 / asyncpg
- Alembic migrations
- PyJWT for Auth-compatible JWT verification
- `uv` for dependency management
- Docker and Docker Compose

## Project structure

```text
group-management-service/
├── app/
│   ├── api/v1/          # Versioned REST endpoints
│   ├── core/            # Settings, JWT auth, Auth Service client
│   ├── db/              # SQLAlchemy base and async sessions
│   ├── models/          # Groups, memberships, invitations
│   ├── schemas/         # Pydantic request/response models
│   ├── services/        # Business rules and authorization
│   └── main.py
├── alembic/             # Schema migrations
├── tests/
├── Dockerfile
├── alembic.ini
├── pyproject.toml
└── .env.example
```

## Configuration

Copy `.env.example` to `.env` and set strong local values. Configure the
**same** `JWT_SECRET` and `JWT_ALG` as the Auth Service. Configure a separate
random `AUTH_SERVICE_API_KEY`, and set the exact same key as
`INTERNAL_API_KEY` in `backend/services/auth_service/.env`.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Group-owned database URL; Compose uses `group_db` |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Credentials for the Compose database |
| `JWT_SECRET`, `JWT_ALG` | Verify Auth Service access tokens (`HS256` by default) |
| `AUTH_SERVICE_URL` | Auth Service base URL; Compose uses `http://auth_service:8000` |
| `AUTH_SERVICE_API_KEY` | Key sent to Auth's protected internal user lookup |
| `INVITATION_BASE_URL` | Public origin used to form invitation links |

For running the API on the host instead of in Compose, change
`DATABASE_URL` to use `localhost:5433` and `AUTH_SERVICE_URL` to
`http://localhost:8001`. The JWT secret and API key must match the Auth
Service's configured values. Do not commit `.env` files.

Auth access tokens contain the integer user ID as `sub` and the token type
`access`; refresh tokens use `refresh`. Both are signed using the configured
JWT algorithm. The group service validates the signature, expiration, and
access-token type, then uses Auth's API-key-protected internal user lookup to
verify target users and retrieve an invitee's email. It does not access the
Auth database or store user credentials.
Tokens issued before the Auth Service added the token-type claim are rejected
by this service; users must sign in again after that Auth Service update.

## Run with Docker Compose

1. Copy `backend/services/group-management-service/.env.example` to `.env`.
2. Set `JWT_SECRET` to the Auth Service's JWT secret.
3. Generate one strong internal API key and configure it as
   `INTERNAL_API_KEY` in the Auth `.env` and `AUTH_SERVICE_API_KEY` in this
   service's `.env`.
4. Ensure the Auth `.env` is configured, then run from the repository root:

   ```powershell
   docker compose up --build 
   ```

The Group API is at `http://localhost:8002`; PostgreSQL is exposed on host
port `5433`. Compose runs `alembic upgrade head` before starting the API.

```text
Swagger UI: http://localhost:8002/docs
ReDoc:      http://localhost:8002/redoc
Health:     http://localhost:8002/health
Readiness:  http://localhost:8002/health/ready
```

For local development, from this service directory:

```powershell
uv sync --all-groups
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

Database migrations:

```powershell
uv run alembic upgrade head
uv run alembic downgrade -1
```

## API

All endpoints are under `/api/v1`. Except health checks, they require:

```http
Authorization: Bearer <Auth-Service access_token>
```

The user ID is read only from the verified JWT `sub` claim. A client cannot
choose an owner by supplying an owner ID in the request body.

### Groups and membership

| Method | Path | Access / behavior |
|---|---|---|
| `POST` | `/groups` | Authenticated user creates a group and its OWNER membership |
| `GET` | `/groups?limit=50&offset=0` | List the caller's groups and role |
| `GET` | `/groups/{group_id}` | Member-only details and owner email |
| `PATCH` | `/groups/{group_id}` | Owner-only name/description update |
| `DELETE` | `/groups/{group_id}` | Owner-only soft archive; dependent rows are preserved |
| `GET` | `/groups/{group_id}/members` | Member-only member list (`limit`, `offset`) |
| `POST` | `/groups/{group_id}/members` | Owner-only add of an Auth-verified `user_id` |
| `DELETE` | `/groups/{group_id}/members/{member_id}` | Owner removes a non-owner |
| `DELETE` | `/groups/{group_id}/members/me` | Member voluntarily leaves |

Group names are trimmed and limited to 100 characters; descriptions are
optional and limited to 2,000 characters. Owners cannot leave or be removed;
ownership transfer is not implemented. Group/member database IDs are UUIDs,
while user IDs are integers to match Auth Service's existing user schema.

### Invitations

| Method | Path | Access / behavior |
|---|---|---|
| `POST` | `/groups/{group_id}/invitations` | Owner creates email invitation (`invited_email`, optional `expires_in_days`) |
| `POST` | `/groups/{group_id}/invitation-links` | Owner creates an unaddressed, single-use link |
| `GET` | `/invitations` | List pending, unexpired email invitations for the caller |
| `GET` | `/invitations/{invitation_id}` | View as invitee, creator, or group owner |
| `POST` | `/invitations/{invitation_id}/accept` | Accept with `{"token":"..."}` |
| `POST` | `/invitations/{invitation_id}/reject` | Reject with `{"token":"..."}` |
| `DELETE` | `/invitations/{invitation_id}` | Group owner cancels a pending invitation |

Invitation expiry is 1–30 days (default 7). The database stores only a SHA-256
digest of a cryptographically random token; the raw token is returned once in
the creation response, never included in later responses or logs. Email
invitations are limited to existing Auth users and can only be accepted by the
matching verified email. Link invitations can be accepted by any authenticated
user with the token and are single-use. The response includes an invitation
URL with the token in its URL fragment; a client should read the fragment and
submit the token in the accept/reject request body.

There is no email delivery integration. Creating an email invitation does not
send email or claim that delivery occurred; the owner must share the returned
link. Invitation statuses are `PENDING`, `ACCEPTED`, `REJECTED`, `EXPIRED`,
and `REVOKED`.

The invitation URL is a deep link built from `INVITATION_BASE_URL`; an
integrating client must handle its fragment and call the REST acceptance
endpoint. This service does not host a frontend invitation page.

### Example

Create a group:

```http
POST /api/v1/groups
Authorization: Bearer <access_token>
Content-Type: application/json

{"name":"Weekend trip","description":"Shared cabin costs"}
```

Example `201 Created` response:

```json
{
  "id": "b38a7035-8a11-48f0-8049-184913a4a8d1",
  "name": "Weekend trip",
  "description": "Shared cabin costs",
  "owner_id": 42,
  "created_at": "2026-11-16T18:00:00Z",
  "updated_at": "2026-11-16T18:00:00Z"
}
```

Create an email invitation:

```http
POST /api/v1/groups/{group_id}/invitations
Authorization: Bearer <owner_access_token>
Content-Type: application/json

{"invited_email":"member@example.com","expires_in_days":7}
```

The `201 Created` response includes an `invitation_token` and
`invitation_url`. The token is returned only at creation; the database stores
only its hash.

Accept it as the matching user:

```http
POST /api/v1/invitations/{invitation_id}/accept
Authorization: Bearer <invitee_access_token>
Content-Type: application/json

{"token":"<one-time invitation token>"}
```

## Persistence and deletion policy

Alembic creates `groups`, `group_memberships`, and `group_invitations`.
Membership uniqueness is enforced on `(group_id, user_id)`; a partial unique
index prevents duplicate pending email invitations. External user IDs have no
cross-service foreign keys.

Delete archives a group by setting `deleted_at` and revokes pending invites.
It deliberately does not delete the group row or memberships. This preserves
referential integrity for future expense/transaction services; no financial
data tables exist in this service to inspect or cascade-delete.

## Tests

```powershell
uv run pytest
```

