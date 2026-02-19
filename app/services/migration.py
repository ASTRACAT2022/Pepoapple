from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    DeviceEvictionPolicy,
    MigrationMode,
    MigrationRun,
    MigrationStatus,
    Server,
    Squad,
    SquadSelectionPolicy,
    SubscriptionAlias,
    User,
)
from app.services.subscription import build_subscription_payload, resolve_user_by_subscription_identifier


def _dry_run(db: Session, payload: dict) -> dict:
    import_users = payload.get("users", [])
    import_servers = payload.get("servers", [])
    import_squads = payload.get("squads", [])
    legacy_tokens = payload.get("legacy_tokens", [])

    existing_user_uuids = {u.uuid for u in db.scalars(select(User)).all()}
    conflicts = [item.get("uuid") for item in import_users if item.get("uuid") in existing_user_uuids]

    return {
        "summary": {
            "users": len(import_users),
            "servers": len(import_servers),
            "squads": len(import_squads),
            "legacy_tokens": len(legacy_tokens),
        },
        "conflicts": {"user_uuids": conflicts},
        "can_apply": len(conflicts) == 0,
    }


def _apply(db: Session, payload: dict) -> dict:
    created = {"users": 0, "servers": 0, "squads": 0, "legacy_tokens": 0}

    squad_map = {}
    for item in payload.get("squads", []):
        existing = db.scalar(select(Squad).where(Squad.name == item["name"]))
        if existing:
            squad_map[item["name"]] = existing.id
            continue
        squad = Squad(
            name=item["name"],
            description=item.get("description", ""),
            selection_policy=SquadSelectionPolicy(item.get("selection_policy", "round-robin")),
            fallback_policy=item.get("fallback_policy", "none"),
            allowed_protocols=item.get("allowed_protocols", ["AWG2", "Sing-box"]),
        )
        db.add(squad)
        db.flush()
        squad_map[item["name"]] = squad.id
        created["squads"] += 1

    for item in payload.get("users", []):
        existing = db.scalar(select(User).where(User.uuid == item["uuid"]))
        if existing:
            continue
        squad_id = item.get("squad_id")
        squad_name = item.get("squad_name")
        if not squad_id and squad_name:
            squad_id = squad_map.get(squad_name)
        user = User(
            uuid=item["uuid"],
            vless_id=item.get("vless_id", item["uuid"]),
            short_id=item.get("short_id", item["uuid"][:8]),
            subscription_token=item["subscription_token"],
            squad_id=squad_id,
            traffic_limit_bytes=item.get("traffic_limit_bytes", 0),
            max_devices=item.get("max_devices", 1),
            external_identities=item.get("external_identities", {}),
            hwid_policy=item.get("hwid_policy", "none"),
            strict_bind=item.get("strict_bind", False),
            device_eviction_policy=DeviceEvictionPolicy(item.get("device_eviction_policy", "reject")),
        )
        db.add(user)
        created["users"] += 1

    for item in payload.get("servers", []):
        existing = db.scalar(select(Server).where(Server.host == item["host"]))
        if existing:
            continue
        squad_id = item.get("squad_id")
        squad_name = item.get("squad_name")
        if not squad_id and squad_name:
            squad_id = squad_map.get(squad_name)
        if not squad_id:
            continue
        server = Server(
            host=item["host"],
            ip=item.get("ip", ""),
            provider=item.get("provider", ""),
            region=item.get("region", ""),
            squad_id=squad_id,
            price=item.get("price", 0),
            currency=item.get("currency", "USD"),
            status=item.get("status", "active"),
        )
        db.add(server)
        created["servers"] += 1

    for item in payload.get("legacy_tokens", []):
        existing = db.scalar(select(SubscriptionAlias).where(SubscriptionAlias.legacy_token == item["legacy_token"]))
        if existing:
            continue
        user = db.scalar(select(User).where(User.uuid == item["user_uuid"]))
        if not user:
            continue
        alias = SubscriptionAlias(
            user_id=user.id,
            legacy_token=item["legacy_token"],
            subscription_token=user.subscription_token,
        )
        db.add(alias)
        created["legacy_tokens"] += 1

    db.commit()
    return {"created": created}


def _verify(db: Session, payload: dict) -> dict:
    checks = []
    for token in payload.get("subscription_tokens", []):
        status = "ok"
        reason = ""
        try:
            user = resolve_user_by_subscription_identifier(db, token)
            subscription = build_subscription_payload(db, user)
            if not isinstance(subscription.get("endpoints", []), list):
                status = "failed"
                reason = "invalid_endpoints"
        except Exception as exc:
            status = "failed"
            reason = str(exc)
        checks.append({"token": token, "status": status, "reason": reason})

    all_ok = all(item["status"] == "ok" for item in checks) if checks else True
    return {"checks": checks, "all_ok": all_ok}


def run_migration(db: Session, mode: MigrationMode, payload: dict) -> MigrationRun:
    record = MigrationRun(mode=mode, status=MigrationStatus.started, details={"input": payload})
    db.add(record)
    db.flush()

    try:
        if mode == MigrationMode.dry_run:
            details = _dry_run(db, payload)
        elif mode == MigrationMode.apply:
            details = _apply(db, payload)
        else:
            details = _verify(db, payload)

        record.status = MigrationStatus.finished
        record.details = details
    except Exception as exc:
        record.status = MigrationStatus.failed
        record.details = {"error": str(exc)}

    record.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return record
