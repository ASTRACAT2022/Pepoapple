from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.services.auth import AuthContext, get_auth_context


def require_scopes(*required_scopes: str) -> Callable:
    def checker(ctx: AuthContext = Depends(get_auth_context)) -> None:
        if "*" in ctx.scopes:
            return
        missing = [scope for scope in required_scopes if scope not in ctx.scopes]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "insufficient_scope", "missing": missing},
            )

    return checker
