from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.subscription import build_subscription_payload, resolve_user_by_subscription_token

router = APIRouter(tags=["subscription"])


@router.get("/subscriptions/{token}")
def subscription(token: str, db: Session = Depends(get_db)) -> dict:
    user = resolve_user_by_subscription_token(db, token)
    return build_subscription_payload(db, user)
