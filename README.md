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
- Next.js + TypeScript + Tailwind admin UI with real API integration
- Functional sections:
  - Dashboard (health, analytics, node state)
  - Users (create, block, limits, assign squad, rotate keys, reset devices/subscription)
  - Squads/Servers (create and list)
  - Nodes (create, push desired config, rollback, offline check)
  - Client Billing (plans, orders, payment confirm)
  - Infra Billing (provider cost + due records)
  - Protocols (create/list protocol profiles)
  - Migration (dry-run/apply/verify + legacy map)
  - Audit (log viewer)
  - Settings (auth mode, bootstrap/login, API keys, webhooks, backups)
- Light/dark adaptation

### Node Agent (Go)
- Poll desired config
- Apply only when desired revision is newer than applied revision
- Validate + atomic apply + rollback config
- Heartbeat and apply result reporting
- Runtime modes:
  - Docker/process supervision (default)
  - systemd mode
- Runtime engines: `Sing-box + AWG2` (no Xray)

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
INSTALL_DEMO_NODES=0 \
bash <(curl -fsSL https://raw.githubusercontent.com/ASTRACAT2022/Pepoapple/main/install.sh)
```

macOS is supported without Docker Desktop (installer uses `colima`).

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
- Optional bundled subscription page: `http://localhost:3010/<token_or_short_id>`

Default compose starts:
- `db`, `redis`, `api`, `frontend`, `subscription-page`

Demo profile additionally starts:
- `seed`, `node-agent-1`, `node-agent-2`

Start with demo profile:

```bash
docker compose --profile demo up -d --build
```

## Separate Node Install

Install one node agent per remote server:

```bash
curl -fsSL https://raw.githubusercontent.com/ASTRACAT2022/Pepoapple/main/install-node.sh -o install-node.sh
chmod +x install-node.sh
AGENT_API_BASE_URL='https://api.example.com' AGENT_NODE_TOKEN='<node_token>' ./install-node.sh
```

Bulk install over SSH:

```bash
./scripts/install-nodes-ssh.sh https://api.example.com root ./nodes.csv
```

`nodes.csv` format:

```text
host,node_token
1.2.3.4,node-1-token
5.6.7.8,node-2-token
```

## Separate Subscription Page

Deploy subscription-page on another server:

```bash
curl -fsSL https://raw.githubusercontent.com/ASTRACAT2022/Pepoapple/main/install-subpage.sh -o install-subpage.sh
chmod +x install-subpage.sh
PANEL_API_BASE_URL='https://api.example.com' CUSTOM_SUB_PREFIX='' ./install-subpage.sh
```

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

Node-only host logs:

```bash
docker compose -f docker-compose.node.yml --env-file .env.node logs -f node-agent
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
- Subscription compatibility: `/api/v1/subscriptions/{token_or_short_id}`
- Subscription page inside API (optional): `/api/v1/sub/{token_or_short_id}`
- GraphQL: `/graphql`
