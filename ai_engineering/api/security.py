"""Minimal API authentication for the AI Engineering Command Center."""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, status


class APIKeyAuth:
    """Bearer-token authentication controlled by an environment variable.

    The service stays convenient for local development when no token is configured,
    but production deployments can require authentication by setting
    AI_ENGINEERING_API_TOKEN.
    """

    def __init__(self, env_name: str = "AI_ENGINEERING_API_TOKEN") -> None:
        self.env_name = env_name

    def require(self, authorization: str | None = Header(default=None)) -> None:
        expected = os.getenv(self.env_name)
        if not expected:
            return
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bearer authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        supplied = authorization.removeprefix("Bearer ").strip()
        if not supplied or not hmac.compare_digest(supplied, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )


api_auth = APIKeyAuth()
