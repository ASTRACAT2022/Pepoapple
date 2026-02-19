from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Server, Squad, SubscriptionAlias, User


def resolve_user_by_subscription_token(db: Session, token: str) -> User:
    direct = db.scalar(select(User).where(User.subscription_token == token))
    if direct:
        return direct

    alias = db.scalar(select(SubscriptionAlias).where(SubscriptionAlias.legacy_token == token))
    if not alias:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="subscription_not_found")

    user = db.scalar(select(User).where(User.subscription_token == alias.subscription_token))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="subscription_not_found")
    return user


def build_subscription_payload(db: Session, user: User) -> dict:
    if not user.squad_id:
        return {
            "user_uuid": user.uuid,
            "short_id": user.short_id,
            "endpoints": [],
            "note": "user_has_no_squad",
        }

    squad = db.get(Squad, user.squad_id)
    if not squad:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="squad_not_found")

    servers = db.scalars(select(Server).where(Server.squad_id == squad.id, Server.status == "active")).all()
    endpoints = [
        {
            "host": server.host,
            "ip": server.ip,
            "region": server.region,
            "provider": server.provider,
            "protocols": squad.allowed_protocols,
            "uris": {
                "vless": f"vless://{user.vless_id}@{server.host}:443?encryption=none&flow=xtls-rprx-vision#{squad.name}",
                "awg2": f"awg2://{user.uuid}@{server.host}:51820#{squad.name}",
            },
        }
        for server in servers
    ]

    return {
        "user_uuid": user.uuid,
        "short_id": user.short_id,
        "selection_policy": squad.selection_policy.value,
        "subscription_url": f"/api/v1/subscriptions/{user.subscription_token}",
        "endpoints": endpoints,
    }
