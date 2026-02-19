import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncGenerator, Optional

import strawberry
from sqlalchemy import desc, select

from app.db.session import SessionLocal
from app.models import AuditLog, Node, Plan, Squad, User


@strawberry.type
class UserType:
    id: str
    uuid: str
    short_id: str
    status: str
    subscription_token: str


@strawberry.type
class PlanType:
    id: str
    name: str
    price: float
    currency: str


@strawberry.type
class NodeType:
    id: str
    status: str
    desired_config_revision: int
    applied_config_revision: int


@strawberry.type
class SquadType:
    id: str
    name: str
    selection_policy: str


@strawberry.type
class AuditEventType:
    id: str
    action: str
    entity_type: str
    entity_id: str
    created_at: datetime


@strawberry.input
class CreatePlanInput:
    name: str
    price: float
    currency: str = "USD"
    duration_days: int = 30
    traffic_limit_bytes: int = 0
    max_devices: int = 1


@strawberry.type
class Query:
    @strawberry.field
    def users(self, limit: int = 50, offset: int = 0) -> list[UserType]:
        with SessionLocal() as db:
            users = db.scalars(select(User).order_by(desc(User.created_at)).offset(offset).limit(limit)).all()
            return [
                UserType(
                    id=user.id,
                    uuid=user.uuid,
                    short_id=user.short_id,
                    status=user.status.value,
                    subscription_token=user.subscription_token,
                )
                for user in users
            ]

    @strawberry.field
    def plans(self) -> list[PlanType]:
        with SessionLocal() as db:
            plans = db.scalars(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.created_at.desc())).all()
            return [PlanType(id=plan.id, name=plan.name, price=plan.price, currency=plan.currency) for plan in plans]

    @strawberry.field
    def nodes(self) -> list[NodeType]:
        with SessionLocal() as db:
            nodes = db.scalars(select(Node).order_by(Node.last_seen_at.desc().nullslast())).all()
            return [
                NodeType(
                    id=node.id,
                    status=node.status.value,
                    desired_config_revision=node.desired_config_revision,
                    applied_config_revision=node.applied_config_revision,
                )
                for node in nodes
            ]

    @strawberry.field
    def squads(self) -> list[SquadType]:
        with SessionLocal() as db:
            squads = db.scalars(select(Squad).order_by(Squad.name.asc())).all()
            return [SquadType(id=s.id, name=s.name, selection_policy=s.selection_policy.value) for s in squads]


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_plan(self, input: CreatePlanInput) -> PlanType:
        with SessionLocal() as db:
            plan = Plan(
                name=input.name,
                price=input.price,
                currency=input.currency,
                duration_days=input.duration_days,
                traffic_limit_bytes=input.traffic_limit_bytes,
                max_devices=input.max_devices,
            )
            db.add(plan)
            db.commit()
            db.refresh(plan)
            return PlanType(id=plan.id, name=plan.name, price=plan.price, currency=plan.currency)


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def audit_events(self, poll_seconds: float = 1.5) -> AsyncGenerator[AuditEventType, None]:
        last_id: Optional[str] = None
        while True:
            with SessionLocal() as db:
                query = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(1)
                event = db.scalar(query)
                if event and event.id != last_id:
                    last_id = event.id
                    yield AuditEventType(
                        id=event.id,
                        action=event.action,
                        entity_type=event.entity_type,
                        entity_id=event.entity_id,
                        created_at=event.created_at,
                    )
            await asyncio.sleep(poll_seconds)


schema = strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)
