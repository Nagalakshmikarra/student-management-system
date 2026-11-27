
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.config import settings


BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)

APP_BRANDING = "GIST - Student Management System"
COLLEGE_NAME = "GIST"


MENUS = {
    "management": [
        {"label": "Dashboard", "url": "/management"},
        {"label": "Departments", "url": "/management/departments"},
    ],
    "hod": [
        {"label": "Dashboard", "url": "/hod"},
        {"label": "Registrations", "url": "/hod/registrations"},
        {"label": "Students", "url": "/hod/students"},
        {"label": "Mentor groups", "url": "/hod/mentor-groups"},
        {"label": "Subjects", "url": "/hod/subjects"},
        {"label": "Leave requests", "url": "/hod/leaves"},
    ],
    "mentor": [
        {"label": "Dashboard", "url": "/mentor"},
    ],
    "trainer": [
        {"label": "Dashboard", "url": "/trainer"},
    ],
    "student": [
        {"label": "Dashboard", "url": "/student"},
    ],
}


def render(request, name, context=None, user=None, status_code=200):
    ctx = dict(context or {})

    ctx["user"] = user

    # Common application branding for every page
    ctx["app_name"] = APP_BRANDING
    ctx["college_name"] = COLLEGE_NAME

    if user is not None:
        ctx.setdefault(
            "menu",
            MENUS.get(user.role.value, []),
        )

    return templates.TemplateResponse(
        request,
        name,
        ctx,
        status_code=status_code,
    )
