from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from urllib.parse import quote

from app.models import Server, Squad, SubscriptionAlias, User


def resolve_user_by_subscription_identifier(db: Session, identifier: str) -> User:
    direct = db.scalar(select(User).where(User.subscription_token == identifier))
    if direct:
        return direct

    alias = db.scalar(select(SubscriptionAlias).where(SubscriptionAlias.legacy_token == identifier))
    if not alias:
        # Remnawave style short links often use short uuid/id instead of token.
        by_short_id = db.scalar(
            select(User).where(User.short_id == identifier).order_by(User.created_at.desc()).limit(1)
        )
        if by_short_id:
            return by_short_id
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


def subscription_links(base_url: str, identifier: str) -> dict:
    sub_url = f"{base_url.rstrip('/')}/api/v1/subscriptions/{identifier}"
    encoded = quote(sub_url, safe="")
    singbox_name = quote("Pepoapple", safe="")
    return {
        "subscription_url": sub_url,
        "sing_box": f"sing-box://import-remote-profile?url={encoded}#{singbox_name}",
        "hiddify": f"hiddify://import/{sub_url}",
        "clash": f"clash://install-config?url={encoded}",
        "v2rayng": f"v2rayng://install-config?url={encoded}",
        "v2rayn": f"v2rayn://install-sub?url={encoded}",
        "streisand": f"streisand://import/{sub_url}",
        "shadowrocket": f"shadowrocket://add/sub://{encoded}",
    }
