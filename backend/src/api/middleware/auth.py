"""Supabase JWT authentication dependency.

Verifies Supabase-issued JWTs on all /api/* routes, extracts `user_id`
from the `sub` claim, and injects it as a typed FastAPI dependency.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, cast

import httpx
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt

from src.config import settings

log = structlog.get_logger(__name__)

_bearer = HTTPBearer(auto_error=False)
_jwks_cache: dict[str, Any] = {}
_jwks_cache_expiry: float = 0.0
_JWKS_CACHE_TTL_SECONDS = 300.0


async def _get_supabase_jwks() -> list[dict[str, Any]]:
    global _jwks_cache, _jwks_cache_expiry

    if _jwks_cache and time.time() < _jwks_cache_expiry:
        cached_keys = _jwks_cache.get("keys", [])
        return cast(list[dict[str, Any]], cached_keys)

    jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        log.warning("supabase.jwks_fetch_failed", jwks_url=jwks_url, error=str(exc))
        raise JWTError("Unable to fetch Supabase JWKS; check SUPABASE_URL/network") from exc

    _jwks_cache = data
    _jwks_cache_expiry = time.time() + _JWKS_CACHE_TTL_SECONDS
    return cast(list[dict[str, Any]], data.get("keys", []))


async def _decode_supabase_token(token: str) -> dict[str, Any]:
    # First try legacy Supabase JWT secret flow (HS256).
    if settings.supabase_jwt_secret:
        try:
            return cast(
                dict[str, Any],
                jwt.decode(
                    token,
                    settings.supabase_jwt_secret,
                    algorithms=["HS256"],
                    options={"verify_aud": False},
                ),
            )
        except JWTError:
            # Fall through to JWKS verification for modern projects.
            pass

    # Then try JWKS-based verification (RS256 / ES256).
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    alg = header.get("alg", "RS256")

    if not kid:
        raise JWTError("Token missing kid header for JWKS verification")

    keys = await _get_supabase_jwks()
    key = next((k for k in keys if k.get("kid") == kid), None)
    if key is None:
        raise JWTError("No matching JWKS key found for token kid")

    return cast(
        dict[str, Any],
        jwt.decode(
            token,
            key,
            algorithms=[alg],
            options={"verify_aud": False},
        ),
    )


async def _get_user_from_supabase_auth(token: str) -> uuid.UUID | None:
    """Fallback validation path via Supabase Auth API.

    This is intentionally used only when local JWT verification fails.
    It avoids hard-failing on provider-side token format/signing differences.
    """
    supabase_auth_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
    api_key = settings.supabase_service_role_key or settings.supabase_anon_key
    if not api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                supabase_auth_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": api_key,
                },
            )
    except httpx.HTTPError as exc:
        log.warning("supabase.auth_user_fetch_failed", error=str(exc))
        return None

    if response.status_code != status.HTTP_200_OK:
        return None

    data = response.json()
    user_id = data.get("id")
    if not user_id:
        return None

    try:
        return uuid.UUID(str(user_id))
    except ValueError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> uuid.UUID:
    """FastAPI dependency — decode and validate the Supabase JWT.

    Returns the authenticated user's UUID extracted from the ``sub`` claim.
    Raises HTTP 401 if the token is missing, malformed, or expired.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )

    token = credentials.credentials
    try:
        payload = await _decode_supabase_token(token)
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        ) from exc
    except JWTError as exc:
        log.warning("jwt.invalid", error=str(exc))
        # Fallback: ask Supabase Auth to validate the token directly.
        user_id = await _get_user_from_supabase_auth(token)
        if user_id is not None:
            return user_id
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive catch for auth infrastructure failures
        log.error("auth.unexpected_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from exc

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub claim",
        )

    try:
        return uuid.UUID(str(sub))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        ) from exc
