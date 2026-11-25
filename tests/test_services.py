import os
os.environ.setdefault("SECRET_KEY", "x" * 40)

from datetime import date

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.models import (
    Batch, Department, MentorGroup, Registration, Role, Section, Student, User,
)
from app.services.approval import approve_registration
from app.services.roll_number import next_roll_number


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def make_setup(s, groups=1):
    dept = Department(code="CSE", name="Computer Science")
    s.add(dept); s.flush()
    hod = User(username="hod@c.edu", full_name="HOD", email="hod@c.edu", password_hash="x",
               role=Role.hod, department_id=dept.id)
    s.add(hod); s.flush()
    batch = Batch(department_id=dept.id, start_year=2026, end_year=2030)
    s.add(batch); s.flush()
    sec = Section(batch_id=batch.id, name="A", current_year=1, current_semester=1)
    s.add(sec); s.flush()
    made = []
    for i in range(groups):
        m = User(username=f"m{i}@c.edu", full_name=f"Mentor {i}", email=f"m{i}@c.edu",
                 password_hash="x", role=Role.mentor, department_id=dept.id)
        s.add(m); s.flush()
        g = MentorGroup(section_id=sec.id, name=f"CSE-A Group {i+1}", mentor_user_id=m.id)
        s.add(g); s.flush()
        made.append(g)
    s.commit()
    return dept, hod, sec, made


def make_reg(s, dept, n):
    r = Registration(reference_no=f"REG-2026-{n:05d}", full_name=f"Student {n}", dob=date(2008, 1, 1),
                     gender="Male", phone="9999999999", email=f"s{n}@x.com", parent_name="Parent",
                     department_id=dept.id, quota="convener", tenth_percent=90, inter_percent=90)
    s.add(r); s.commit()
    return r


def test_roll_serials_increase(session):
    dept, *_ = make_setup(session)
    assert next_roll_number(session, dept, 2026) == "26CSE001"
    assert next_roll_number(session, dept, 2026) == "26CSE002"
    assert next_roll_number(session, dept, 2026) == "26CSE003"


def test_full_mentor_group_is_skipped(session):
    dept, hod, sec, groups = make_setup(session, groups=2)
    for i in range(30):  # fill group 1 with 30 students
        u = User(username=f"fill{i}", full_name="f", email="f@x.com", password_hash="x", role=Role.student)
        session.add(u); session.flush()
        session.add(Student(user_id=u.id, roll_number=f"FILL{i}", full_name="f", dob=date(2008, 1, 1),
                            gender="Male", phone="1", email="f@x.com", parent_name="p",
                            department_id=dept.id, batch_id=sec.batch_id, section_id=sec.id,
                            mentor_group_id=groups[0].id, quota="convener", admission_year=2026))
    session.commit()

    result = approve_registration(session, make_reg(session, dept, 1), hod)
    assert result["mentor_group_name"] == groups[1].name


def test_second_approve_fails(session):
    dept, hod, *_ = make_setup(session)
    reg = make_reg(session, dept, 1)
    approve_registration(session, reg, hod)
    with pytest.raises(ValueError):
        approve_registration(session, reg, hod)