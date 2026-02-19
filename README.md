# Pepoapple (Ananas)

Proxy Manager + Client Billing Platform with AWG2/Sing-box support and zero-touch migration from Remnawave.

## Implemented Scope

### Core Platform
- FastAPI backend with REST API versioning under `/api/v1`
- GraphQL API at `/graphql` (Query + Mutation + Subscription)
- PostgreSQL models via SQLAlchemy + Redis-ready rate limiting
- Audit log for critical operations

### Security
- JWT access/refresh auth
- Scoped API keys
- Role model: `super_admin`, `admin`, `operator`, `billing_manager`, `support`, `reseller`, `user`
- Scope checks (`users.read`, `users.write`, `billing.read`, `billing.write`, `nodes.control`, `squads.write`, `api.manage`, `migration.run`, `infra.billing.read`)
- Request rate limiting middleware

### Proxy/Infra Management
- Users, squads, servers, nodes
- Protocol profiles (`AWG2`, `TUIC`, `VLESS`, `Sing-box`)
- Node config revisions + rollback flow
- Agent endpoints:
  - `POST /agent/heartbeat`
  - `GET /agent/desired-config`
  - `POST /agent/apply-result`
  - `POST /agent/report-usage`

### HWID and Device Policy
- Device hash tracking
- `strict_bind`
- `max_devices`
- Eviction policies (`reject`, `evict_oldest`)
- Manual device reset

### Billing
- Plans, orders, payments
- Payment confirmation activates subscription
- Infra billing report with due/reminder view

### Webhooks
- Webhook endpoint registration
- Event queueing + delivery tracking + retry processing
- Supported emitted events:
  - `user.created`
  - `user.blocked`
  - `traffic.limit_reached`
  - `order.paid`
  - `config.applied`
  - `migration.completed`

### Migration Tool
- Modes: `dry-run`, `apply`, `verify`
- Legacy token mapping for compatibility links
- Subscription verification flow for migrated tokens

### Backup
- Snapshot creation to local storage
- Backup registry in DB

### Frontend
- Next.js + TypeScript + Tailwind admin UI scaffold
- Sections for Dashboard, Users, Squads, Nodes, Servers, Protocols, Billing, Audit, Settings, Migration
- Light/dark adaptation

### Node Agent (Go)
- Poll desired config
- Validate + apply + rollback config
- Heartbeat and apply result reporting
- Systemd restart hooks for `awg2` and `sing-box`

## Repository Layout

- `app/` backend service
- `sql/` SQL migration scripts
- `agent/` Go node agent
- `frontend/` Next.js admin panel
- `deploy/` systemd unit examples
- `install.sh` one-command installer

## Easy Installer

One command install/update:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/ASTRACAT2022/Pepoapple/main/install.sh)
```

Optional installer env overrides:

```bash
INSTALL_DIR=$HOME/Pepoapple \
API_BASE_URL=https://api.example.com \
ADMIN_USER=root \
ADMIN_PASSWORD='StrongPass123!' \
bash <(curl -fsSL https://raw.githubusercontent.com/ASTRACAT2022/Pepoapple/main/install.sh)
```

## Run Backend (Local)

1. Start dependencies:

```bash
docker compose up -d db redis
```

2. Copy environment:

```bash
cp .env.example .env
```

3. Install Python deps:

```bash
python3 -m pip install fastapi uvicorn sqlalchemy 'psycopg[binary]' pydantic-settings python-multipart python-jose[cryptography] passlib redis strawberry-graphql[fastapi] httpx pytest pytest-asyncio
```

4. Run API:

```bash
make run
```

## Run Full Stack (Docker)

```bash
cp .env.example .env
make docker-up
```

- Backend: `http://localhost:8080`
- GraphQL: `http://localhost:8080/graphql`
- Frontend: `http://localhost:3000`
- Node Agents in Docker: `node-agent-1`, `node-agent-2`

What Compose now does automatically:
- starts `db`, `redis`, `api`, `frontend`
- runs `seed` once to create demo squad/servers/nodes
- starts 2 node-agent containers connected to API

## Auth Bootstrap

Create first super-admin:

```bash
curl -X POST http://localhost:8080/api/v1/auth/bootstrap \
  -H 'Content-Type: application/json' \
  -d '{"username":"root","password":"secret123"}'
```

## Tests

```bash
make test
```

Current test set covers:
- MVP acceptance criteria
- auth bootstrap/login/api-key flow
- HWID strict + eviction policy
- webhook enqueue/delivery processing
- migration dry-run/apply/verify
- GraphQL query availability

## Docker Operations

Check container status:

```bash
docker compose ps
```

Check agents/API logs:

```bash
docker compose logs -f api node-agent-1 node-agent-2
```

## SQL Scripts

- `sql/001_init.sql` - base MVP schema
- `sql/002_full_features.sql` - full feature expansion

## Notable API Groups

- Auth: `/api/v1/auth/*`
- Users + HWID: `/api/v1/users/*`
- Squads/Servers: `/api/v1/squads`, `/api/v1/servers`
- Nodes + configs: `/api/v1/nodes/*`
- Billing: `/api/v1/plans`, `/api/v1/orders`, `/api/v1/payments/confirm`
- Infra billing: `/api/v1/infra-billing/report`
- Protocols: `/api/v1/protocols`
- Webhooks: `/api/v1/webhooks/*`
- Migration: `/api/v1/migration/*`
- Backups: `/api/v1/backups/*`
- Analytics: `/api/v1/analytics/overview`
- Subscription compatibility: `/api/v1/subscriptions/{token}`
- GraphQL: `/graphql`
