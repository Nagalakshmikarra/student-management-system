from sqlmodel import Session, select

from app.models import Department, RollCounter


def next_roll_number(session: Session, department: Department, admission_year: int) -> str:
    # Why a counter table is safer than counting students:
    # counting breaks when students are deleted, dropped or moved (numbers get reused),
    # and two approvals at the same moment would read the same count and create
    # duplicate roll numbers. A counter only ever goes up, so numbers are never reused.
    counter = session.exec(
        select(RollCounter).where(
            RollCounter.department_id == department.id,
            RollCounter.admission_year == admission_year,
        )
    ).first()

    if counter is None:
        counter = RollCounter(department_id=department.id, admission_year=admission_year, last_serial=0)

    counter.last_serial += 1
    session.add(counter)
    session.flush()  # saved in this transaction; the caller commits once at the end

    return f"{admission_year % 100:02d}{department.code}{counter.last_serial:03d}"
    