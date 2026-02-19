# Pepoapple Deployment Manual

This guide covers production deployment of Pepoapple (API + Frontend + PostgreSQL + Redis + Node Agents) using Docker Compose.

## 1. Architecture

Services:
- `api` - FastAPI backend (`:8080`)
- `frontend` - Next.js admin panel (`:3000`)
- `db` - PostgreSQL 16
- `redis` - Redis 7
- `seed` - one-time demo data bootstrap
- `node-agent-1`, `node-agent-2` - Go node agents connected to API

Persistent volumes:
- `pgdata` - PostgreSQL data
- `backups` - exported backup snapshots
- `agent1-data`, `agent2-data` - agent runtime/config data

## 2. Prerequisites

On target server:
- Linux host with Docker Engine 24+
- Docker Compose v2+
- 2 CPU / 4 GB RAM minimum
- Open ports:
  - `80` and `443` (reverse proxy)
  - `8080` (optional direct API access)
  - `3000` (optional direct frontend access)

Recommended:
- separate reverse proxy (Nginx/Caddy/Traefik)
- domain names:
  - `panel.example.com` -> frontend
  - `api.example.com` -> API

## 3. Clone and Prepare

```bash
git clone https://github.com/ASTRACAT2022/Pepoapple.git
cd Pepoapple
cp .env.example .env
```

Fast path (automatic installer):

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/ASTRACAT2022/Pepoapple/main/install.sh)
```

Installer supports optional overrides:
- `INSTALL_DIR`
- `API_BASE_URL`
- `ADMIN_USER`
- `ADMIN_PASSWORD`
- `AUTO_INSTALL_DOCKER` (`1` or `0`)

## 4. Environment Configuration

Edit `.env` before first start:

Mandatory:
- `JWT_SECRET` - set a long random secret (32+ chars)
- `DOCKER_DATABASE_URL` - keep default unless custom DB host
- `DOCKER_REDIS_URL` - keep default unless custom Redis host
- `NEXT_PUBLIC_API_BASE_URL` - public API URL (e.g. `https://api.example.com`)

Node/seed:
- `SEED_SQUAD_NAME`
- `NODE_1_TOKEN`
- `NODE_2_TOKEN`
- `AGENT_HEARTBEAT_INTERVAL_SEC`

Security hardening:
- do not use default secrets/tokens in production
- restrict public access to DB/Redis ports (5432/6379)

## 5. Start Full Stack

```bash
docker compose up -d --build
```

Check status:

```bash
docker compose ps
```

Check logs:

```bash
docker compose logs -f api frontend node-agent-1 node-agent-2
```

## 6. Bootstrap Admin

Create first super-admin once:

```bash
curl -X POST http://localhost:8080/api/v1/auth/bootstrap \
  -H 'Content-Type: application/json' \
  -d '{"username":"root","password":"CHANGE_ME_STRONG_PASSWORD"}'
```

If API is behind TLS domain:

```bash
curl -X POST https://api.example.com/api/v1/auth/bootstrap \
  -H 'Content-Type: application/json' \
  -d '{"username":"root","password":"CHANGE_ME_STRONG_PASSWORD"}'
```

## 7. Post-Deploy Validation Checklist

Health:
```bash
curl http://localhost:8080/api/v1/health
```

GraphQL:
```bash
curl -X POST http://localhost:8080/graphql \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ users { id } }"}'
```

Frontend:
- open `http://SERVER_IP:3000`

Agents:
- verify node heartbeat in logs:
```bash
docker compose logs -f node-agent-1 node-agent-2
```

DB connectivity:
```bash
docker compose exec db psql -U pepoapple -d pepoapple -c '\dt'
```

## 8. Reverse Proxy (Nginx Example)

Example `/etc/nginx/conf.d/pepoapple.conf`:

```nginx
server {
  listen 80;
  server_name panel.example.com;

  location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}

server {
  listen 80;
  server_name api.example.com;

  location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

Then enable TLS (Certbot or Caddy).

## 9. Backups and Restore

Run backup via API:

```bash
curl -X POST http://localhost:8080/api/v1/backups/run \
  -H 'X-Scopes: *' \
  -H 'Content-Type: application/json' \
  -d '{"storage_type":"local"}'
```

Backup files are in Docker volume mounted to `/app/backups` inside API container.

Manual DB backup:

```bash
docker compose exec db pg_dump -U pepoapple pepoapple > pepoapple_db_$(date +%F).sql
```

Restore DB:

```bash
cat pepoapple_db_YYYY-MM-DD.sql | docker compose exec -T db psql -U pepoapple -d pepoapple
```

## 10. Upgrade Procedure

1. Pull latest code:
```bash
git pull
```

2. Rebuild and restart:
```bash
docker compose up -d --build
```

3. Verify health/logs:
```bash
docker compose ps
docker compose logs --tail=200 api
```

## 11. Scaling Node Agents

To add more node agents:
1. Add unique token in `.env` (e.g. `NODE_3_TOKEN`)
2. Duplicate `node-agent-*` service in `docker-compose.yml`
3. Seed/register matching node in API (via seed script update or REST call)
4. `docker compose up -d --build`

## 12. Production Hardening

- Put API and frontend behind TLS only
- Block direct public access to DB/Redis ports
- Rotate JWT/API key secrets periodically
- Replace `X-Scopes: *` usage with real JWT/API keys
- Enable centralized logs (Loki/ELK) and metrics (Prometheus/Grafana)
- Add external uptime checks for `/api/v1/health`
- Use firewall and fail2ban

## 13. Troubleshooting

API cannot connect to DB:
- check `DOCKER_DATABASE_URL` in `.env`
- check `docker compose logs db api`

Frontend cannot call API:
- check `NEXT_PUBLIC_API_BASE_URL`
- check reverse proxy upstream and CORS/network

Agents offline:
- verify tokens match seeded node tokens
- check agent logs
- ensure API is reachable from Docker network (`http://api:8080`)

Auth bootstrap conflict:
- means admin already exists (`bootstrap_already_completed`)
- use `/api/v1/auth/login`

## 14. Useful Commands

Start stack:
```bash
docker compose up -d --build
```

Stop stack:
```bash
docker compose down
```

Stop + remove volumes (danger: data loss):
```bash
docker compose down -v
```

Run backend tests locally:
```bash
python3 -m pytest -q
```
