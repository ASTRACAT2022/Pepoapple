# Pepoapple Deployment Manual

This guide covers production deployment of Pepoapple with:
- panel/API in Docker
- node agents on separate servers
- optional separate subscription page (Remnawave-style)
- macOS test deployment without Docker Desktop

## 1. Topology

Recommended production topology:
- `panel host`: `api`, `frontend`, `postgres`, `redis`, optional `subscription-page`
- `node hosts`: one `node-agent` per server
- reverse proxy/TLS in front of panel and subpage

Ports:
- `3000` frontend
- `8080` API
- `3010` subscription-page (optional)
- `5432` Postgres (keep private)
- `6379` Redis (keep private)

## 2. Prerequisites

Linux:
- Docker Engine 24+
- Docker Compose v2+
- Git, curl

macOS (without Docker Desktop):
- Homebrew
- `docker` CLI + `colima` (installer can set this up automatically)

## 3. Quick Install (Panel Host)

One command:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/ASTRACAT2022/Pepoapple/main/install.sh)
```

Useful overrides:

```bash
INSTALL_DIR=/opt/pepoapple \
API_BASE_URL=https://api.example.com \
ADMIN_USER=admin \
ADMIN_PASSWORD='StrongPass123!' \
INSTALL_DEMO_NODES=0 \
AUTO_INSTALL_DOCKER=1 \
bash <(curl -fsSL https://raw.githubusercontent.com/ASTRACAT2022/Pepoapple/main/install.sh)
```

What it does:
- installs missing dependencies
- installs Docker (or Docker+Colima on macOS)
- clones/updates repo
- creates `.env`
- starts stack
- waits for API health
- bootstraps first admin

## 4. Manual Start (Panel Host)

```bash
git clone https://github.com/ASTRACAT2022/Pepoapple.git
cd Pepoapple
cp .env.example .env
```

Edit `.env`:
- `JWT_SECRET`
- `NEXT_PUBLIC_API_BASE_URL`
- `PUBLIC_API_BASE_URL`
- optional: `SUBPAGE_*`

Start base stack (without demo node containers):

```bash
docker compose up -d --build
```

Start with local demo node containers too:

```bash
docker compose --profile demo up -d --build
```

## 5. Separate Node Installation (Per Server)

Create node in panel (`Nodes`), copy node token, then run on each node server:

```bash
curl -fsSL https://raw.githubusercontent.com/ASTRACAT2022/Pepoapple/main/install-node.sh -o install-node.sh
chmod +x install-node.sh
AGENT_API_BASE_URL='https://api.example.com' AGENT_NODE_TOKEN='<node_token>' ./install-node.sh
```

Batch install over SSH:

```bash
./scripts/install-nodes-ssh.sh https://api.example.com root ./nodes.csv
```

`nodes.csv` format:

```text
1.2.3.4,node-token-1
5.6.7.8,node-token-2
```

Agent runtime notes:
- runtime is `Sing-box + AWG2` (no Xray)
- agent applies only new config revisions
- atomic apply + rollback
- per-engine config files stored in node volume

## 6. Subscription Page (Remnawave-style)

### Option A: bundled (same host)
Already included in main `docker-compose.yml` as service `subscription-page`.

URL example:
- `http://sub.example.com/<token_or_short_id>`

### Option B: separate server

```bash
curl -fsSL https://raw.githubusercontent.com/ASTRACAT2022/Pepoapple/main/install-subpage.sh -o install-subpage.sh
chmod +x install-subpage.sh
PANEL_API_BASE_URL='https://api.example.com' \
CUSTOM_SUB_PREFIX='' \
./install-subpage.sh
```

Supported envs:
- `PANEL_API_BASE_URL`
- `PAGE_TITLE`
- `SUPPORT_URL`
- `SHOW_RAW_LINKS=true|false`
- `CUSTOM_SUB_PREFIX` (like Remnawave custom sub path)

## 7. macOS Test Deploy (No Docker Desktop)

Run installer directly on macOS:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/ASTRACAT2022/Pepoapple/main/install.sh)
```

Installer will:
- install `docker`, `docker-compose`, `colima` via Homebrew (if missing)
- start Colima automatically
- start Pepoapple stack

If Homebrew is missing, install from [brew.sh](https://brew.sh) first.

## 8. Validation Checklist

Health:

```bash
curl -fsS http://localhost:8080/api/v1/health
```

Bootstrap/login:

```bash
curl -X POST http://localhost:8080/api/v1/auth/bootstrap \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"StrongPass123!"}'
```

Subscription compatibility:

```bash
curl -fsS http://localhost:8080/api/v1/subscriptions/<token_or_short_id>
```

Node heartbeat/apply:
- check `Nodes` page status
- check node logs:

```bash
docker compose -f docker-compose.node.yml --env-file .env.node logs -f node-agent
```

## 9. Upgrade

Panel host:

```bash
cd /opt/pepoapple
git pull
docker compose up -d --build
```

Node hosts:

```bash
cd /opt/pepoapple-node
git pull
docker compose -f docker-compose.node.yml --env-file .env.node up -d --build
```

## 10. Troubleshooting

Frontend build error `Can't resolve ../../lib/api`:
- fixed in current code (`frontend/lib` copied in Dockerfile)

`docker compose` warns about `version` key:
- removed in current compose files

Node stays `offline`:
- verify `AGENT_NODE_TOKEN`
- verify API reachability from node host
- check node service logs

Config apply failed:
- verify desired config JSON
- ensure at least one engine config exists (`singbox` or root sing-box fields, and/or `awg2`)
- agent will rollback previous config on failure

AWG2 binary/runtime issues:
- set custom env in node `.env.node`:
  - `AGENT_AWG2_RUN_COMMAND`
  - `AGENT_AWG2_VERSION_COMMAND`
- restart node agent container
