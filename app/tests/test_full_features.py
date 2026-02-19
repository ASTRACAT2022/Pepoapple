import uuid


def make_user_payload(**overrides):
    base_uuid = overrides.pop("uuid", str(uuid.uuid4()))
    payload = {
        "uuid": base_uuid,
        "vless_id": str(uuid.uuid4()),
        "short_id": base_uuid.split("-")[0],
        "squad_id": None,
        "traffic_limit_bytes": 0,
        "max_devices": 1,
        "hwid_policy": "hash",
        "strict_bind": True,
        "device_eviction_policy": "reject",
        "subscription_token": f"tok-{base_uuid.split('-')[0]}",
        "external_identities": {},
    }
    payload.update(overrides)
    return payload


def test_auth_bootstrap_and_api_key_flow(client):
    bootstrap = client.post("/api/v1/auth/bootstrap", json={"username": "root", "password": "secret123"})
    assert bootstrap.status_code == 200, bootstrap.text
    token = bootstrap.json()["access_token"]

    login = client.post("/api/v1/auth/login", json={"username": "root", "password": "secret123"})
    assert login.status_code == 200, login.text

    api_key_resp = client.post(
        "/api/v1/auth/api-keys",
        json={"name": "integration", "scopes": ["users.read", "users.write"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert api_key_resp.status_code == 200, api_key_resp.text
    api_key = api_key_resp.json()["key"]

    me = client.get("/api/v1/auth/me", headers={"X-API-Key": api_key})
    assert me.status_code == 200
    assert me.json()["auth_type"] == "api_key"


def test_hwid_strict_and_evict_policy(client, admin_headers):
    user1_resp = client.post("/api/v1/users", json=make_user_payload(), headers=admin_headers)
    assert user1_resp.status_code == 200
    user1_id = user1_resp.json()["id"]

    d1 = client.post(
        f"/api/v1/users/{user1_id}/devices/register",
        json={"device_hash": "dev-a"},
        headers=admin_headers,
    )
    assert d1.status_code == 200
    d2 = client.post(
        f"/api/v1/users/{user1_id}/devices/register",
        json={"device_hash": "dev-b"},
        headers=admin_headers,
    )
    assert d2.status_code == 409

    user2_resp = client.post(
        "/api/v1/users",
        json=make_user_payload(max_devices=1, device_eviction_policy="evict_oldest", strict_bind=True),
        headers=admin_headers,
    )
    user2_id = user2_resp.json()["id"]
    client.post(f"/api/v1/users/{user2_id}/devices/register", json={"device_hash": "old"}, headers=admin_headers)
    d3 = client.post(
        f"/api/v1/users/{user2_id}/devices/register",
        json={"device_hash": "new"},
        headers=admin_headers,
    )
    assert d3.status_code == 200

    all_devices = client.get(f"/api/v1/users/{user2_id}/devices", headers=admin_headers).json()
    active_hashes = [x["device_hash"] for x in all_devices if x["is_active"]]
    assert active_hashes == ["new"]


def test_webhook_registration_and_delivery_attempt(client, admin_headers):
    endpoint = client.post(
        "/api/v1/webhooks/endpoints",
        json={
            "name": "local-test",
            "target_url": "http://127.0.0.1:9/hook",
            "secret": "abc",
            "events": ["user.created"],
        },
        headers=admin_headers,
    )
    assert endpoint.status_code == 200

    user_resp = client.post(
        "/api/v1/users",
        json=make_user_payload(),
        headers=admin_headers,
    )
    assert user_resp.status_code == 200

    process = client.post("/api/v1/webhooks/process", headers=admin_headers)
    assert process.status_code == 200
    assert process.json()["processed"] >= 1

    deliveries = client.get("/api/v1/webhooks/deliveries", headers=admin_headers)
    assert deliveries.status_code == 200
    assert len(deliveries.json()) >= 1


def test_migration_modes_and_graphql(client, admin_headers):
    dry_run = client.post(
        "/api/v1/migration/run",
        json={"mode": "dry-run", "payload": {"users": [{"uuid": "u1"}], "servers": [], "squads": []}},
        headers=admin_headers,
    )
    assert dry_run.status_code == 200
    assert dry_run.json()["status"] == "finished"

    apply = client.post(
        "/api/v1/migration/run",
        json={
            "mode": "apply",
            "payload": {
                "squads": [{"name": "MIG-S1"}],
                "users": [
                    {
                        "uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                        "vless_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                        "short_id": "aa11bb22",
                        "subscription_token": "migr-tok",
                        "squad_name": "MIG-S1",
                    }
                ],
                "servers": [{"host": "mig1.example.com", "squad_name": "MIG-S1"}],
                "legacy_tokens": [{"user_uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "legacy_token": "legacy-migr"}],
            },
        },
        headers=admin_headers,
    )
    assert apply.status_code == 200
    assert apply.json()["status"] == "finished"

    verify = client.post(
        "/api/v1/migration/run",
        json={"mode": "verify", "payload": {"subscription_tokens": ["legacy-migr"]}},
        headers=admin_headers,
    )
    assert verify.status_code == 200
    assert verify.json()["status"] == "finished"

    gql = client.post("/graphql", json={"query": "{ users { id uuid } }"})
    assert gql.status_code == 200
    assert "data" in gql.json()
