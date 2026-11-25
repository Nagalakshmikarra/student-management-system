from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, func, select

from app.config import settings
from app.database import get_session
from app.deps import get_current_user
from app.models import User
from app.security import create_access_token, hash_password, verify_password
from app.templating import render

router = APIRouter()

ROLE_HOME = {
    "management": "/management",
    "hod": "/hod",
    "mentor": "/mentor",
    "trainer": "/trainer",
    "student": "/student",
}


@router.get("/login")
def login_page(request: Request):
    return render(request, "login.html")


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    uname = username.strip().lower()
    user = session.exec(select(User).where(func.lower(User.username) == uname)).first()

    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return render(
            request, "login.html",
            {"error": "Wrong username or password", "username": username},
            status_code=401,
        )

    token = create_access_token(user.id, user.role.value)
    target = "/change-password" if user.must_change_password else ROLE_HOME[user.role.value]
    response = RedirectResponse(target, status_code=303)
    response.set_cookie(
        "access_token", token, httponly=True, samesite="lax",
        max_age=settings.ACCESS_TOKEN_MINUTES * 60,
    )
    return response


@router.get("/change-password")
def change_password_page(request: Request, user: User = Depends(get_current_user)):
    return render(request, "change_password.html", user=user)


@router.post("/change-password")
def change_password(
    request: Request,
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    error = None
    if len(new_password) < 8:
        error = "Password must be at least 8 characters."
    elif new_password != confirm_password:
        error = "Passwords do not match."
    if error:
        return render(request, "change_password.html", {"error": error}, user=user, status_code=400)

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    session.add(user)
    session.commit()
    return RedirectResponse(ROLE_HOME[user.role.value], status_code=303)


@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("access_token")
    return response