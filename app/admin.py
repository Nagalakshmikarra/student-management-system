
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from sqlmodel import Session, select
from sqlalchemy import func

from app.database import engine
from app.config import settings
from app.models import (
    User,
    Student,
    Department,
    Batch,
    Section,
    MentorGroup,
    Subject,
    TeachingAssignment,
    Registration,
    Attendance,
    Mark,
    Exam,
    ExamSchedule,
    HallTicket,
    LeaveRequest,
    Notice,
    Role,
)
from app.security import verify_password


# --------------------------------------------------
# ADMIN AUTHENTICATION
# --------------------------------------------------


def is_management(user: User | None) -> bool:
    """Only active Management accounts may use the admin panel.

    Compare the stored value rather than the enum object so that legacy rows
    holding a plain string role are handled consistently.
    """
    if not user or not user.is_active:
        return False

    role = getattr(user.role, "value", user.role)
    return role == Role.management.value


class ManagementAdminAuth(AuthenticationBackend):

    async def login(self, request: Request) -> bool:
        form = await request.form()

        username = str(form.get("username", "")).strip().lower()
        password = str(form.get("password", ""))

        with Session(engine) as session:
            user = session.exec(
                select(User).where(
                    func.lower(User.username) == username
                )
            ).first()

            if (
                not is_management(user)
                or not verify_password(password, user.password_hash)
            ):
                return False

            request.session.clear()
            request.session.update({
                "admin_user_id": user.id
            })

            return True

    async def authenticate(self, request: Request) -> bool:
        user_id = request.session.get("admin_user_id")

        if not user_id:
            return False

        with Session(engine) as session:
            user = session.get(User, user_id)

            return is_management(user)

    async def get_user_id(self, request: Request) -> int | None:
        if "session" not in request.scope:
            return None
        return request.session.get("admin_user_id")

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True


# --------------------------------------------------
# PEOPLE
# --------------------------------------------------

class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    category = "People"

    column_list = [
        User.id,
        User.username,
        User.full_name,
        User.email,
        User.role,
        User.department_id,
        User.is_active,
        User.must_change_password,
    ]

    column_searchable_list = [
        User.username,
        User.role,
        User.full_name,
        User.email,
    ]

    # Detail and export views default to *all* model fields in SQLAdmin.
    # Pin them to the safe list so password hashes can never be displayed.
    column_details_list = column_list
    column_export_list = column_list

    form_columns = [
        User.username,
        User.full_name,
        User.email,
        User.role,
        User.department_id,
        User.is_active,
        User.must_change_password,
    ]

    can_create = False
    can_delete = False


class StudentAdmin(ModelView, model=Student):
    name = "Student"
    name_plural = "Students"
    category = "People"

    column_list = [
        Student.id,
        Student.roll_number,
        Student.full_name,
        Student.email,
        Student.phone,
        Student.department_id,
        Student.section_id,
        Student.status,
    ]

    column_searchable_list = [
        Student.roll_number,
        Student.full_name,
    ]

    form_columns = [
        Student.roll_number,
        Student.full_name,
        Student.dob,
        Student.gender,
        Student.phone,
        Student.email,
        Student.parent_name,
        Student.department_id,
        Student.batch_id,
        Student.section_id,
        Student.mentor_group_id,
        Student.quota,
        Student.admission_year,
        Student.status,
    ]


# --------------------------------------------------
# ACADEMICS
# --------------------------------------------------

class DepartmentAdmin(ModelView, model=Department):
    name = "Department"
    name_plural = "Departments"
    category = "Academics"

    column_list = [
        Department.id,
        Department.code,
        Department.name,
        Department.hod_user_id,
    ]

    column_searchable_list = [
        Department.code,
        Department.name,
    ]


class BatchAdmin(ModelView, model=Batch):
    name = "Batch"
    name_plural = "Batches"
    category = "Academics"

    column_list = [
        Batch.id,
        Batch.department_id,
        Batch.start_year,
        Batch.end_year,
    ]


class SectionAdmin(ModelView, model=Section):
    name = "Section"
    name_plural = "Sections"
    category = "Academics"

    column_list = [
        Section.id,
        Section.batch_id,
        Section.name,
        Section.current_year,
        Section.current_semester,
        Section.capacity,
    ]


class MentorGroupAdmin(ModelView, model=MentorGroup):
    name = "Mentor Group"
    name_plural = "Mentor Groups"
    category = "Academics"

    column_list = [
        MentorGroup.id,
        MentorGroup.section_id,
        MentorGroup.name,
        MentorGroup.mentor_user_id,
        MentorGroup.capacity,
    ]


class SubjectAdmin(ModelView, model=Subject):
    name = "Subject"
    name_plural = "Subjects"
    category = "Academics"

    column_list = [
        Subject.id,
        Subject.code,
        Subject.name,
        Subject.department_id,
        Subject.year,
        Subject.semester,
        Subject.credits,
    ]

    column_searchable_list = [
        Subject.code,
        Subject.name,
    ]


class TeachingAssignmentAdmin(ModelView, model=TeachingAssignment):
    name = "Teaching Assignment"
    name_plural = "Teaching Assignments"
    category = "Academics"

    column_list = [
        TeachingAssignment.id,
        TeachingAssignment.subject_id,
        TeachingAssignment.section_id,
        TeachingAssignment.trainer_user_id,
    ]


# --------------------------------------------------
# ADMISSIONS
# --------------------------------------------------

class RegistrationAdmin(ModelView, model=Registration):
    name = "Registration"
    name_plural = "Registrations"
    category = "Admissions"

    column_list = [
        Registration.id,
        Registration.reference_no,
        Registration.full_name,
        Registration.department_id,
        Registration.quota,
        Registration.status,
        Registration.submitted_at,
    ]

    column_searchable_list = [
        Registration.reference_no,
        Registration.status,
        Registration.full_name,
    ]

    form_columns = [
        Registration.reference_no,
        Registration.full_name,
        Registration.dob,
        Registration.gender,
        Registration.phone,
        Registration.email,
        Registration.parent_name,
        Registration.department_id,
        Registration.quota,
        Registration.entrance_rank,
        Registration.tenth_percent,
        Registration.inter_percent,
        Registration.photo_path,
        Registration.marks_memo_path,
        Registration.id_proof_path,
        Registration.status,
        Registration.hod_remarks,
    ]

    can_delete = False


# --------------------------------------------------
# EXAMS AND ATTENDANCE
# --------------------------------------------------

class AttendanceAdmin(ModelView, model=Attendance):
    name = "Attendance"
    name_plural = "Attendance"
    category = "Exams and Attendance"

    column_list = [
        Attendance.id,
        Attendance.student_id,
        Attendance.subject_id,
        Attendance.date,
        Attendance.status,
        Attendance.marked_by_user_id,
    ]


class MarkAdmin(ModelView, model=Mark):
    name = "Mark"
    name_plural = "Marks"
    category = "Exams and Attendance"

    column_list = [
        Mark.id,
        Mark.exam_id,
        Mark.student_id,
        Mark.subject_id,
        Mark.marks_obtained,
    ]


class ExamAdmin(ModelView, model=Exam):
    name = "Exam"
    name_plural = "Exams"
    category = "Exams and Attendance"

    column_list = [
        Exam.id,
        Exam.name,
        Exam.exam_type,
        Exam.section_id,
        Exam.max_marks,
    ]

    column_searchable_list = [
        Exam.name,
    ]


class ExamScheduleAdmin(ModelView, model=ExamSchedule):
    name = "Exam Schedule"
    name_plural = "Exam Schedules"
    category = "Exams and Attendance"

    column_list = [
        ExamSchedule.id,
        ExamSchedule.exam_id,
        ExamSchedule.subject_id,
        ExamSchedule.exam_date,
        ExamSchedule.start_time,
        ExamSchedule.end_time,
    ]


class HallTicketAdmin(ModelView, model=HallTicket):
    name = "Hall Ticket"
    name_plural = "Hall Tickets"
    category = "Exams and Attendance"

    column_list = [
        HallTicket.id,
        HallTicket.exam_id,
        HallTicket.student_id,
        HallTicket.ticket_no,
        HallTicket.issued_at,
    ]

    column_searchable_list = [
        HallTicket.ticket_no,
    ]


class LeaveRequestAdmin(ModelView, model=LeaveRequest):
    name = "Leave Request"
    name_plural = "Leave Requests"
    category = "Exams and Attendance"

    column_list = [
        LeaveRequest.id,
        LeaveRequest.student_id,
        LeaveRequest.from_date,
        LeaveRequest.to_date,
        LeaveRequest.reason,
        LeaveRequest.status,
        LeaveRequest.created_at,
    ]


class NoticeAdmin(ModelView, model=Notice):
    name = "Notice"
    name_plural = "Notices"
    category = "Exams and Attendance"

    column_list = [
        Notice.id,
        Notice.title,
        Notice.department_id,
        Notice.posted_by_user_id,
        Notice.created_at,
    ]

    column_searchable_list = [
        Notice.title,
        Notice.body,
    ]


# --------------------------------------------------
# REGISTER ADMIN PANEL
# --------------------------------------------------

def setup_admin(app):

    authentication_backend = ManagementAdminAuth(
        secret_key=settings.SECRET_KEY
    )

    admin = Admin(
        app=app,
        engine=engine,
        title="GIST SMS - Administration",
        base_url="/admin",
        authentication_backend=authentication_backend,
    )

    admin.add_view(UserAdmin)
    admin.add_view(StudentAdmin)

    admin.add_view(DepartmentAdmin)
    admin.add_view(BatchAdmin)
    admin.add_view(SectionAdmin)
    admin.add_view(MentorGroupAdmin)
    admin.add_view(SubjectAdmin)
    admin.add_view(TeachingAssignmentAdmin)

    admin.add_view(RegistrationAdmin)

    admin.add_view(AttendanceAdmin)
    admin.add_view(MarkAdmin)
    admin.add_view(ExamAdmin)
    admin.add_view(ExamScheduleAdmin)
    admin.add_view(HallTicketAdmin)
    admin.add_view(LeaveRequestAdmin)
    admin.add_view(NoticeAdmin)

    return admin
