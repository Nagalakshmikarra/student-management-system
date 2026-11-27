
import secrets
import string
from datetime import datetime

from sqlalchemy import text
from sqlmodel import Session, select

from app.models import (
    User,
    Role,
    Department,
    Registration,
    RegistrationStatus,
    Student,
    StudentStatus,
    Batch,
    Section,
    MentorGroup,
)
from app.security import hash_password


def generate_temporary_password():
    """Generate a random 8-character temporary password."""
    characters = string.ascii_letters + string.digits
    return "".join(secrets.choice(characters) for _ in range(8))


def get_next_section_name(existing_names):
    """Generate A, B, C ... Z, AA, AB ..."""
    number = 1

    while True:
        value = number
        name = ""

        while value > 0:
            value, remainder = divmod(value - 1, 26)
            name = chr(65 + remainder) + name

        if name not in existing_names:
            return name

        number += 1


def allocate_roll_number(
    session: Session,
    department_id: int,
    department_code: str,
    admission_year: int,
):
    """
    Atomically increment the serial counter for one department/year.

    The unique index on roll_counter(department_id, admission_year)
    is created by app/database.py.
    """

    result = session.execute(
        text("""
            INSERT INTO roll_counter
                (department_id, admission_year, last_serial)
            VALUES
                (:department_id, :admission_year, 1)
            ON CONFLICT(department_id, admission_year)
            DO UPDATE SET
                last_serial = roll_counter.last_serial + 1
            RETURNING last_serial
        """),
        {
            "department_id": department_id,
            "admission_year": admission_year,
        },
    )

    serial = result.scalar_one()

    return (
        f"{str(admission_year)[-2:]}"
        f"{department_code.upper()}"
        f"{serial:03d}"
    )


def approve_registration(
    session: Session,
    registration_id: int | Registration,
    hod: User,
):
    """
    Approve a pending registration.

    All changes are committed together. If an operation fails,
    the database transaction is rolled back.
    """

    # Callers may pass either an id or a Registration instance.
    registration_id = getattr(registration_id, "id", registration_id)

    try:
        # Validate HOD.
        if hod.role != Role.hod:
            raise ValueError("Only an HOD can approve registrations.")

        if hod.department_id is None:
            raise ValueError(
                "Your HOD account has no department assigned."
            )

        # Load registration.
        registration = session.get(Registration, registration_id)

        if registration is None:
            raise ValueError("Registration not found.")

        # Restrict HOD to their own department.
        if registration.department_id != hod.department_id:
            raise ValueError(
                "You cannot approve another department's registration."
            )

        # Only pending registrations can be approved.
        if registration.status != RegistrationStatus.pending:
            raise ValueError(
                "This registration has already been processed. "
                "Only pending registrations can be approved."
            )

        department = session.get(
            Department,
            registration.department_id,
        )

        if department is None:
            raise ValueError("Department not found.")

        # Admission year is the current calendar year.
        admission_year = datetime.now().year

        # Allocate roll number.
        roll_number = allocate_roll_number(
            session=session,
            department_id=department.id,
            department_code=department.code,
            admission_year=admission_year,
        )

        # Find or create batch.
        batch = session.exec(
            select(Batch).where(
                Batch.department_id == department.id,
                Batch.start_year == admission_year,
            )
        ).first()

        if batch is None:
            batch = Batch(
                department_id=department.id,
                start_year=admission_year,
                end_year=admission_year + 4,
            )
            session.add(batch)
            session.flush()

        # Find sections in this batch.
        sections = session.exec(
            select(Section).where(
                Section.batch_id == batch.id
            )
        ).all()

        section_choices = []

        for current_section in sections:
            count = len(
                session.exec(
                    select(Student).where(
                        Student.section_id == current_section.id
                    )
                ).all()
            )

            if count < current_section.capacity:
                section_choices.append(
                    (count, current_section)
                )

        # Choose section with fewest students.
        if section_choices:
            section_choices.sort(
                key=lambda item: (item[0], item[1].name)
            )
            section = section_choices[0][1]

        else:
            # All sections are full. Create the next section.
            section_name = get_next_section_name(
                {item.name for item in sections}
            )

            section = Section(
                batch_id=batch.id,
                name=section_name,
                current_year=1,
                current_semester=1,
                capacity=60,
            )

            session.add(section)
            session.flush()

        # Find mentor groups for this section.
        mentor_groups = session.exec(
            select(MentorGroup).where(
                MentorGroup.section_id == section.id
            )
        ).all()

        group_choices = []

        for group in mentor_groups:
            group_count = len(
                session.exec(
                    select(Student).where(
                        Student.mentor_group_id == group.id
                    )
                ).all()
            )

            # Never exceed 30 students, even if capacity is configured higher.
            effective_capacity = min(group.capacity, 30)

            if group_count < effective_capacity:
                group_choices.append((group_count, group))

        selected_group = None
        mentor_name = None

        if group_choices:
            group_choices.sort(
                key=lambda item: (item[0], item[1].name)
            )
            selected_group = group_choices[0][1]

            mentor = session.get(
                User,
                selected_group.mentor_user_id,
            )

            if mentor is None:
                raise ValueError(
                    "The selected mentor account does not exist."
                )

            if mentor.role != Role.mentor:
                raise ValueError(
                    "The selected mentor account does not have the mentor role."
                )

            mentor_name = mentor.full_name

        # Create student login.
        temporary_password = generate_temporary_password()

        student_user = User(
            username=roll_number.lower(),
            full_name=registration.full_name,
            email=registration.email,
            password_hash=hash_password(temporary_password),
            role=Role.student,
            department_id=department.id,
            is_active=True,
            must_change_password=True,
        )

        session.add(student_user)
        session.flush()

        # Create student record.
        student = Student(
            user_id=student_user.id,
            roll_number=roll_number,
            full_name=registration.full_name,
            dob=registration.dob,
            gender=registration.gender,
            phone=registration.phone,
            email=registration.email,
            parent_name=registration.parent_name,
            department_id=department.id,
            batch_id=batch.id,
            section_id=section.id,
            mentor_group_id=(
                selected_group.id if selected_group else None
            ),
            quota=registration.quota,
            admission_year=admission_year,
            status=StudentStatus.active,
        )

        session.add(student)
        session.flush()

        # Update registration.
        registration.status = RegistrationStatus.approved
        registration.decided_at = datetime.utcnow()
        registration.decided_by_user_id = hod.id
        registration.student_id = student.id

        session.add(registration)

        result = {
            "roll_number": roll_number,
            "username": roll_number.lower(),
            "temporary_password": temporary_password,
            "section": section.name,
            "mentor_group": (
                selected_group.name if selected_group else None
            ),
            # Kept for callers using the original result key.
            "mentor_group_name": (
                selected_group.name if selected_group else None
            ),
            "mentor_name": mentor_name,
            "mentor_warning": (
                None
                if selected_group
                else "Create a new mentor group for this section."
            ),
        }

        session.commit()
        return result

    except Exception:
        session.rollback()
        raise
