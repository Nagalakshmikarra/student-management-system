# app/models/later.py  (Day 2 / Day 3 tables)

from datetime import date, datetime
from enum import Enum

from pydantic import NaiveDatetime
from sqlmodel import SQLModel, Field


class AttendanceStatus(str, Enum):
    present = "present"
    absent = "absent"
    late = "late"


class ExamType(str, Enum):
    internal = "internal"
    midterm = "midterm"
    final = "final"


class LeaveStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Attendance(SQLModel, table=True):
    __tablename__ = "attendance"

    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.id", index=True)
    subject_id: int = Field(foreign_key="subject.id")
    date: date
    status: AttendanceStatus = AttendanceStatus.present
    marked_by_user_id: int | None = Field(default=None, foreign_key="user.id")


class Exam(SQLModel, table=True):
    __tablename__ = "exam"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=150)
    exam_type: ExamType = ExamType.internal
    section_id: int = Field(foreign_key="section.id")
    max_marks: int = 100


class ExamSchedule(SQLModel, table=True):
    __tablename__ = "exam_schedule"

    id: int | None = Field(default=None, primary_key=True)
    exam_id: int = Field(foreign_key="exam.id")
    subject_id: int = Field(foreign_key="subject.id")
    exam_date: date
    start_time: str = Field(max_length=10)
    end_time: str = Field(max_length=10)


class Mark(SQLModel, table=True):
    __tablename__ = "mark"

    id: int | None = Field(default=None, primary_key=True)
    exam_id: int = Field(foreign_key="exam.id")
    student_id: int = Field(foreign_key="student.id", index=True)
    subject_id: int = Field(foreign_key="subject.id")
    marks_obtained: float


class HallTicket(SQLModel, table=True):
    __tablename__ = "hall_ticket"

    id: int | None = Field(default=None, primary_key=True)
    exam_id: int = Field(foreign_key="exam.id")
    student_id: int = Field(foreign_key="student.id", index=True)
    ticket_no: str = Field(unique=True, max_length=40)
    issued_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class LeaveRequest(SQLModel, table=True):
    __tablename__ = "leave_request"

    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.id", index=True)
    from_date: date
    to_date: date
    reason: str
    status: LeaveStatus = LeaveStatus.pending
    decided_by_user_id: int | None = Field(default=None, foreign_key="user.id")
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)


class Notice(SQLModel, table=True):
    __tablename__ = "notice"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    body: str
    posted_by_user_id: int = Field(foreign_key="user.id")
    department_id: int | None = Field(default=None, foreign_key="department.id")
    created_at: NaiveDatetime = Field(default_factory=datetime.utcnow)