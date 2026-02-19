#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <api_base_url> <ssh_user> <nodes_file>"
  echo "nodes_file format: host,node_token"
  exit 1
fi

API_BASE_URL="$1"
SSH_USER="$2"
NODES_FILE="$3"

if [ ! -f "$NODES_FILE" ]; then
  echo "nodes file not found: $NODES_FILE"
  exit 1
fi

while IFS=, read -r host token; do
  host="${host//[[:space:]]/}"
  token="${token//[[:space:]]/}"

  if [ -z "$host" ] || [ -z "$token" ]; then
    continue
  fi

  echo "==> Installing node agent on ${host}"
  ssh "${SSH_USER}@${host}" \
    "curl -fsSL https://raw.githubusercontent.com/ASTRACAT2022/Pepoapple/main/install-node.sh -o /tmp/install-node.sh && \
     chmod +x /tmp/install-node.sh && \
     AGENT_API_BASE_URL='${API_BASE_URL}' AGENT_NODE_TOKEN='${token}' /tmp/install-node.sh"
done < "$NODES_FILE"
