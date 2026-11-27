from fastapi import APIRouter, Depends, HTTPException, Request

from app.deps import get_current_user
from app.models import User
from app.templating import render

router = APIRouter(
    prefix="/management",
    tags=["GIST Management"],
)


@router.get("")
def management_dashboard(
    request: Request,
    user: User = Depends(get_current_user),
):
    if user.role.value != "management":
        raise HTTPException(status_code=403, detail="Management access only")

    return render(
        request,
        "management/dashboard.html",
        {"page_title": "Dashboard"},
        user=user,
    )
