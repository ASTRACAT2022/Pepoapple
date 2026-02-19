from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import ProtocolProfile, ProtocolType
from app.schemas.protocols import ProtocolProfileCreate, ProtocolProfileResponse
from app.services.auth import AuthContext, get_auth_context
from app.services.rbac import require_scopes

router = APIRouter(prefix="/protocols", tags=["protocols"])


@router.post("", response_model=ProtocolProfileResponse, dependencies=[Depends(require_scopes("nodes.control"))])
def create_protocol_profile(
    payload: ProtocolProfileCreate,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
) -> ProtocolProfile:
    try:
        protocol_type = ProtocolType(payload.protocol_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_protocol_type") from exc

    profile = ProtocolProfile(name=payload.name, protocol_type=protocol_type, schema_json=payload.profile_schema)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("", response_model=list[ProtocolProfileResponse], dependencies=[Depends(require_scopes("nodes.control"))])
def list_protocol_profiles(db: Session = Depends(get_db)) -> list[ProtocolProfile]:
    return db.scalars(select(ProtocolProfile).order_by(desc(ProtocolProfile.created_at))).all()
