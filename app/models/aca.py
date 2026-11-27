
from datetime import date
from enum import Enum

from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint


class StudentStatus(str, Enum):
    active = "active"
    dropped = "dropped"
    passed_out = "passed_out"


class Department(SQLModel, table=True):
    __tablename__ = "department"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=10)
    name: str = Field(max_length=150)
    hod_user_id: int | None = Field(default=None, foreign_key="user.id")


class Batch(SQLModel, table=True):
    __tablename__ = "batch"

    id: int | None = Field(default=None, primary_key=True)
    department_id: int = Field(foreign_key="department.id", index=True)
    start_year: int
    end_year: int


class Section(SQLModel, table=True):
    __tablename__ = "section"

    id: int | None = Field(default=None, primary_key=True)
    batch_id: int = Field(foreign_key="batch.id", index=True)
    name: str = Field(max_length=10)
    current_year: int = 1
    current_semester: int = 1
    capacity: int = 60


class MentorGroup(SQLModel, table=True):
    __tablename__ = "mentor_group"

    id: int | None = Field(default=None, primary_key=True)
    section_id: int = Field(foreign_key="section.id", index=True)
    name: str = Field(max_length=100)
    mentor_user_id: int = Field(foreign_key="user.id")
    capacity: int = 30


class Student(SQLModel, table=True):
    __tablename__ = "student"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)
    roll_number: str = Field(unique=True, index=True, max_length=30)
    full_name: str = Field(max_length=150)
    dob: date
    gender: str = Field(max_length=20)
    phone: str = Field(max_length=20)
    email: str = Field(max_length=150)
    parent_name: str = Field(max_length=150)
    department_id: int = Field(foreign_key="department.id", index=True)
    batch_id: int = Field(foreign_key="batch.id")
    section_id: int = Field(foreign_key="section.id", index=True)
    mentor_group_id: int | None = Field(
        default=None,
        foreign_key="mentor_group.id",
        index=True,
    )
    quota: str = Field(max_length=30)
    admission_year: int
    status: StudentStatus = Field(default=StudentStatus.active)


class Subject(SQLModel, table=True):
    __tablename__ = "subject"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(max_length=20, index=True)
    name: str = Field(max_length=150)
    department_id: int = Field(foreign_key="department.id", index=True)
    year: int = 1
    semester: int = 1
    credits: int = 3


class TeachingAssignment(SQLModel, table=True):
    __tablename__ = "teaching_assignment"

    id: int | None = Field(default=None, primary_key=True)
    subject_id: int = Field(foreign_key="subject.id")
    section_id: int = Field(foreign_key="section.id")
    trainer_user_id: int = Field(foreign_key="user.id")


class RollCounter(SQLModel, table=True):
    __tablename__ = "roll_counter"

    __table_args__ = (
        UniqueConstraint(
            "department_id",
            "admission_year",
            name="uq_roll_counter_department_year",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    department_id: int = Field(foreign_key="department.id", index=True)
    admission_year: int
    last_serial: int = 0
