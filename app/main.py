from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from strawberry.fastapi import GraphQLRouter

from app.api.v1.router import agent_router, api_router
from app.core.config import get_settings
from app.core.rate_limit import RateLimitMiddleware
from app.db.init_db import init_db
from app.graphql.schema import schema

settings = get_settings()
@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(RateLimitMiddleware)


@app.exception_handler(IntegrityError)
async def integrity_handler(_: Request, exc: IntegrityError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"error": "integrity_error", "detail": str(exc.orig)})


app.include_router(api_router)
app.include_router(agent_router)
app.include_router(GraphQLRouter(schema), prefix="/graphql")
