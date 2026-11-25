import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.config import settings
from app.database import create_db_and_tables, engine
from app.models import Batch, Department, MentorGroup, Role, Section, User
from app.security import hash_password

DEPTS = [
    ("CSE", "Computer Science and Engineering"),
    ("ECE", "Electronics and Communication Engineering"),
    ("EEE", "Electrical and Electronics Engineering"),
    ("MECH", "Mechanical Engineering"),
    ("CIVIL", "Civil Engineering"),
]

create_db_and_tables()
year = settings.ADMISSION_YEAR

with Session(engine) as s:
    for code, name in DEPTS:
        if s.exec(select(Department).where(Department.code == code)).first():
            continue
        dept = Department(code=code, name=name)
        s.add(dept)
        s.flush()

        hod = User(username=f"hod.{code.lower()}@college.edu", full_name=f"{code} Head of Department",
                   email=f"hod.{code.lower()}@college.edu", password_hash=hash_password("Hod@123"),
                   role=Role.hod, department_id=dept.id)
        s.add(hod)
        s.flush()
        dept.hod_user_id = hod.id

        batch = Batch(department_id=dept.id, start_year=year, end_year=year + 4)
        s.add(batch)
        s.flush()

        for sec_name in ("A", "B"):
            sec = Section(batch_id=batch.id, name=sec_name, current_year=1, current_semester=1)
            s.add(sec)
            s.flush()
            for g in (1, 2):
                email = f"mentor.{code.lower()}.{sec_name.lower()}{g}@college.edu"
                mentor = User(username=email, full_name=f"{code}-{sec_name} Mentor {g}", email=email,
                              password_hash=hash_password("Mentor@123"), role=Role.mentor,
                              department_id=dept.id)
                s.add(mentor)
                s.flush()
                s.add(MentorGroup(section_id=sec.id, name=f"{code}-{sec_name} Group {g}",
                                  mentor_user_id=mentor.id))
    s.commit()
    print("Seeded departments, HODs, sections, mentor groups.")