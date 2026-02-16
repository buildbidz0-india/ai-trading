"""Role-Based Access Control (RBAC) — FastAPI dependency factories.

Provides dependency factories that enforce role-based authorization
on protected endpoints.
"""

from __future__ import annotations

from typing import Sequence

from fastapi import Depends, HTTPException, status

from app.dependencies import get_current_user


def require_role(*allowed_roles: str):
    """Create a FastAPI dependency that enforces role-based access.

    Usage:
        @router.post("/admin-only", dependencies=[Depends(require_role("admin"))])
        async def admin_endpoint(): ...
    """

    async def _check_role(user: dict = Depends(get_current_user)) -> dict:
        user_role = user.get("role", "")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {', '.join(allowed_roles)}",
            )
        return user

    return _check_role
