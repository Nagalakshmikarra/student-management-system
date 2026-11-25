from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, func, select

from app.config import settings
from app.database import get_session
from app.models import Department, Registration, RegistrationStatus, Student
from app.templating import BASE_DIR, render

router = APIRouter()

UPLOAD_ROOT = BASE_DIR / "static" / "uploads" / "registrations"
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".pdf"}
MAX_BYTES = 2 * 1024 * 1024
QUOTAS = ["convener", "management", "spot"]
GENDERS = ["Male", "Female", "Other"]
FILE_FIELDS = (("photo", "Photo"), ("marks_memo", "Marks memo"), ("id_proof", "ID proof"))
REQUIRED = {
    "full_name": "Full name", "dob": "Date of birth", "gender": "Gender", "phone": "Phone",
    "email": "Email", "parent_name": "Parent name", "department_id": "Branch",
    "quota": "Quota", "tenth_percent": "10th percentage", "inter_percent": "Intermediate percentage",
}


def form_context(session, values=None, errors=None, action="/register", files_required=True):
    return {
        "departments": session.exec(select(Department).order_by(Department.code)).all(),
        "quotas": QUOTAS, "genders": GENDERS,
        "v": values or {}, "errors": errors or [],
        "action": action, "files_required": files_required,
        "today": date.today().isoformat(),
    }


def validate(form, session):
    errors = []
    v = {k: str(form.get(k, "") or "").strip() for k in
         list(REQUIRED) + ["entrance_rank"]}
    for key, label in REQUIRED.items():
        if not v[key]:
            errors.append(f"{label} is required.")

    if v["phone"] and not (v["phone"].isdigit() and len(v["phone"]) == 10):
        errors.append("Phone must be exactly 10 digits.")

    dob = None
    if v["dob"]:
        try:
            dob = date.fromisoformat(v["dob"])
            t = date.today()
            age = t.year - dob.year - ((t.month, t.day) < (dob.month, dob.day))
            if age < 16:
                errors.append("Student must be at least 16 years old.")
        except ValueError:
            errors.append("Date of birth is invalid.")

    for key, label in (("tenth_percent", "10th percentage"), ("inter_percent", "Intermediate percentage")):
        if v[key]:
            try:
                if not 0 <= float(v[key]) <= 100:
                    errors.append(f"{label} must be between 0 and 100.")
            except ValueError:
                errors.append(f"{label} must be a number.")

    if v["entrance_rank"]:
        if not v["entrance_rank"].isdigit():
            errors.append("Entrance rank must be a whole number.")

    if v["quota"] and v["quota"] not in QUOTAS:
        errors.append("Invalid quota.")

    if v["department_id"]:
        if not v["department_id"].isdigit() or session.get(Department, int(v["department_id"])) is None:
            errors.append("Please choose a valid branch.")

    return v, dob, errors


async def read_upload(upload, label, required):
    """Return (content, extension, error)."""
    if upload is None or not getattr(upload, "filename", ""):
        return (None, None, f"{label} is required." if required else None)
    ext = Path(upload.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return (None, None, f"{label}: only .jpg, .jpeg, .png or .pdf files are allowed.")
    content = await upload.read()
    if len(content) > MAX_BYTES:
        return (None, None, f"{label}: file is too large (maximum 2 MB).")
    if len(content) == 0:
        return (None, None, f"{label}: file is empty.")
    return (content, ext, None)


async def collect_files(form, required):
    files, errors = {}, []
    for key, label in FILE_FIELDS:
        content, ext, err = await read_upload(form.get(key), label, required)
        if err:
            errors.append(err)
        elif content:
            files[key] = (content, ext)
    return files, errors


def save_files(ref, files):
    folder = UPLOAD_ROOT / ref
    folder.mkdir(parents=True, exist_ok=True)
    paths = {}
    for key, (content, ext) in files.items():
        (folder / f"{key}{ext}").write_bytes(content)
        paths[key] = f"uploads/registrations/{ref}/{key}{ext}"
    return paths


@router.get("/register")
def register_page(request: Request, session: Session = Depends(get_session)):
    return render(request, "register/form.html", form_context(session))


@router.post("/register")
async def register_submit(request: Request, session: Session = Depends(get_session)):
    form = await request.form()
    v, dob, errors = validate(form, session)
    files, file_errors = await collect_files(form, required=True)
    errors += file_errors

    if errors:
        return render(request, "register/form.html", form_context(session, v, errors), status_code=400)

    last_id = session.exec(select(func.max(Registration.id))).one() or 0
    ref = f"REG-{settings.ADMISSION_YEAR}-{last_id + 1:05d}"
    paths = save_files(ref, files)

    reg = Registration(
        reference_no=ref, full_name=v["full_name"], dob=dob, gender=v["gender"],
        phone=v["phone"], email=v["email"], parent_name=v["parent_name"],
        department_id=int(v["department_id"]), quota=v["quota"],
        entrance_rank=int(v["entrance_rank"]) if v["entrance_rank"] else None,
        tenth_percent=float(v["tenth_percent"]), inter_percent=float(v["inter_percent"]),
        photo_path=paths.get("photo"), marks_memo_path=paths.get("marks_memo"),
        id_proof_path=paths.get("id_proof"), status=RegistrationStatus.pending,
    )
    session.add(reg)
    session.commit()
    return RedirectResponse(f"/register/done/{ref}", status_code=303)


@router.get("/register/done/{ref}")
def register_done(ref: str, request: Request):
    return render(request, "register/done.html", {"ref": ref})


def status_context(session, ref):
    reg = session.exec(select(Registration).where(Registration.reference_no == ref)).first()
    if not reg:
        return {"ref": ref, "not_found": True}
    dept = session.get(Department, reg.department_id)
    roll = None
    if reg.status == RegistrationStatus.approved and reg.student_id:
        st = session.get(Student, reg.student_id)
        roll = st.roll_number if st else None
    return {"ref": ref, "reg": reg, "dept": dept, "roll": roll}


@router.get("/register/status")
def register_status(request: Request, ref: str = "", session: Session = Depends(get_session)):
    ref = ref.strip().upper()
    if not ref:
        return render(request, "register/status.html", {"ref": ""})
    return render(request, "register/status.html", status_context(session, ref))


@router.get("/register/edit/{ref}")
def edit_page(ref: str, request: Request, session: Session = Depends(get_session)):
    reg = session.exec(select(Registration).where(Registration.reference_no == ref)).first()
    if not reg or reg.status != RegistrationStatus.correction:
        return RedirectResponse(f"/register/status?ref={ref}", status_code=303)
    values = {
        "full_name": reg.full_name, "dob": reg.dob.isoformat(), "gender": reg.gender,
        "phone": reg.phone, "email": reg.email, "parent_name": reg.parent_name,
        "department_id": str(reg.department_id), "quota": reg.quota,
        "entrance_rank": str(reg.entrance_rank or ""), "tenth_percent": str(reg.tenth_percent),
        "inter_percent": str(reg.inter_percent),
    }
    ctx = form_context(session, values, action=f"/register/edit/{ref}", files_required=False)
    ctx.update(editing=True, ref=ref, remarks=reg.hod_remarks)
    return render(request, "register/form.html", ctx)


@router.post("/register/edit/{ref}")
async def edit_submit(ref: str, request: Request, session: Session = Depends(get_session)):
    reg = session.exec(select(Registration).where(Registration.reference_no == ref)).first()
    if not reg or reg.status != RegistrationStatus.correction:
        return RedirectResponse(f"/register/status?ref={ref}", status_code=303)

    form = await request.form()
    v, dob, errors = validate(form, session)
    files, file_errors = await collect_files(form, required=False)
    errors += file_errors
    if errors:
        ctx = form_context(session, v, errors, action=f"/register/edit/{ref}", files_required=False)
        ctx.update(editing=True, ref=ref, remarks=reg.hod_remarks)
        return render(request, "register/form.html", ctx, status_code=400)

    paths = save_files(ref, files)
    reg.full_name, reg.dob, reg.gender = v["full_name"], dob, v["gender"]
    reg.phone, reg.email, reg.parent_name = v["phone"], v["email"], v["parent_name"]
    reg.department_id, reg.quota = int(v["department_id"]), v["quota"]
    reg.entrance_rank = int(v["entrance_rank"]) if v["entrance_rank"] else None
    reg.tenth_percent, reg.inter_percent = float(v["tenth_percent"]), float(v["inter_percent"])
    if "photo" in paths: reg.photo_path = paths["photo"]
    if "marks_memo" in paths: reg.marks_memo_path = paths["marks_memo"]
    if "id_proof" in paths: reg.id_proof_path = paths["id_proof"]
    reg.status = RegistrationStatus.pending
    reg.submitted_at = datetime.utcnow()
    session.add(reg)
    session.commit()
    return RedirectResponse(f"/register/done/{ref}", status_code=303)