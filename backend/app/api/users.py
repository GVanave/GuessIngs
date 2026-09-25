from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.auth import _end_session, _start_session
from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas import DeleteAccountIn, PasswordChangeIn, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(body: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.full_name is not None:
        user.full_name = " ".join(body.full_name.split())
    if body.preferences is not None:
        user.preferences = body.preferences.model_dump()
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/password")
def change_password(body: PasswordChangeIn, response: Response, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise AppError(400, "wrong_password", "Your current password is incorrect.")
    user.password_hash = hash_password(body.new_password)
    user.token_version += 1  # signs out all other sessions
    db.commit()
    db.refresh(user)
    return _start_session(response, user)


@router.delete("/me", status_code=204)
def delete_me(body: DeleteAccountIn, response: Response, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    if not verify_password(body.password, user.password_hash):
        raise AppError(400, "wrong_password", "Your password is incorrect.")
    db.delete(user)
    db.commit()
    _end_session(response)
    response.status_code = 204
    return response
