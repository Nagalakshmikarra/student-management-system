
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from app.database import get_session
from app.deps import get_current_user
from app.models import User, Registration, RegistrationStatus
from app.templating import render
from app.services.approval import approve_registration


router = APIRouter(
    prefix="/hod",
    tags=["GIST HOD"],
)


def check_hod(user: User):
    if user.role.value != "hod":
        raise HTTPException(
            status_code=403,
            detail="HOD access only",
        )


# HOD DASHBOARD
@router.get("")
def hod_dashboard(
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    check_hod(user)

    registrations = session.exec(
        select(Registration).where(
            Registration.department_id == user.department_id
        )
    ).all()

    stats = {
        "pending": sum(
            r.status == RegistrationStatus.pending
            for r in registrations
        ),
        "approved": sum(
            r.status == RegistrationStatus.approved
            for r in registrations
        ),
        "correction": sum(
            r.status == RegistrationStatus.correction
            for r in registrations
        ),
        "rejected": sum(
            r.status == RegistrationStatus.rejected
            for r in registrations
        ),
    }

    recent_registrations = sorted(
        registrations,
        key=lambda r: r.submitted_at,
        reverse=True,
    )[:5]

    return render(
        request,
        "hod/dashboard.html",
        {
            "stats": stats,
            "recent_registrations": recent_registrations,
            "college_name": "GIST",
            "app_name": "GIST - Student Management System",
        },
        user=user,
    )


# HOD REGISTRATIONS PAGE
@router.get("/registrations")
def hod_registrations(
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    check_hod(user)

    registrations = session.exec(
        select(Registration).where(
            Registration.department_id == user.department_id
        )
    ).all()

    registrations = sorted(
        registrations,
        key=lambda r: r.submitted_at,
        reverse=True,
    )

    return render(
        request,
        "hod/registrations.html",
        {
            "registrations": registrations,
            "college_name": "GIST",
            "app_name": "GIST - Student Management System",
        },
        user=user,
    )


# APPROVE REGISTRATION
@router.post("/registrations/{registration_id}/approve")
def approve_registration_route(
    registration_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    check_hod(user)

    try:
        result = approve_registration(
            session=session,
            registration_id=registration_id,
            hod=user,
        )

        return render(
            request,
            "hod/approval_result.html",
            {
                "result": result,
                "college_name": "GIST",
                "app_name": "GIST - Student Management System",
            },
            user=user,
        )

    except ValueError as exc:
        session.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )
