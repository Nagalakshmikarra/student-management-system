import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.models import Role, User
from app.security import hash_password

create_db_and_tables()

with Session(engine) as session:
    exists = session.exec(select(User).where(User.username == "management@college.edu")).first()
    if exists:
        print("Admin already exists.")
    else:
        session.add(User(
            username="management@college.edu",
            full_name="Management Admin",
            email="management@college.edu",
            password_hash=hash_password("Admin@123"),
            role=Role.management,
        ))
        session.commit()
        print("Created management@college.edu / Admin@123")