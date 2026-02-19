#!/usr/bin/env python3
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

API_BASE = os.getenv("API_BASE", "http://api:8080").rstrip("/")
HEADERS = {"Content-Type": "application/json", "X-Scopes": "*"}
SQUAD_NAME = os.getenv("SEED_SQUAD_NAME", "DOCKER-DEMO")
NODE_1_TOKEN = os.getenv("NODE_1_TOKEN", "demo-node-1-token")
NODE_2_TOKEN = os.getenv("NODE_2_TOKEN", "demo-node-2-token")


def request(method: str, path: str, body: Optional[dict] = None, expected: tuple[int, ...] = (200,)):
    url = f"{API_BASE}{path}"
    payload = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method=method)
    for k, v in HEADERS.items():
        req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw) if raw else {}
            if resp.status not in expected:
                raise RuntimeError(f"Unexpected status {resp.status} for {method} {path}: {data}")
            return resp.status, data
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        data = json.loads(raw) if raw else {}
        if exc.code in expected:
            return exc.code, data
        raise RuntimeError(f"HTTP {exc.code} for {method} {path}: {data}") from exc


def wait_api(max_attempts: int = 60):
    for _ in range(max_attempts):
        try:
            request("GET", "/api/v1/health", expected=(200,))
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("API did not become ready in time")


def ensure_squad() -> str:
    status, payload = request(
        "POST",
        "/api/v1/squads",
        {
            "name": SQUAD_NAME,
            "description": "Docker demo squad",
            "selection_policy": "round-robin",
            "fallback_policy": "none",
            "allowed_protocols": ["AWG2", "Sing-box"],
        },
        expected=(200, 409),
    )
    if status == 200:
        return payload["id"]

    _, squads = request("GET", "/api/v1/squads", expected=(200,))
    for squad in squads:
        if squad["name"] == SQUAD_NAME:
            return squad["id"]
    raise RuntimeError("Could not resolve squad id")


def ensure_server(squad_id: str, host: str, ip: str) -> str:
    status, payload = request(
        "POST",
        "/api/v1/servers",
        {
            "host": host,
            "ip": ip,
            "provider": "docker",
            "region": "local",
            "squad_id": squad_id,
            "price": 0,
            "currency": "USD",
        },
        expected=(200, 409),
    )
    if status == 200:
        return payload["id"]

    _, servers = request("GET", f"/api/v1/squads/{urllib.parse.quote(squad_id)}/servers", expected=(200,))
    for server in servers:
        if server["host"] == host:
            return server["id"]
    raise RuntimeError(f"Could not resolve server id for {host}")


def ensure_node(server_id: str, token: str):
    request(
        "POST",
        "/api/v1/nodes",
        {
            "server_id": server_id,
            "node_token": token,
            "engine_awg2_enabled": True,
            "engine_singbox_enabled": True,
            "desired_config": {"inbounds": []},
        },
        expected=(200, 409),
    )


def main():
    wait_api()
    squad_id = ensure_squad()

    server1 = ensure_server(squad_id, "agent-1.local", "10.240.0.11")
    server2 = ensure_server(squad_id, "agent-2.local", "10.240.0.12")

    ensure_node(server1, NODE_1_TOKEN)
    ensure_node(server2, NODE_2_TOKEN)

    print("Seed complete: squad + 2 servers + 2 nodes")


if __name__ == "__main__":
    main()
