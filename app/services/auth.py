import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import ApiKey, ApiKeyStatus, AuthPrincipal, RoleName

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

ROLE_SCOPES = {
    RoleName.super_admin: ["*"],
    RoleName.admin: ["users.read", "users.write", "nodes.control", "squads.write", "api.manage", "migration.run"],
    RoleName.operator: ["users.read", "users.write", "nodes.control", "squads.write"],
    RoleName.billing_manager: ["billing.read", "billing.write", "infra.billing.read"],
    RoleName.support: ["users.read", "users.write", "billing.read"],
    RoleName.reseller: ["users.read", "users.write", "billing.read"],
    RoleName.user: ["users.read"],
}


@dataclass
class AuthContext:
    principal_id: str
    scopes: set[str]
    role: str
    reseller_id: Optional[str] = None
    auth_type: str = "bearer"


@dataclass
class ApiKeySecret:
    raw: str
    prefix: str
    hashed: str


settings = get_settings()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _create_token(payload: dict, expires_delta: timedelta) -> str:
    now = _now()
    to_encode = payload.copy()
    to_encode.update({"iat": int(now.timestamp()), "exp": int((now + expires_delta).timestamp())})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def role_scopes(role: RoleName) -> set[str]:
    return set(ROLE_SCOPES.get(role, []))


def principal_scopes(principal: AuthPrincipal) -> set[str]:
    explicit_scopes = set(principal.scopes or [])
    return explicit_scopes | role_scopes(principal.role)


def create_token_pair(principal: AuthPrincipal) -> tuple[str, str]:
    scopes = list(principal_scopes(principal))
    access = _create_token(
        {
            "sub": principal.id,
            "typ": "access",
            "role": principal.role.value,
            "scopes": scopes,
            "reseller_id": principal.reseller_id,
        },
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh = _create_token(
        {
            "sub": principal.id,
            "typ": "refresh",
            "v": principal.refresh_token_version,
        },
        timedelta(days=settings.refresh_token_expire_days),
    )
    return access, refresh


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token") from exc


def authenticate_principal(db: Session, username: str, password: str) -> AuthPrincipal:
    principal = db.scalar(select(AuthPrincipal).where(AuthPrincipal.username == username, AuthPrincipal.is_active.is_(True)))
    if not principal or not verify_password(password, principal.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    return principal


def generate_api_key_secret() -> ApiKeySecret:
    raw = f"ppa_{secrets.token_urlsafe(32)}"
    prefix = raw[:12]
    hashed = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return ApiKeySecret(raw=raw, prefix=prefix, hashed=hashed)


def _from_api_key(db: Session, api_key_raw: str) -> AuthContext:
    key_hash = hashlib.sha256(api_key_raw.encode("utf-8")).hexdigest()
    api_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.status == ApiKeyStatus.active))
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_api_key")
    api_key.last_used_at = _now()
    db.commit()
    return AuthContext(
        principal_id=api_key.owner_principal_id,
        scopes=set(api_key.scopes or []),
        role="api_key",
        reseller_id=api_key.reseller_id,
        auth_type="api_key",
    )


def _from_bearer(db: Session, bearer_token: str) -> AuthContext:
    claims = decode_token(bearer_token)
    if claims.get("typ") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token_type")

    principal = db.get(AuthPrincipal, claims.get("sub"))
    if not principal or not principal.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="principal_not_found")

    return AuthContext(
        principal_id=principal.id,
        scopes=set(claims.get("scopes", [])),
        role=claims.get("role", principal.role.value),
        reseller_id=claims.get("reseller_id"),
        auth_type="bearer",
    )


def _from_dev_scopes(x_scopes: Optional[str]) -> Optional[AuthContext]:
    if not x_scopes:
        return None
    scopes = {scope.strip() for scope in x_scopes.split(",") if scope.strip()}
    return AuthContext(principal_id="dev", scopes=scopes, role="dev", auth_type="dev")


def get_auth_context(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    x_scopes: Optional[str] = Header(default=None, alias="X-Scopes"),
) -> AuthContext:
    dev_ctx = _from_dev_scopes(x_scopes)
    if dev_ctx:
        return dev_ctx

    if x_api_key:
        return _from_api_key(db, x_api_key)

    if authorization and authorization.startswith("Bearer "):
        return _from_bearer(db, authorization.removeprefix("Bearer ").strip())

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="auth_required")


def get_optional_auth_context(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    x_scopes: Optional[str] = Header(default=None, alias="X-Scopes"),
) -> Optional[AuthContext]:
    if not authorization and not x_api_key and not x_scopes:
        return None
    return get_auth_context(db=db, authorization=authorization, x_api_key=x_api_key, x_scopes=x_scopes)
