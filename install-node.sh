#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/ASTRACAT2022/Pepoapple.git}"
BRANCH="${BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-/opt/pepoapple-node}"
AUTO_INSTALL_DOCKER="${AUTO_INSTALL_DOCKER:-1}"
AGENT_API_BASE_URL="${AGENT_API_BASE_URL:-}"
AGENT_NODE_TOKEN="${AGENT_NODE_TOKEN:-}"
AGENT_HEARTBEAT_INTERVAL_SEC="${AGENT_HEARTBEAT_INTERVAL_SEC:-15}"
AGENT_RUNTIME_MODE="${AGENT_RUNTIME_MODE:-process}"
AGENT_SINGBOX_RUN_COMMAND="${AGENT_SINGBOX_RUN_COMMAND:-sing-box run -D /data -c /data/singbox.json}"
AGENT_AWG2_RUN_COMMAND="${AGENT_AWG2_RUN_COMMAND:-awg2 -f wg0}"
OS_NAME="$(uname -s)"

GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
NC="\033[0m"

DOCKER_CMD=(docker)

info() { printf "${GREEN}[INFO]${NC} %s\n" "$1"; }
warn() { printf "${YELLOW}[WARN]${NC} %s\n" "$1"; }
err() { printf "${RED}[ERROR]${NC} %s\n" "$1" >&2; }

need_cmd() { command -v "$1" >/dev/null 2>&1; }

is_macos() { [ "$OS_NAME" = "Darwin" ]; }

is_linux() { [ "$OS_NAME" = "Linux" ]; }

as_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif need_cmd sudo; then
    sudo "$@"
  else
    err "Root privileges required (sudo missing)."
    exit 1
  fi
}

install_tools() {
  if need_cmd git && need_cmd curl; then
    return
  fi
  if is_linux && [ -f /etc/debian_version ]; then
    info "Installing git/curl..."
    as_root apt-get update
    as_root apt-get install -y git curl
  elif is_macos; then
    if ! need_cmd brew; then
      err "Homebrew is required on macOS. Install it first: https://brew.sh"
      exit 1
    fi
    info "Installing git/curl via Homebrew..."
    brew install git curl
  else
    err "Install git and curl manually, then rerun."
    exit 1
  fi
}

install_docker() {
  if need_cmd docker; then
    return
  fi
  if [ "$AUTO_INSTALL_DOCKER" != "1" ]; then
    err "Docker missing and AUTO_INSTALL_DOCKER=0"
    exit 1
  fi
  if is_macos; then
    if ! need_cmd brew; then
      err "Homebrew is required on macOS. Install it first: https://brew.sh"
      exit 1
    fi
    info "Installing Docker CLI + Colima via Homebrew..."
    brew install docker docker-compose colima
    return
  fi
  info "Installing Docker..."
  curl -fsSL https://get.docker.com | as_root sh
}

ensure_compose() {
  if docker compose version >/dev/null 2>&1; then
    return
  fi
  if is_linux && [ -f /etc/debian_version ]; then
    info "Installing docker compose plugin..."
    as_root apt-get update
    as_root apt-get install -y docker-compose-plugin
  elif is_macos && need_cmd brew; then
    info "Installing docker-compose via Homebrew..."
    brew install docker-compose
  fi
  docker compose version >/dev/null 2>&1 || { err "docker compose not available"; exit 1; }
}

configure_docker_cmd() {
  if docker info >/dev/null 2>&1; then
    DOCKER_CMD=(docker)
    return
  fi
  if is_macos && need_cmd colima; then
    info "Starting Colima Docker runtime..."
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
    warn "Using sudo docker"
    return
  fi
  err "Cannot access docker daemon"
  exit 1
}

clone_or_update() {
  if [ -d "$INSTALL_DIR/.git" ]; then
    info "Updating $INSTALL_DIR"
    git -C "$INSTALL_DIR" fetch origin "$BRANCH"
    git -C "$INSTALL_DIR" checkout "$BRANCH"
    git -C "$INSTALL_DIR" pull --ff-only origin "$BRANCH"
  else
    info "Cloning repository to $INSTALL_DIR"
    as_root mkdir -p "$INSTALL_DIR"
    as_root chown "$(id -un)":"$(id -gn)" "$INSTALL_DIR"
    git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
  fi
}

write_env_file() {
  if [ -z "$AGENT_API_BASE_URL" ]; then
    err "AGENT_API_BASE_URL is required (example: https://api.example.com)"
    exit 1
  fi
  if [ -z "$AGENT_NODE_TOKEN" ]; then
    err "AGENT_NODE_TOKEN is required"
    exit 1
  fi

  cat > "$INSTALL_DIR/.env.node" <<EOF_ENV
AGENT_API_BASE_URL=${AGENT_API_BASE_URL}
AGENT_NODE_TOKEN=${AGENT_NODE_TOKEN}
AGENT_HEARTBEAT_INTERVAL_SEC=${AGENT_HEARTBEAT_INTERVAL_SEC}
AGENT_RUNTIME_MODE=${AGENT_RUNTIME_MODE}
AGENT_SINGBOX_RUN_COMMAND=${AGENT_SINGBOX_RUN_COMMAND}
AGENT_AWG2_RUN_COMMAND=${AGENT_AWG2_RUN_COMMAND}
EOF_ENV
}

start_node_agent() {
  info "Starting node-agent container"
  (
    cd "$INSTALL_DIR"
    "${DOCKER_CMD[@]}" compose -f docker-compose.node.yml --env-file .env.node up -d --build
  )
}

main() {
  install_tools
  install_docker
  ensure_compose
  configure_docker_cmd
  clone_or_update
  write_env_file
  start_node_agent

  cat <<EOF_DONE

Node agent installation completed.

Install dir: $INSTALL_DIR
Env file: $INSTALL_DIR/.env.node

Useful commands:
- status: cd $INSTALL_DIR && ${DOCKER_CMD[*]} compose -f docker-compose.node.yml --env-file .env.node ps
- logs:   cd $INSTALL_DIR && ${DOCKER_CMD[*]} compose -f docker-compose.node.yml --env-file .env.node logs -f node-agent
EOF_DONE
}

main "$@"
