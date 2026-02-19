from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import ApiKey, ApiKeyStatus, AuthPrincipal, Reseller, RoleName
from app.schemas.auth import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    BootstrapAdminRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.services.audit import write_audit
from app.services.auth import (
    create_token_pair,
    decode_token,
    generate_api_key_secret,
    get_auth_context,
    hash_password,
    principal_scopes,
)
from app.services.rbac import require_scopes

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/bootstrap", response_model=TokenResponse)
def bootstrap_admin(payload: BootstrapAdminRequest, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.scalar(select(AuthPrincipal.id))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="bootstrap_already_completed")

    principal = AuthPrincipal(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=RoleName.super_admin,
        scopes=["*"],
    )
    db.add(principal)
    db.flush()

    write_audit(db, "system", "auth.bootstrap", "auth_principal", principal.id, {"username": principal.username})
    db.commit()

    access, refresh = create_token_pair(principal)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=60 * 30,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    principal = db.scalar(select(AuthPrincipal).where(AuthPrincipal.username == payload.username, AuthPrincipal.is_active.is_(True)))
    if not principal:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")

    from app.services.auth import verify_password

    if not verify_password(payload.password, principal.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")

    access, refresh = create_token_pair(principal)
    write_audit(db, principal.username, "auth.login", "auth_principal", principal.id)
    db.commit()

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=60 * 30,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    claims = decode_token(payload.refresh_token)
    if claims.get("typ") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_refresh_token")

    principal = db.get(AuthPrincipal, claims.get("sub"))
    if not principal or not principal.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="principal_not_found")

    if claims.get("v") != principal.refresh_token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh_token_revoked")

    access, refresh_token = create_token_pair(principal)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh_token,
        expires_in=60 * 30,
    )


@router.get("/me")
def me(ctx=Depends(get_auth_context)) -> dict:
    return {
        "principal_id": ctx.principal_id,
        "role": ctx.role,
        "scopes": sorted(list(ctx.scopes)),
        "reseller_id": ctx.reseller_id,
        "auth_type": ctx.auth_type,
    }


@router.post(
    "/api-keys",
    response_model=ApiKeyCreatedResponse,
    dependencies=[Depends(require_scopes("api.manage"))],
)
def create_api_key(payload: ApiKeyCreate, db: Session = Depends(get_db), ctx=Depends(get_auth_context)) -> ApiKeyCreatedResponse:
    if ctx.auth_type == "dev":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="api_keys_require_real_principal")

    if payload.reseller_id:
        reseller = db.get(Reseller, payload.reseller_id)
        if not reseller:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reseller_not_found")

    secret = generate_api_key_secret()
    owner = db.get(AuthPrincipal, ctx.principal_id)
    if not owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="owner_not_found")
    scopes = payload.scopes or sorted(list(principal_scopes(owner)))

    api_key = ApiKey(
        name=payload.name,
        key_prefix=secret.prefix,
        key_hash=secret.hashed,
        scopes=scopes,
        owner_principal_id=owner.id,
        reseller_id=payload.reseller_id,
        status=ApiKeyStatus.active,
    )
    db.add(api_key)
    db.flush()

    write_audit(
        db,
        ctx.principal_id,
        "api_key.created",
        "api_key",
        api_key.id,
        {"scopes": scopes, "reseller_id": api_key.reseller_id},
    )
    db.commit()

    return ApiKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key=secret.raw,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
    )


@router.get("/api-keys", response_model=list[ApiKeyResponse], dependencies=[Depends(require_scopes("api.manage"))])
def list_api_keys(db: Session = Depends(get_db), ctx=Depends(get_auth_context)) -> list[ApiKey]:
    query = select(ApiKey).where(ApiKey.owner_principal_id == ctx.principal_id).order_by(ApiKey.created_at.desc())
    return db.scalars(query).all()


@router.post("/api-keys/{api_key_id}/revoke", dependencies=[Depends(require_scopes("api.manage"))])
def revoke_api_key(api_key_id: str, db: Session = Depends(get_db), ctx=Depends(get_auth_context)) -> dict:
    api_key = db.get(ApiKey, api_key_id)
    if not api_key or api_key.owner_principal_id != ctx.principal_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="api_key_not_found")

    api_key.status = ApiKeyStatus.revoked
    write_audit(db, ctx.principal_id, "api_key.revoked", "api_key", api_key.id)
    db.commit()
    return {"ok": True}
