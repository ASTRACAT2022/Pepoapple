from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Server, Squad, SquadSelectionPolicy
from app.schemas.squads import ServerCreate, ServerResponse, SquadCreate, SquadResponse
from app.services.audit import write_audit
from app.services.rbac import require_scopes

router = APIRouter(tags=["squads"])


@router.post("/squads", response_model=SquadResponse, dependencies=[Depends(require_scopes("squads.write"))])
def create_squad(payload: SquadCreate, db: Session = Depends(get_db)) -> Squad:
    squad = Squad(
        name=payload.name,
        description=payload.description,
        selection_policy=SquadSelectionPolicy(payload.selection_policy),
        fallback_policy=payload.fallback_policy,
        allowed_protocols=payload.allowed_protocols,
    )
    db.add(squad)
    write_audit(db, "admin", "squad.created", "squad", squad.id, {"name": squad.name})
    db.commit()
    db.refresh(squad)
    return squad


@router.get("/squads", response_model=list[SquadResponse], dependencies=[Depends(require_scopes("users.read"))])
def list_squads(db: Session = Depends(get_db)) -> list[Squad]:
    return db.scalars(select(Squad).order_by(Squad.name)).all()


@router.post("/servers", response_model=ServerResponse, dependencies=[Depends(require_scopes("nodes.control"))])
def create_server(payload: ServerCreate, db: Session = Depends(get_db)) -> Server:
    squad = db.get(Squad, payload.squad_id)
    if not squad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="squad_not_found")

    server = Server(**payload.model_dump())
    db.add(server)
    write_audit(db, "admin", "server.created", "server", server.id, {"squad_id": server.squad_id})
    db.commit()
    db.refresh(server)
    return server


@router.get("/squads/{squad_id}/servers", response_model=list[ServerResponse], dependencies=[Depends(require_scopes("users.read"))])
def list_squad_servers(squad_id: str, db: Session = Depends(get_db)) -> list[Server]:
    squad = db.get(Squad, squad_id)
    if not squad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="squad_not_found")

    return db.scalars(select(Server).where(Server.squad_id == squad_id).order_by(Server.host)).all()
