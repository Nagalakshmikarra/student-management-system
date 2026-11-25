from sqlmodel import Session, func, select

from app.models import Batch, Department, MentorGroup, Section, Student


def get_or_create_batch(session: Session, department: Department, admission_year: int) -> Batch:
    batch = session.exec(
        select(Batch).where(Batch.department_id == department.id, Batch.start_year == admission_year)
    ).first()
    if batch is None:
        batch = Batch(department_id=department.id, start_year=admission_year, end_year=admission_year + 4)
        session.add(batch)
        session.flush()
    return batch


def _count_students(session: Session, column, value) -> int:
    return session.exec(select(func.count()).select_from(Student).where(column == value)).one()


def pick_section(session: Session, batch: Batch) -> Section:
    sections = session.exec(select(Section).where(Section.batch_id == batch.id).order_by(Section.name)).all()

    best, best_count = None, None
    for sec in sections:
        count = _count_students(session, Student.section_id, sec.id)
        if count < sec.capacity and (best is None or count < best_count):
            best, best_count = sec, count
    if best:
        return best

    # all full (or none yet): create the next section letter A, B, C...
    new_name = chr(ord("A") + len(sections))
    new_section = Section(batch_id=batch.id, name=new_name, current_year=1, current_semester=1)
    session.add(new_section)
    session.flush()
    return new_section


def pick_mentor_group(session: Session, section: Section) -> MentorGroup | None:
    groups = session.exec(select(MentorGroup).where(MentorGroup.section_id == section.id)).all()

    best, best_count = None, None
    for g in groups:
        count = _count_students(session, Student.mentor_group_id, g.id)
        if count < g.capacity and (best is None or count < best_count):
            best, best_count = g, count
    return best  # None -> HOD sees: "Create a new mentor group for this section"