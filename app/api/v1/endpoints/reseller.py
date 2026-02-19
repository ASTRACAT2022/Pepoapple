from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Reseller, User
from app.schemas.reseller import ResellerCreate, ResellerResponse
from app.services.audit import write_audit
from app.services.auth import AuthContext, get_auth_context
from app.services.rbac import require_scopes

router = APIRouter(prefix="/resellers", tags=["resellers"])


@router.post("", response_model=ResellerResponse, dependencies=[Depends(require_scopes("api.manage"))])
def create_reseller(
    payload: ResellerCreate,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
) -> Reseller:
    reseller = Reseller(name=payload.name, description=payload.description)
    db.add(reseller)
    db.flush()
    write_audit(db, ctx.principal_id, "reseller.created", "reseller", reseller.id)
    db.commit()
    db.refresh(reseller)
    return reseller


@router.get("", response_model=list[ResellerResponse], dependencies=[Depends(require_scopes("api.manage"))])
def list_resellers(db: Session = Depends(get_db)) -> list[Reseller]:
    return db.scalars(select(Reseller).order_by(Reseller.created_at.desc())).all()


@router.post("/{reseller_id}/users/{user_id}", dependencies=[Depends(require_scopes("users.write"))])
def assign_user_to_reseller(
    reseller_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
) -> dict:
    reseller = db.get(Reseller, reseller_id)
    if not reseller:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reseller_not_found")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")

    user.reseller_id = reseller_id
    write_audit(db, ctx.principal_id, "reseller.user_assigned", "user", user.id, {"reseller_id": reseller_id})
    db.commit()
    return {"ok": True}
