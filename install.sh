#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/ASTRACAT2022/Pepoapple.git}"
BRANCH="${BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/Pepoapple}"
AUTO_INSTALL_DOCKER="${AUTO_INSTALL_DOCKER:-1}"
INSTALL_DEMO_NODES="${INSTALL_DEMO_NODES:-0}"
API_BASE_URL="${API_BASE_URL:-}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
OS_NAME="$(uname -s)"

GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
NC="\033[0m"

DOCKER_CMD=(docker)
GENERATED_ADMIN_PASSWORD=""

log_info() {
  printf "${GREEN}[INFO]${NC} %s\n" "$1"
}

log_warn() {
  printf "${YELLOW}[WARN]${NC} %s\n" "$1"
}

log_error() {
  printf "${RED}[ERROR]${NC} %s\n" "$1" >&2
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

is_macos() {
  [ "$OS_NAME" = "Darwin" ]
}

is_linux() {
  [ "$OS_NAME" = "Linux" ]
}

run_as_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif need_cmd sudo; then
    sudo "$@"
  else
    log_error "This step requires root privileges, but sudo is not available."
    exit 1
  fi
}

install_base_tools() {
  local missing=()
  for tool in git curl; do
    if ! need_cmd "$tool"; then
      missing+=("$tool")
    fi
  done

  if [ "${#missing[@]}" -eq 0 ]; then
    return
  fi

  if is_linux && [ -f /etc/debian_version ]; then
    log_info "Installing missing tools: ${missing[*]}"
    run_as_root apt-get update
    run_as_root apt-get install -y "${missing[@]}"
  elif is_macos; then
    if ! need_cmd brew; then
      log_error "Homebrew is required on macOS. Install it first: https://brew.sh"
      exit 1
    fi
    log_info "Installing missing tools with Homebrew: ${missing[*]}"
    brew install "${missing[@]}"
  else
    log_error "Missing required tools (${missing[*]}). Install them and rerun installer."
    exit 1
  fi
}

install_docker_if_needed() {
  if need_cmd docker; then
    return
  fi

  if [ "$AUTO_INSTALL_DOCKER" != "1" ]; then
    log_error "Docker is not installed. Set AUTO_INSTALL_DOCKER=1 or install Docker manually."
    exit 1
  fi

  if is_macos; then
    if ! need_cmd brew; then
      log_error "Homebrew is required on macOS. Install it first: https://brew.sh"
      exit 1
    fi
    log_info "Installing Docker CLI + Colima via Homebrew..."
    brew install docker docker-compose colima
    return
  fi

  if is_linux && [ -f /etc/os-release ]; then
    log_info "Docker not found. Installing Docker Engine via official script..."
    curl -fsSL https://get.docker.com | run_as_root sh
    return
  fi

  log_error "Cannot auto-install Docker on this OS. Install Docker manually and rerun installer."
  exit 1
}

ensure_compose() {
  if docker compose version >/dev/null 2>&1; then
    return
  fi

  if is_linux && [ -f /etc/debian_version ]; then
    log_info "Installing docker compose plugin..."
    run_as_root apt-get update
    run_as_root apt-get install -y docker-compose-plugin
  elif is_macos && need_cmd brew; then
    log_info "Installing docker-compose plugin/binary via Homebrew..."
    brew install docker-compose
  fi

  if ! docker compose version >/dev/null 2>&1; then
    log_error "docker compose is not available. Install Docker Compose v2 and rerun."
    exit 1
  fi
}

configure_docker_cmd() {
  if docker info >/dev/null 2>&1; then
    DOCKER_CMD=(docker)
    return
  fi

  if is_macos && need_cmd colima; then
    log_info "Starting Colima Docker runtime..."
    if ! colima status >/dev/null 2>&1; then
      colima start
    fi
    if docker info >/dev/null 2>&1; then
      DOCKER_CMD=(docker)
      return
    fi
  fi

  if need_cmd sudo && sudo docker info >/dev/null 2>&1; then
    DOCKER_CMD=(sudo docker)
    log_warn "Using sudo for docker commands."
    return
  fi

  log_error "Cannot access Docker daemon. Ensure Docker service is running and permissions are correct."
  exit 1
}

git_clone_or_update() {
  if [ -d "$INSTALL_DIR/.git" ]; then
    log_info "Existing installation found at $INSTALL_DIR. Updating..."
    git -C "$INSTALL_DIR" fetch origin "$BRANCH"
    git -C "$INSTALL_DIR" checkout "$BRANCH"
    git -C "$INSTALL_DIR" pull --ff-only origin "$BRANCH"
  else
    log_info "Cloning repository to $INSTALL_DIR"
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
  fi
}

rand_hex() {
  if need_cmd openssl; then
    openssl rand -hex "$1"
  else
    dd if=/dev/urandom bs=1 count="$1" 2>/dev/null | od -An -tx1 | tr -d ' \n'
  fi
}

env_file() {
  printf "%s/.env" "$INSTALL_DIR"
}

get_env_val() {
  local key="$1"
  local file
  file="$(env_file)"
  if [ ! -f "$file" ]; then
    return
  fi
  grep -E "^${key}=" "$file" | tail -n 1 | cut -d'=' -f2-
}

set_env_val() {
  local key="$1"
  local value="$2"
  local file tmp
  file="$(env_file)"
  tmp="$(mktemp)"

  awk -v k="$key" -v v="$value" -F= '
    BEGIN { done=0 }
    $1==k { print k "=" v; done=1; next }
    { print }
    END { if (!done) print k "=" v }
  ' "$file" > "$tmp"

  mv "$tmp" "$file"
}

init_env_file() {
  local file
  file="$(env_file)"

  if [ ! -f "$file" ]; then
    cp "$INSTALL_DIR/.env.example" "$file"
    log_info "Created .env from .env.example"
  fi

  local jwt
  jwt="$(get_env_val JWT_SECRET || true)"
  if [ -z "$jwt" ] || [ "$jwt" = "change-me" ]; then
    set_env_val JWT_SECRET "$(rand_hex 32)"
  fi

  if [ "$(get_env_val NODE_1_TOKEN || true)" = "demo-node-1-token" ] || [ -z "$(get_env_val NODE_1_TOKEN || true)" ]; then
    set_env_val NODE_1_TOKEN "node1-$(rand_hex 12)"
  fi

  if [ "$(get_env_val NODE_2_TOKEN || true)" = "demo-node-2-token" ] || [ -z "$(get_env_val NODE_2_TOKEN || true)" ]; then
    set_env_val NODE_2_TOKEN "node2-$(rand_hex 12)"
  fi

  local api_url
  api_url="$(get_env_val NEXT_PUBLIC_API_BASE_URL || true)"
  if [ -n "$API_BASE_URL" ]; then
    set_env_val NEXT_PUBLIC_API_BASE_URL "$API_BASE_URL"
  elif [ -z "$api_url" ] || [ "$api_url" = "http://localhost:8080" ]; then
    set_env_val NEXT_PUBLIC_API_BASE_URL "http://localhost:8080"
  fi
}

compose_up() {
  log_info "Starting docker stack..."
  if [ "$INSTALL_DEMO_NODES" = "1" ]; then
    (
      cd "$INSTALL_DIR"
      "${DOCKER_CMD[@]}" compose --profile demo up -d --build
    )
  else
    (
      cd "$INSTALL_DIR"
      "${DOCKER_CMD[@]}" compose up -d --build
    )
  fi
}

wait_api_health() {
  log_info "Waiting for API health..."

  local tries=90
  local i
  for ((i=1; i<=tries; i++)); do
    if curl -fsS "http://localhost:8080/api/v1/health" >/dev/null 2>&1; then
      log_info "API is healthy."
      return
    fi
    sleep 2
  done

  log_warn "API health endpoint did not respond in time. Check logs: docker compose logs -f api"
}

bootstrap_admin() {
  if [ -z "$ADMIN_PASSWORD" ]; then
    GENERATED_ADMIN_PASSWORD="admin-$(rand_hex 8)"
    ADMIN_PASSWORD="$GENERATED_ADMIN_PASSWORD"
  fi

  local payload
  payload="{\"username\":\"${ADMIN_USER}\",\"password\":\"${ADMIN_PASSWORD}\"}"

  local status
  status="$(curl -sS -o /tmp/pepoapple_bootstrap.json -w "%{http_code}" \
    -X POST "http://localhost:8080/api/v1/auth/bootstrap" \
    -H "Content-Type: application/json" \
    -d "$payload" || true)"

  if [ "$status" = "200" ]; then
    log_info "Admin bootstrap completed."
  elif [ "$status" = "409" ]; then
    log_info "Admin already exists. Skipping bootstrap."
    GENERATED_ADMIN_PASSWORD=""
  else
    log_warn "Admin bootstrap returned HTTP ${status}. Response saved to /tmp/pepoapple_bootstrap.json"
    GENERATED_ADMIN_PASSWORD=""
  fi
}

print_summary() {
  local panel_url api_url
  panel_url="http://localhost:3000"
  api_url="http://localhost:8080"

  cat <<EOF_SUMMARY

Installation complete.

Paths:
- Install dir: $INSTALL_DIR
- Env file: $(env_file)

Endpoints:
- Panel: $panel_url
- API: $api_url
- GraphQL: $api_url/graphql
- Subscription page: http://localhost:3010/<token_or_short_id>

Docker:
- Check status: cd $INSTALL_DIR && ${DOCKER_CMD[*]} compose ps
- Logs: cd $INSTALL_DIR && ${DOCKER_CMD[*]} compose logs -f api frontend subscription-page

Node agents on separate servers:
- Run per node server:
  curl -fsSL https://raw.githubusercontent.com/ASTRACAT2022/Pepoapple/main/install-node.sh -o install-node.sh
  chmod +x install-node.sh
  AGENT_API_BASE_URL='$api_url' AGENT_NODE_TOKEN='<node_token>' ./install-node.sh
EOF_SUMMARY

  if [ -n "$GENERATED_ADMIN_PASSWORD" ]; then
    cat <<EOF_CREDS

Admin credentials (generated):
- Username: $ADMIN_USER
- Password: $GENERATED_ADMIN_PASSWORD

Change this password immediately after first login.
EOF_CREDS
  fi
}

main() {
  install_base_tools
  install_docker_if_needed
  ensure_compose
  configure_docker_cmd
  git_clone_or_update
  init_env_file
  compose_up
  wait_api_health
  bootstrap_admin
  print_summary
}

main "$@"
