
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import text

from app.config import settings

# Import all models before create_all.
import app.models


connect_args = {}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False,
        "timeout": 30,
    }


engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

    if settings.DATABASE_URL.startswith("sqlite"):
        with engine.begin() as connection:

            duplicates = connection.execute(
                text("""
                    SELECT department_id, admission_year, COUNT(*)
                    FROM roll_counter
                    GROUP BY department_id, admission_year
                    HAVING COUNT(*) > 1
                """)
            ).all()

            if duplicates:
                raise RuntimeError(
                    "Duplicate roll counter records found. "
                    "Resolve them before enabling student approvals: "
                    f"{duplicates}"
                )

            connection.execute(
                text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS
                    uq_roll_counter_department_year
                    ON roll_counter (
                        department_id,
                        admission_year
                    )
                """)
            )


def get_session():
    with Session(engine) as session:
        yield session
