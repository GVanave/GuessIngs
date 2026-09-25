from __future__ import annotations

import uuid

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE, csrf_matches, decode_access_token
from app.models import User

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _token_from_request(request: Request) -> tuple[str | None, bool]:
    """Return (token, from_cookie)."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip(), False
    return request.cookies.get(SESSION_COOKIE), True


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token, from_cookie = _token_from_request(request)
    if not token:
        raise AppError(401, "not_authenticated", "Please sign in to continue.")
    payload = decode_access_token(token)
    if payload is None:
        raise AppError(401, "invalid_session", "Your session has expired. Please sign in again.")
    # Cookie sessions must pass the double-submit CSRF check on state-changing requests.
    if from_cookie and request.method not in SAFE_METHODS:
        if not csrf_matches(request.cookies.get(CSRF_COOKIE), request.headers.get(CSRF_HEADER)):
            raise AppError(403, "csrf_failed", "Your session could not be verified. Please refresh the page.")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, KeyError):
        raise AppError(401, "invalid_session", "Your session has expired. Please sign in again.")
    user = db.get(User, user_id)
    if user is None or not user.is_active or user.token_version != payload.get("ver"):
        raise AppError(401, "invalid_session", "Your session has expired. Please sign in again.")
    return user
