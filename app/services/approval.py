import secrets
import string
from datetime import datetime

from sqlmodel import Session

from app.models import (
    Department, Registration, RegistrationStatus, Role, Student, User,
)
from app.security import hash_password
from app.services.placement import get_or_create_batch, pick_mentor_group, pick_section
from app.services.roll_number import next_roll_number


def _temp_password(length: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def approve_registration(session: Session, registration: Registration, hod_user: User) -> dict:
    if registration.status != RegistrationStatus.pending:
        raise ValueError("Only pending registrations can be approved.")
    if hod_user.department_id != registration.department_id:
        raise ValueError("This registration belongs to another department.")

    try:
        department = session.get(Department, registration.department_id)
        year = registration.submitted_at.year if False else _admission_year()

        roll = next_roll_number(session, department, year)
        batch = get_or_create_batch(session, department, year)
        section = pick_section(session, batch)
        group = pick_mentor_group(session, section)

        temp_password = _temp_password()
        user = User(
            username=roll, full_name=registration.full_name, email=registration.email,
            password_hash=hash_password(temp_password), role=Role.student,
            department_id=department.id, must_change_password=True,
        )
        session.add(user)
        session.flush()

        student = Student(
            user_id=user.id, roll_number=roll, full_name=registration.full_name,
            dob=registration.dob, gender=registration.gender, phone=registration.phone,
            email=registration.email, parent_name=registration.parent_name,
            department_id=department.id, batch_id=batch.id, section_id=section.id,
            mentor_group_id=group.id if group else None, quota=registration.quota,
            admission_year=year,
        )
        session.add(student)
        session.flush()

        registration.status = RegistrationStatus.approved
        registration.decided_at = datetime.utcnow()
        registration.decided_by_user_id = hod_user.id
        registration.student_id = student.id
        session.add(registration)

        mentor_name = None
        if group:
            mentor = session.get(User, group.mentor_user_id)
            mentor_name = mentor.full_name if mentor else None

        session.commit()  # single commit at the end
    except Exception:
        session.rollback()
        raise

    return {
        "roll_number": roll,
        "temp_password": temp_password,
        "section_name": section.name,
        "mentor_group_name": group.name if group else None,
        "mentor_name": mentor_name,
        "warning": None if group else "Create a new mentor group for this section",
    }


def _admission_year() -> int:
    from app.config import settings
    return settings.ADMISSION_YEAR