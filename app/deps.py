from fastapi import Depends, HTTPException, Request
from sqlmodel import Session

from app.database import get_session
from app.models import User
from app.security import decode_access_token


class NotLoggedIn(Exception):
    pass


def get_current_user(request: Request, session: Session = Depends(get_session)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise NotLoggedIn()
    payload = decode_access_token(token)
    if not payload:
        raise NotLoggedIn()
    try:
        user = session.get(User, int(payload["sub"]))
    except (KeyError, ValueError):
        raise NotLoggedIn()
    if user is None or not user.is_active:
        raise NotLoggedIn()
    return user


def require_role(*roles):
    allowed = {r.value if hasattr(r, "value") else r for r in roles}

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in allowed:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return checker