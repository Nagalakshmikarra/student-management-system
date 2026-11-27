import os
from datetime import date
from types import SimpleNamespace

os.environ.setdefault("SECRET_KEY", "x" * 40)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine
from starlette.requests import Request

from app.models import (
    Batch,
    Department,
    Registration,
    RegistrationStatus,
    Role,
    Section,
    Student,
    User,
)
from app.security import hash_password

# Use an isolated in-memory database. Both modules hold a module-level engine,
# so patch them before app.main calls setup_admin().
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SQLModel.metadata.create_all(test_engine)

import app.admin as admin_module
import app.database as database_module

admin_module.engine = test_engine
database_module.engine = test_engine

from app.main import app
from app.templating import templates


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def fresh_admin_session(client: TestClient):
    client.get("/admin/logout")
    yield


@pytest.fixture(scope="module")
def records() -> dict:
    with Session(test_engine) as session:
        management = User(
            username="management@college.edu",
            full_name="Management User",
            email="management@college.edu",
            password_hash=hash_password("AdminPass123"),
            role=Role.management,
        )
        hod = User(
            username="hod@college.edu",
            full_name="HOD User",
            email="hod@college.edu",
            password_hash=hash_password("HodPass123"),
            role=Role.hod,
        )
        mentor = User(
            username="mentor@college.edu",
            full_name="Mentor User",
            email="mentor@college.edu",
            password_hash=hash_password("MentorPass123"),
            role=Role.mentor,
        )
        trainer = User(
            username="trainer@college.edu",
            full_name="Trainer User",
            email="trainer@college.edu",
            password_hash=hash_password("TrainerPass123"),
            role=Role.trainer,
        )
        session.add(management)
        session.add(hod)
        session.add(mentor)
        session.add(trainer)
        session.flush()

        department = Department(code="CSE", name="Computer Science", hod_user_id=hod.id)
        session.add(department)
        session.flush()

        batch = Batch(department_id=department.id, start_year=2026, end_year=2030)
        session.add(batch)
        session.flush()

        section = Section(batch_id=batch.id, name="A")
        session.add(section)
        session.flush()

        student_user = User(
            username="26cse001",
            full_name="Student One",
            email="26cse001@college.edu",
            password_hash=hash_password("StudentPass123"),
            role=Role.student,
        )
        session.add(student_user)
        session.flush()

        student = Student(
            user_id=student_user.id,
            roll_number="26CSE001",
            full_name="Student One",
            dob=date(2008, 1, 1),
            gender="Male",
            phone="9999999999",
            email="26cse001@college.edu",
            parent_name="Parent One",
            department_id=department.id,
            batch_id=batch.id,
            section_id=section.id,
            quota="convener",
            admission_year=2026,
        )
        session.add(student)

        registration = Registration(
            reference_no="REG-2026-00001",
            full_name="Applicant One",
            dob=date(2008, 1, 1),
            gender="Male",
            phone="8888888888",
            email="applicant@college.edu",
            parent_name="Parent One",
            department_id=department.id,
            quota="convener",
            tenth_percent=90,
            inter_percent=90,
            status=RegistrationStatus.pending,
        )
        session.add(registration)
        session.commit()

        # Return plain values: ORM instances are detached when the session closes.
        return {
            "management": {
                "id": management.id,
                "username": management.username,
                "email": management.email,
                "password_hash": management.password_hash,
            },
            "hod": {
                "username": hod.username,
                "password": "HodPass123",
            },
            "mentor": {
                "username": mentor.username,
                "password": "MentorPass123",
            },
            "trainer": {
                "username": trainer.username,
                "password": "TrainerPass123",
            },
            "student": {
                "username": student_user.username,
                "password": "StudentPass123",
                "roll_number": student.roll_number,
                "full_name": student.full_name,
            },
            "registration": {
                "reference_no": registration.reference_no,
            },
        }


def login(client: TestClient, username: str, password: str):
    return client.post(
        "/admin/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def test_admin_requires_login(client: TestClient):
    response = client.get("/admin", follow_redirects=True)

    assert response.status_code == 200
    assert response.url.path == "/admin/login"


def test_management_login_shows_all_menu_groups(client: TestClient, records: dict):
    assert client.get("/admin/login").status_code == 200

    response = login(client, records["management"]["username"], "AdminPass123")

    assert response.status_code == 302
    assert response.headers["location"].endswith("/admin/")

    dashboard = client.get("/admin/")
    assert dashboard.status_code == 200
    for group in ("People", "Academics", "Admissions", "Exams and Attendance"):
        assert group in dashboard.text
    for label in (
        "Users",
        "Students",
        "Departments",
        "Batches",
        "Sections",
        "Mentor Groups",
        "Subjects",
        "Teaching Assignments",
        "Registrations",
        "Attendance",
        "Marks",
        "Exams",
        "Exam Schedules",
        "Hall Tickets",
        "Leave Requests",
        "Notices",
    ):
        assert label in dashboard.text


@pytest.mark.parametrize("role", ["hod", "mentor", "trainer", "student"])
def test_non_management_roles_cannot_log_in_to_admin(
    client: TestClient, records: dict, role: str
):
    account = records[role]
    response = login(client, account["username"], account["password"])

    assert response.status_code == 400
    assert "invalid" in response.text.lower()

    assert client.get("/admin/", follow_redirects=False).status_code in (302, 307)


def test_student_search_by_roll_number(client: TestClient, records: dict):
    login(client, records["management"]["username"], "AdminPass123")

    response = client.get("/admin/student/list", params={"search": "26CSE001"})

    assert response.status_code == 200
    assert "26CSE001" in response.text
    assert "Student One" in response.text


def test_user_search_by_role(client: TestClient, records: dict):
    login(client, records["management"]["username"], "AdminPass123")

    response = client.get("/admin/user/list", params={"search": "management"})

    assert response.status_code == 200
    assert records["management"]["username"] in response.text


def test_registration_search_by_status(client: TestClient, records: dict):
    login(client, records["management"]["username"], "AdminPass123")

    response = client.get(
        "/admin/registration/list", params={"search": "pending"}
    )

    assert response.status_code == 200
    assert records["registration"]["reference_no"] in response.text


def test_password_hash_is_never_displayed_or_editable(
    client: TestClient, records: dict
):
    login(client, records["management"]["username"], "AdminPass123")
    user_id = records["management"]["id"]

    for path in (
        "/admin/user/list",
        f"/admin/user/details/{user_id}",
        f"/admin/user/edit/{user_id}",
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert "password_hash" not in response.text.lower()
        assert records["management"]["password_hash"] not in response.text

    # A crafted POST cannot smuggle a password hash into the edit form.
    response = client.post(
        f"/admin/user/edit/{user_id}",
        data={
            "username": records["management"]["username"],
            "full_name": "Management User",
            "email": records["management"]["email"],
            "role": "management",
            "is_active": "y",
            "password_hash": hash_password("ChangedByAdmin"),
        },
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)

    with Session(test_engine) as session:
        stored = session.get(User, user_id)
        assert stored.password_hash == records["management"]["password_hash"]


def test_admin_link_is_management_only(client: TestClient, records: dict):
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/management",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
        }
    )
    template = templates.env.get_template("base.html")

    def render_for(role: Role) -> str:
        return template.render(
            request=request,
            user=SimpleNamespace(full_name="Test User", role=role),
            menu=[],
            app_name="GIST SMS",
            page_title="Dashboard",
        )

    assert 'href="/admin"' in render_for(Role.management)
    for role in (Role.hod, Role.mentor, Role.trainer, Role.student):
        assert 'href="/admin"' not in render_for(role)


def test_management_dashboard_renders_admin_link(client: TestClient, records: dict):
    response = client.post(
        "/login",
        data={
            "username": records["management"]["username"],
            "password": "AdminPass123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    dashboard = client.get("/management")
    assert dashboard.status_code == 200
    assert 'href="/admin"' in dashboard.text


def test_password_hash_is_not_exported(client: TestClient, records: dict):
    login(client, records["management"]["username"], "AdminPass123")

    response = client.get("/admin/user/export/csv")

    assert response.status_code == 200
    assert "password_hash" not in response.text.lower()
    assert records["management"]["password_hash"] not in response.text


def test_tampered_admin_session_is_rejected(client: TestClient, records: dict):
    login(client, records["management"]["username"], "AdminPass123")
    assert client.get("/admin/").status_code == 200

    client.cookies.set("session", "not-a-signed-session")

    try:
        assert client.get("/admin/", follow_redirects=False).status_code in (302, 307)
    finally:
        # Do not leak the invalid cookie into later tests.
        client.cookies.clear()


def test_user_search_by_username(client: TestClient, records: dict):
    login(client, records["management"]["username"], "AdminPass123")

    response = client.get(
        "/admin/user/list", params={"search": records["student"]["username"]}
    )

    assert response.status_code == 200
    assert records["student"]["username"] in response.text


def test_registration_search_by_reference_no(client: TestClient, records: dict):
    login(client, records["management"]["username"], "AdminPass123")

    response = client.get(
        "/admin/registration/list",
        params={"search": records["registration"]["reference_no"]},
    )

    assert response.status_code == 200
    assert records["registration"]["reference_no"] in response.text


@pytest.mark.parametrize(
    "identity",
    [
        "user",
        "student",
        "department",
        "batch",
        "section",
        "mentor-group",
        "subject",
        "teaching-assignment",
        "registration",
        "attendance",
        "mark",
        "exam",
        "exam-schedule",
        "hall-ticket",
        "leave-request",
        "notice",
    ],
)
def test_every_record_list_is_available(
    client: TestClient, records: dict, identity: str
):
    login(client, records["management"]["username"], "AdminPass123")

    assert client.get(f"/admin/{identity}/list").status_code == 200
