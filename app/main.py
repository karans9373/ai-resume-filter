import logging
import mimetypes
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .database import Base, DATA_DIR, engine, get_db
from .models import JobApplication, JobRequest, JobRole
from .schemas import CandidateSchema, ScreeningResponse
from .services.parsing import extract_text_from_upload
from .services.scoring import deserialize_list, score_candidate, serialize_list


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
SAMPLE_DATA_DIR = PROJECT_DIR / "sample_data"
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI-Powered Resume Screening System")
app.add_middleware(SessionMiddleware, secret_key="demo-hr-dashboard-secret", same_site="lax")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

DEMO_HR_EMAIL = "hr@aetherresume.demo"
DEMO_HR_PASSWORD = "HR12345"
DEMO_HR_NAME = "Ava Sharma"


DEMO_JOB_ROLES = [
    {
        "title": "HR Analytics Engineer",
        "department": "Talent Ops",
        "location": "Noida",
        "employment_type": "Full-time",
        "description": "We need Python, FastAPI, SQL, Git, NLP, machine learning, REST API, HTML, CSS and communication skills.",
    },
    {
        "title": "Demo Recruiter Role",
        "department": "HR Tech",
        "location": "Remote",
        "employment_type": "Full-time",
        "description": "Need Python FastAPI SQL Git communication HTML CSS machine learning and NLP experience.",
    },
    {
        "title": "Product Data Analyst",
        "department": "Analytics",
        "location": "Remote",
        "employment_type": "Full-time",
        "description": "Need Python SQL communication machine learning NLP and REST API skills.",
    },
    {
        "title": "Backend Python Engineer",
        "department": "Engineering",
        "location": "Remote",
        "employment_type": "Full-time",
        "description": "Need Python FastAPI SQL Git NLP machine learning communication REST API.",
    },
]


DEMO_APPLICATIONS = [
    {"job_index": 0, "file_name": "ananya_sharma_resume.txt", "manual_name": "Ananya Sharma", "manual_email": "", "manual_phone": ""},
    {"job_index": 1, "file_name": "sneha_iyer_resume.txt", "manual_name": "Sneha Iyer", "manual_email": "", "manual_phone": ""},
    {"job_index": 2, "file_name": "rahul_verma_resume.txt", "manual_name": "Rahul Verma", "manual_email": "", "manual_phone": ""},
]


def initialize_database() -> None:
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as exc:
        if "already exists" not in str(exc).lower():
            raise


initialize_database()


def build_simple_pdf(text: str) -> bytes:
    def pdf_escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    y_position = 790
    content_lines = ["BT", "/F1 12 Tf", "50 790 Td", "14 TL"]
    for line in text.splitlines():
        safe_line = pdf_escape(line)
        content_lines.append(f"({safe_line}) Tj")
        content_lines.append("T*")
        y_position -= 14
        if y_position <= 60:
            break
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="ignore")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode())
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode()
    )
    return bytes(pdf)


def ensure_demo_resume_pdf() -> None:
    source = SAMPLE_DATA_DIR / "ananya_sharma_resume.txt"
    target = SAMPLE_DATA_DIR / "demo_resume_ananya.pdf"
    if not source.exists() or target.exists():
        return
    target.write_bytes(build_simple_pdf(source.read_text(encoding="utf-8")))


def seed_demo_content() -> None:
    ensure_demo_resume_pdf()
    db = Session(bind=engine)
    try:
        jobs_by_title = {job.title: job for job in db.query(JobRole).all()}
        created_or_existing_jobs: list[JobRole] = []
        for job_payload in DEMO_JOB_ROLES:
            job = jobs_by_title.get(job_payload["title"])
            if not job:
                job = JobRole(**job_payload)
                db.add(job)
                db.flush()
                jobs_by_title[job.title] = job
            created_or_existing_jobs.append(job)
        db.commit()

        if db.query(JobApplication).count() == 0:
            for item in DEMO_APPLICATIONS:
                sample_path = SAMPLE_DATA_DIR / item["file_name"]
                if not sample_path.exists():
                    continue
                content = sample_path.read_bytes()
                parsed_text = extract_text_from_upload(sample_path.name, content)
                application = build_application_record(
                    job=created_or_existing_jobs[item["job_index"]],
                    upload=UploadFile(filename=sample_path.name, file=BytesIO(content)),
                    content=content,
                    parsed_text=parsed_text,
                    manual_name=item["manual_name"],
                    manual_email=item["manual_email"],
                    manual_phone=item["manual_phone"],
                )
                db.add(application)

            db.commit()

            for job in created_or_existing_jobs:
                rerank_job_applications(db, job.id)

        request_source = SAMPLE_DATA_DIR / "ananya_sharma_resume.txt"
        if request_source.exists() and db.query(JobRequest).count() == 0:
            request_content = request_source.read_bytes()
            request_text = extract_text_from_upload(request_source.name, request_content)
            request_payload = score_candidate(request_source.name, request_text, "Future role request based on resume")
            stored_name, stored_path = store_upload(request_content, request_source.name, "job-requests")
            db.add(
                JobRequest(
                    file_name=request_source.name,
                    stored_file_name=stored_name,
                    resume_path=stored_path,
                    candidate_name=request_payload["candidate_name"] or "Ananya Sharma",
                    email=request_payload["email"] or "ananya.sharma@example.com",
                    phone=request_payload["phone"] or "+91 98765 43210",
                    requested_role="Any future Python / AI role related to my resume",
                    summary=short_summary(request_payload),
                    skills=serialize_list(request_payload["skills"]),
                    education=serialize_list(request_payload["education"]),
                    experience_highlights=serialize_list(request_payload["experience_highlights"]),
                    extracted_text=request_payload["extracted_text"],
                )
            )
            db.commit()
    finally:
        db.close()


def get_hr_session(request: Request) -> dict | None:
    return request.session.get("hr_user")


def require_hr_page(request: Request) -> dict:
    hr_user = get_hr_session(request)
    if not hr_user:
        raise HTTPException(status_code=303, detail="login_required")
    return hr_user


def require_hr_api(request: Request) -> dict:
    hr_user = get_hr_session(request)
    if not hr_user:
        raise HTTPException(status_code=401, detail="HR login required.")
    return hr_user


def short_summary(payload: dict) -> str:
    if payload["experience_highlights"]:
        return payload["experience_highlights"][0][:220]
    return payload["extracted_text"][:220]


def store_upload(content: bytes, file_name: str, bucket: str) -> tuple[str, str]:
    directory = UPLOAD_DIR / bucket
    directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{Path(file_name).suffix.lower()}"
    stored_path = directory / stored_name
    stored_path.write_bytes(content)
    return stored_name, str(stored_path)


def serialize_application(application: JobApplication) -> dict:
    return {
        "id": application.id,
        "rank_position": application.rank_position,
        "candidate_name": application.candidate_name,
        "file_name": application.file_name,
        "email": application.email,
        "phone": application.phone,
        "summary": application.summary,
        "skills": deserialize_list(application.skills),
        "education": deserialize_list(application.education),
        "experience_highlights": deserialize_list(application.experience_highlights),
        "skill_score": round(application.skill_score, 2),
        "similarity_score": round(application.similarity_score, 2),
        "experience_score": round(application.experience_score, 2),
        "final_score": round(application.final_score, 2),
        "match_percentage": round(application.match_percentage, 2),
        "resume_url": f"/hr/applications/{application.id}/resume",
        "created_at": application.created_at.isoformat(),
    }


def serialize_job_request(job_request: JobRequest) -> dict:
    return {
        "id": job_request.id,
        "candidate_name": job_request.candidate_name,
        "file_name": job_request.file_name,
        "email": job_request.email,
        "phone": job_request.phone,
        "requested_role": job_request.requested_role,
        "summary": job_request.summary,
        "skills": deserialize_list(job_request.skills),
        "education": deserialize_list(job_request.education),
        "experience_highlights": deserialize_list(job_request.experience_highlights),
        "resume_url": f"/hr/job-requests/{job_request.id}/resume",
        "created_at": job_request.created_at.isoformat(),
    }


def serialize_job(job: JobRole) -> dict:
    applications = sorted(job.applications, key=lambda item: (-item.final_score, item.created_at))
    total_applications = len(applications)
    top_match = round(applications[0].match_percentage, 2) if applications else 0
    average_match = round(sum(item.match_percentage for item in applications) / total_applications, 2) if applications else 0
    return {
        "id": job.id,
        "title": job.title,
        "department": job.department,
        "location": job.location,
        "employment_type": job.employment_type,
        "status": job.status,
        "description": job.description,
        "created_at": job.created_at.isoformat(),
        "total_applications": total_applications,
        "top_match": top_match,
        "average_match": average_match,
        "applications": [serialize_application(item) for item in applications],
    }


def serialize_public_job(job: JobRole) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "department": job.department,
        "location": job.location,
        "employment_type": job.employment_type,
        "description": job.description,
        "status": job.status,
        "application_count": len(job.applications),
    }


def serialize_matched_job(job: JobRole, score_payload: dict) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "department": job.department,
        "location": job.location,
        "employment_type": job.employment_type,
        "description": job.description,
        "status": job.status,
        "match_percentage": score_payload["match_percentage"],
        "skill_score": score_payload["skill_score"],
        "similarity_score": score_payload["similarity_score"],
        "experience_score": score_payload["experience_score"],
        "skills": score_payload["skills"],
        "matched_skills": score_payload.get("matched_skills", []),
        "summary": short_summary(score_payload),
    }


def rerank_job_applications(db: Session, job_id: int) -> None:
    applications = (
        db.query(JobApplication)
        .filter(JobApplication.job_id == job_id)
        .order_by(JobApplication.final_score.desc(), JobApplication.created_at.asc())
        .all()
    )
    for index, application in enumerate(applications, start=1):
        application.rank_position = index
    db.commit()


def build_application_record(
    *,
    job: JobRole,
    upload: UploadFile,
    content: bytes,
    parsed_text: str,
    manual_name: str,
    manual_email: str,
    manual_phone: str,
) -> JobApplication:
    payload = score_candidate(upload.filename, parsed_text, job.description)
    stored_name, stored_path = store_upload(content, upload.filename, f"job-{job.id}")
    return JobApplication(
        job_id=job.id,
        file_name=upload.filename,
        stored_file_name=stored_name,
        resume_path=stored_path,
        candidate_name=manual_name.strip() or payload["candidate_name"],
        email=manual_email.strip() or payload["email"],
        phone=manual_phone.strip() or payload["phone"],
        summary=short_summary(payload),
        skills=serialize_list(payload["skills"]),
        education=serialize_list(payload["education"]),
        experience_highlights=serialize_list(payload["experience_highlights"]),
        extracted_text=payload["extracted_text"],
        skill_score=payload["skill_score"],
        similarity_score=payload["similarity_score"],
        experience_score=payload["experience_score"],
        final_score=payload["final_score"],
        match_percentage=payload["match_percentage"],
        rank_position=0,
    )


@app.on_event("startup")
def app_startup() -> None:
    try:
        seed_demo_content()
    except Exception:
        logger.exception("Demo seed failed during startup.")


@app.exception_handler(HTTPException)
async def hr_login_redirect_handler(request: Request, exc: HTTPException):
    if exc.status_code == 303 and exc.detail == "login_required":
        return RedirectResponse(url="/hr/login", status_code=303)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/", response_class=HTMLResponse)
@app.get("/candidate", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "candidate.html",
        {
            "request": request,
            "sample_job_description": (
                "We are hiring a Python developer with FastAPI, SQL, Git, HTML, CSS, "
                "REST API, NLP, and machine learning experience."
            ),
            "job_count": db.query(JobRole).count(),
            "application_count": db.query(JobApplication).count(),
            "job_request_count": db.query(JobRequest).count(),
        },
    )


@app.get("/candidate/job-request", response_class=HTMLResponse)
def candidate_job_request_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "candidate_job_request.html",
        {
            "request": request,
            "job_count": db.query(JobRole).count(),
            "job_request_count": db.query(JobRequest).count(),
        },
    )


@app.get("/hr", response_class=HTMLResponse)
def hr_portal(request: Request, db: Session = Depends(get_db)):
    job_count = db.query(JobRole).count()
    application_count = db.query(JobApplication).count()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "job_count": job_count,
            "application_count": application_count,
            "job_request_count": db.query(JobRequest).count(),
            "demo_hr_email": DEMO_HR_EMAIL,
            "demo_hr_password": DEMO_HR_PASSWORD,
        },
    )


@app.get("/hr/login", response_class=HTMLResponse)
def hr_login_page(request: Request):
    if get_hr_session(request):
        return RedirectResponse(url="/hr/dashboard", status_code=303)
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "request": request,
            "demo_hr_email": DEMO_HR_EMAIL,
            "demo_hr_password": DEMO_HR_PASSWORD,
            "error": "",
        },
    )


@app.post("/hr/login", response_class=HTMLResponse)
async def hr_login(request: Request, email: str = Form(...), password: str = Form(...)):
    if email.strip().lower() == DEMO_HR_EMAIL and password == DEMO_HR_PASSWORD:
        request.session["hr_user"] = {"name": DEMO_HR_NAME, "email": DEMO_HR_EMAIL}
        return RedirectResponse(url="/hr/dashboard", status_code=303)

    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "request": request,
            "demo_hr_email": DEMO_HR_EMAIL,
            "demo_hr_password": DEMO_HR_PASSWORD,
            "error": "Only the HR demo account can log in here. Use the demo credentials shown below.",
        },
        status_code=401,
    )


@app.get("/hr/demo-login")
def hr_demo_login(request: Request):
    request.session["hr_user"] = {"name": DEMO_HR_NAME, "email": DEMO_HR_EMAIL}
    return RedirectResponse(url="/hr/dashboard", status_code=303)


@app.post("/hr/logout")
def hr_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@app.get("/hr/dashboard", response_class=HTMLResponse)
def hr_dashboard(request: Request, db: Session = Depends(get_db)):
    hr_user = require_hr_page(request)
    jobs = db.query(JobRole).order_by(JobRole.created_at.desc()).all()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "hr_user": hr_user,
            "jobs_count": len(jobs),
            "applications_count": db.query(JobApplication).count(),
            "job_request_count": db.query(JobRequest).count(),
        },
    )


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/hr/jobs")
def hr_jobs(request: Request, db: Session = Depends(get_db)):
    require_hr_api(request)
    jobs = db.query(JobRole).order_by(JobRole.created_at.desc()).all()
    return [serialize_job(job) for job in jobs]


@app.get("/api/public/jobs")
def public_jobs(db: Session = Depends(get_db)):
    jobs = db.query(JobRole).filter(JobRole.status == "Open").order_by(JobRole.created_at.desc()).all()
    return [serialize_public_job(job) for job in jobs]


@app.post("/api/public/match-jobs")
async def match_public_jobs(
    candidate_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    selected_job_id: int | None = Form(None),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await resume.read()
    if not content:
        raise HTTPException(status_code=400, detail="Resume file is required.")

    parsed_text = extract_text_from_upload(resume.filename, content)
    open_jobs = db.query(JobRole).filter(JobRole.status == "Open").order_by(JobRole.created_at.desc()).all()

    matches = []
    selected_job_match = None
    top_overall_match = None
    for job in open_jobs:
        score_payload = score_candidate(resume.filename, parsed_text, job.description)
        serialized_match = serialize_matched_job(job, score_payload)
        if top_overall_match is None or serialized_match["match_percentage"] > top_overall_match["match_percentage"]:
            top_overall_match = serialized_match
        if selected_job_id and job.id == selected_job_id:
            selected_job_match = serialized_match
        if score_payload["match_percentage"] >= 20:
            matches.append(serialized_match)

    matches.sort(key=lambda item: item["match_percentage"], reverse=True)

    top_payload = score_candidate(resume.filename, parsed_text, parsed_text)
    profile = {
        "candidate_name": candidate_name.strip() or top_payload["candidate_name"],
        "email": email.strip() or top_payload["email"],
        "phone": phone.strip() or top_payload["phone"],
        "skills": top_payload["skills"],
        "summary": short_summary(top_payload),
    }

    return {
        "profile": profile,
        "matches": matches,
        "has_matches": bool(matches),
        "selected_job_match": selected_job_match,
        "top_overall_match": top_overall_match,
    }


@app.get("/api/hr/job-requests")
def hr_job_requests(request: Request, db: Session = Depends(get_db)):
    require_hr_api(request)
    requests = db.query(JobRequest).order_by(JobRequest.created_at.desc()).all()
    return [serialize_job_request(item) for item in requests]


@app.post("/api/hr/jobs")
async def create_hr_job(
    request: Request,
    title: str = Form(...),
    department: str = Form(""),
    location: str = Form(""),
    employment_type: str = Form(""),
    description: str = Form(...),
    db: Session = Depends(get_db),
):
    require_hr_api(request)
    if not title.strip() or not description.strip():
        raise HTTPException(status_code=400, detail="Role title and description are required.")

    job = JobRole(
        title=title.strip(),
        department=department.strip(),
        location=location.strip(),
        employment_type=employment_type.strip(),
        description=description.strip(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return serialize_job(job)


@app.patch("/api/hr/jobs/{job_id}")
async def update_hr_job(
    job_id: int,
    request: Request,
    title: str = Form(...),
    department: str = Form(""),
    location: str = Form(""),
    employment_type: str = Form(""),
    status: str = Form("Open"),
    description: str = Form(...),
    db: Session = Depends(get_db),
):
    require_hr_api(request)
    job = db.get(JobRole, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if not title.strip() or not description.strip():
        raise HTTPException(status_code=400, detail="Role title and description are required.")

    job.title = title.strip()
    job.department = department.strip()
    job.location = location.strip()
    job.employment_type = employment_type.strip()
    job.status = status.strip() or "Open"
    job.description = description.strip()
    db.commit()
    db.refresh(job)
    return serialize_job(job)


@app.get("/api/hr/jobs/{job_id}/applications")
def get_job_applications(job_id: int, request: Request, db: Session = Depends(get_db)):
    require_hr_api(request)
    job = db.get(JobRole, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return serialize_job(job)


@app.post("/api/hr/jobs/{job_id}/applications")
async def upload_job_applications(
    job_id: int,
    request: Request,
    resumes: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    require_hr_api(request)
    job = db.get(JobRole, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if not resumes:
        raise HTTPException(status_code=400, detail="Upload at least one resume.")

    created = []
    errors = []
    job_upload_dir = UPLOAD_DIR / f"job-{job.id}"
    job_upload_dir.mkdir(parents=True, exist_ok=True)

    for upload in resumes:
        content = await upload.read()
        if not content:
            errors.append(f"{upload.filename}: empty file.")
            continue

        try:
            parsed_text = extract_text_from_upload(upload.filename, content)
            application = build_application_record(
                job=job,
                upload=upload,
                content=content,
                parsed_text=parsed_text,
                manual_name="",
                manual_email="",
                manual_phone="",
            )
            db.add(application)
            created.append(upload.filename)
        except Exception as exc:
            errors.append(f"{upload.filename}: {exc}")

    if not created:
        db.rollback()
        raise HTTPException(status_code=400, detail={"message": "No resumes could be processed.", "errors": errors})

    db.commit()
    rerank_job_applications(db, job.id)
    db.refresh(job)
    refreshed_job = db.get(JobRole, job.id)
    response = serialize_job(refreshed_job)
    response["uploaded_files"] = created
    response["errors"] = errors
    return response


@app.delete("/api/hr/applications/{application_id}")
def delete_job_application(application_id: int, request: Request, db: Session = Depends(get_db)):
    require_hr_api(request)
    application = db.get(JobApplication, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    job_id = application.job_id
    resume_path = Path(application.resume_path)
    db.delete(application)
    db.commit()

    if resume_path.exists():
        resume_path.unlink()

    rerank_job_applications(db, job_id)
    return {"status": "deleted", "application_id": application_id}


@app.post("/api/public/jobs/{job_id}/apply")
async def apply_to_public_job(
    job_id: int,
    candidate_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    job = db.get(JobRole, job_id)
    if not job or job.status != "Open":
        raise HTTPException(status_code=404, detail="Selected job is not available.")

    content = await resume.read()
    if not content:
        raise HTTPException(status_code=400, detail="Resume file is required.")

    parsed_text = extract_text_from_upload(resume.filename, content)
    application = build_application_record(
        job=job,
        upload=resume,
        content=content,
        parsed_text=parsed_text,
        manual_name=candidate_name,
        manual_email=email,
        manual_phone=phone,
    )
    db.add(application)
    db.commit()
    rerank_job_applications(db, job.id)
    db.refresh(application)
    return {"status": "applied", "job_title": job.title, "application": serialize_application(application)}


@app.post("/api/public/job-requests")
async def create_public_job_request(
    candidate_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    requested_role: str = Form(""),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await resume.read()
    if not content:
        raise HTTPException(status_code=400, detail="Resume file is required.")

    parsed_text = extract_text_from_upload(resume.filename, content)
    payload = score_candidate(resume.filename, parsed_text, requested_role or "General candidate profile request")
    stored_name, stored_path = store_upload(content, resume.filename, "job-requests")

    job_request = JobRequest(
        file_name=resume.filename,
        stored_file_name=stored_name,
        resume_path=stored_path,
        candidate_name=candidate_name.strip() or payload["candidate_name"],
        email=email.strip() or payload["email"],
        phone=phone.strip() or payload["phone"],
        requested_role=requested_role.strip(),
        summary=short_summary(payload),
        skills=serialize_list(payload["skills"]),
        education=serialize_list(payload["education"]),
        experience_highlights=serialize_list(payload["experience_highlights"]),
        extracted_text=payload["extracted_text"],
    )
    db.add(job_request)
    db.commit()
    db.refresh(job_request)
    return {"status": "requested", "job_request": serialize_job_request(job_request)}


@app.get("/hr/applications/{application_id}/resume")
def view_application_resume(application_id: int, request: Request, db: Session = Depends(get_db)):
    require_hr_page(request)
    application = db.get(JobApplication, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Resume not found.")

    resume_path = Path(application.resume_path)
    if not resume_path.exists():
        raise HTTPException(status_code=404, detail="Stored resume file is missing.")

    media_type, _ = mimetypes.guess_type(str(resume_path))
    return FileResponse(str(resume_path), media_type=media_type or "application/octet-stream", filename=application.file_name)


@app.get("/hr/job-requests/{job_request_id}/resume")
def view_job_request_resume(job_request_id: int, request: Request, db: Session = Depends(get_db)):
    require_hr_page(request)
    job_request = db.get(JobRequest, job_request_id)
    if not job_request:
        raise HTTPException(status_code=404, detail="Resume not found.")

    resume_path = Path(job_request.resume_path)
    if not resume_path.exists():
        raise HTTPException(status_code=404, detail="Stored resume file is missing.")

    media_type, _ = mimetypes.guess_type(str(resume_path))
    return FileResponse(str(resume_path), media_type=media_type or "application/octet-stream", filename=job_request.file_name)


@app.post("/api/screen", response_model=ScreeningResponse)
async def screen_resumes(job_description: str = Form(...), resumes: list[UploadFile] = File(...)):
    job_description = job_description.strip()
    if not job_description:
        raise HTTPException(status_code=400, detail="Job description is required.")
    if not resumes:
        raise HTTPException(status_code=400, detail="At least one resume is required.")

    ranked_candidates: list[dict] = []
    for upload in resumes:
        content = await upload.read()
        if not content:
            continue
        parsed_text = extract_text_from_upload(upload.filename, content)
        ranked_candidates.append(score_candidate(upload.filename, parsed_text, job_description))

    ranked_candidates.sort(key=lambda item: item["final_score"], reverse=True)
    payload = []
    for index, item in enumerate(ranked_candidates, start=1):
        payload.append(
            CandidateSchema(
                rank_position=index,
                candidate_name=item["candidate_name"],
                file_name=item["file_name"],
                email=item["email"],
                phone=item["phone"],
                skills=item["skills"],
                education=item["education"],
                experience_highlights=item["experience_highlights"],
                skill_score=item["skill_score"],
                similarity_score=item["similarity_score"],
                experience_score=item["experience_score"],
                final_score=item["final_score"],
                match_percentage=item["match_percentage"],
            )
        )

    return ScreeningResponse(total_candidates=len(payload), ranked_candidates=payload)


@app.get("/api/candidates")
def latest_candidates(db: Session = Depends(get_db)):
    candidates = db.query(JobApplication).order_by(JobApplication.created_at.desc()).limit(25).all()
    return [serialize_application(candidate) for candidate in candidates]
