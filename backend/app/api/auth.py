from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import AppError
from app.core.ratelimit import check_limit, rate_limit
from app.core.security import (
    CSRF_COOKIE,
    DUMMY_HASH,
    SESSION_COOKIE,
    create_access_token,
    hash_password,
    new_csrf_token,
    verify_password,
)
from app.models import User
from app.schemas import LoginIn, RegisterIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _start_session(response: Response, user: User) -> dict:
    settings = get_settings()
    token = create_access_token(user.id, user.token_version)
    max_age = settings.access_token_minutes * 60
    common = {"max_age": max_age, "secure": settings.cookie_secure, "samesite": "lax", "path": "/",
              "domain": settings.cookie_domain}
    response.set_cookie(SESSION_COOKIE, token, httponly=True, **common)
    response.set_cookie(CSRF_COOKIE, new_csrf_token(), httponly=False, **common)
    return {"access_token": token, "token_type": "bearer", "user": UserOut.model_validate(user).model_dump(mode="json")}


def _end_session(response: Response) -> None:
    settings = get_settings()
    for name in (SESSION_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path="/", domain=settings.cookie_domain)


@router.post("/register", status_code=201, dependencies=[Depends(rate_limit("auth", "rate_limit_auth_per_minute"))])
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.execute(select(User).where(func.lower(User.email) == email)).scalar_one_or_none():
        raise AppError(409, "email_taken", "An account with this email already exists. Try signing in.")
    user = User(email=email, password_hash=hash_password(body.password), full_name=body.full_name, preferences={})
    db.add(user)
    db.commit()
    db.refresh(user)
    return _start_session(response, user)


@router.post("/login", dependencies=[Depends(rate_limit("auth", "rate_limit_auth_per_minute"))])
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    # Also limit per account, so distributed guessing against one email is throttled.
    check_limit(f"login-email:{body.email.lower()}", get_settings().rate_limit_auth_per_minute * 2, 300)
    user = db.execute(select(User).where(func.lower(User.email) == body.email.lower())).scalar_one_or_none()
    # Always run a bcrypt check so response time does not reveal whether the email exists.
    valid = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid or not user.is_active:
        raise AppError(401, "invalid_credentials", "Incorrect email or password.")
    return _start_session(response, user)


@router.post("/logout", status_code=204)
def logout(response: Response):
    _end_session(response)
    response.status_code = 204
    return response


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
