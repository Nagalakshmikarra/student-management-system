# app/models/registration.py

from datetime import date, datetime
from enum import Enum

from sqlmodel import SQLModel, Field


class RegistrationStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    correction = "correction"


class Registration(SQLModel, table=True):
    __tablename__ = "registration"

    id: int | None = Field(default=None, primary_key=True)
    reference_no: str = Field(unique=True, index=True, max_length=30)

    full_name: str = Field(max_length=150)
    dob: date
    gender: str = Field(max_length=20)
    phone: str = Field(max_length=20)
    email: str = Field(max_length=150)
    parent_name: str = Field(max_length=150)

    department_id: int = Field(foreign_key="department.id", index=True)
    quota: str = Field(max_length=30)
    entrance_rank: int | None = None
    tenth_percent: float
    inter_percent: float

    photo_path: str | None = None
    marks_memo_path: str | None = None
    id_proof_path: str | None = None

    status: RegistrationStatus = Field(default=RegistrationStatus.pending)
    hod_remarks: str | None = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    decided_at: datetime | None = None
    decided_by_user_id: int | None = Field(default=None, foreign_key="user.id")
    student_id: int | None = Field(default=None, foreign_key="student.id")