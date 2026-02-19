#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/ASTRACAT2022/Pepoapple.git}"
BRANCH="${BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-/opt/pepoapple-subscription-page}"
AUTO_INSTALL_DOCKER="${AUTO_INSTALL_DOCKER:-1}"
PANEL_API_BASE_URL="${PANEL_API_BASE_URL:-}"
PAGE_TITLE="${PAGE_TITLE:-Pepoapple Subscription}"
SUPPORT_URL="${SUPPORT_URL:-https://t.me/}"
SHOW_RAW_LINKS="${SHOW_RAW_LINKS:-true}"
SUBPAGE_PORT="${SUBPAGE_PORT:-3010}"
CUSTOM_SUB_PREFIX="${CUSTOM_SUB_PREFIX:-}"
OS_NAME="$(uname -s)"

need_cmd() { command -v "$1" >/dev/null 2>&1; }
is_macos() { [ "$OS_NAME" = "Darwin" ]; }
is_linux() { [ "$OS_NAME" = "Linux" ]; }

as_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif need_cmd sudo; then
    sudo "$@"
  else
    echo "Root privileges required." >&2
    exit 1
  fi
}

install_deps() {
  if need_cmd git && need_cmd curl; then
    return
  fi
  if is_linux && [ -f /etc/debian_version ]; then
    as_root apt-get update
    as_root apt-get install -y git curl
  elif is_macos; then
    if ! need_cmd brew; then
      echo "Homebrew is required on macOS. Install it first: https://brew.sh" >&2
      exit 1
    fi
    brew install git curl
  fi
}

install_docker() {
  if need_cmd docker; then
    return
  fi
  if [ "$AUTO_INSTALL_DOCKER" != "1" ]; then
    echo "Docker missing and AUTO_INSTALL_DOCKER=0" >&2
    exit 1
  fi
  if is_macos; then
    if ! need_cmd brew; then
      echo "Homebrew is required on macOS. Install it first: https://brew.sh" >&2
      exit 1
    fi
    brew install docker docker-compose colima
    return
  fi
  curl -fsSL https://get.docker.com | as_root sh
}

ensure_compose() {
  if docker compose version >/dev/null 2>&1; then
    return
  fi
  if is_linux && [ -f /etc/debian_version ]; then
    as_root apt-get update
    as_root apt-get install -y docker-compose-plugin
  elif is_macos && need_cmd brew; then
    brew install docker-compose
  fi
  docker compose version >/dev/null 2>&1 || { echo "docker compose missing" >&2; exit 1; }
}

ensure_docker_runtime() {
  if docker info >/dev/null 2>&1; then
    return
  fi
  if is_macos && need_cmd colima; then
    if ! colima status >/dev/null 2>&1; then
      colima start
    fi
  fi
  docker info >/dev/null 2>&1 || { echo "Cannot access Docker daemon" >&2; exit 1; }
}

clone_or_update() {
  if [ -d "$INSTALL_DIR/.git" ]; then
    git -C "$INSTALL_DIR" fetch origin "$BRANCH"
    git -C "$INSTALL_DIR" checkout "$BRANCH"
    git -C "$INSTALL_DIR" pull --ff-only origin "$BRANCH"
  else
    as_root mkdir -p "$INSTALL_DIR"
    as_root chown "$(id -un)":"$(id -gn)" "$INSTALL_DIR"
    git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
  fi
}

write_compose() {
  if [ -z "$PANEL_API_BASE_URL" ]; then
    echo "PANEL_API_BASE_URL is required, example: https://api.example.com" >&2
    exit 1
  fi

  cat > "$INSTALL_DIR/.env.subpage" <<EOF_ENV
PANEL_API_BASE_URL=${PANEL_API_BASE_URL}
PAGE_TITLE=${PAGE_TITLE}
SUPPORT_URL=${SUPPORT_URL}
SHOW_RAW_LINKS=${SHOW_RAW_LINKS}
SUBPAGE_PORT=${SUBPAGE_PORT}
CUSTOM_SUB_PREFIX=${CUSTOM_SUB_PREFIX}
EOF_ENV

  cat > "$INSTALL_DIR/docker-compose.subpage.yml" <<'EOF_COMPOSE'
services:
  subscription-page:
    build:
      context: ./subscription-page
      dockerfile: Dockerfile
    env_file:
      - .env.subpage
    ports:
      - "${SUBPAGE_PORT:-3010}:3010"
    restart: unless-stopped
EOF_COMPOSE
}

start_service() {
  (cd "$INSTALL_DIR" && docker compose -f docker-compose.subpage.yml up -d --build)
}

detect_host_ip() {
  if is_linux && need_cmd hostname; then
    hostname -I 2>/dev/null | awk '{print $1}'
    return
  fi
  if is_macos; then
    ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost"
    return
  fi
  echo "localhost"
}

main() {
  install_deps
  install_docker
  ensure_compose
  ensure_docker_runtime
  clone_or_update
  write_compose
  start_service
  HOST_IP="$(detect_host_ip)"
  PATH_HINT="/<token_or_short_id>"
  if [ -n "$CUSTOM_SUB_PREFIX" ]; then
    PATH_HINT="/${CUSTOM_SUB_PREFIX}/<token_or_short_id>"
  fi
  echo ""
  echo "Subscription page deployed: http://${HOST_IP}:${SUBPAGE_PORT}"
  echo "Example link: http://${HOST_IP}:${SUBPAGE_PORT}${PATH_HINT}"
}

main "$@"
