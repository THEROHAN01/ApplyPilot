"""
Module: scripts/seed.py
Purpose: Idempotent local-dev seed data for ApplyPilot. Creates two users, five
         sample jobs (Indian + global mix), three applications across statuses,
         and one resume row. Safe to run repeatedly — existing rows are skipped.
Dependencies: backend models/config/security (added to sys.path at runtime)
Usage:
    # Postgres must be up (docker compose up -d db) and migrated (alembic upgrade head).
    DATABASE_URL=postgresql+psycopg2://applypilot:applypilot@localhost:5433/applypilot \
        python scripts/seed.py
Author: ApplyPilot
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Make the backend package importable when run from the repo root.
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from sqlalchemy.orm import Session  # noqa: E402

import models  # noqa: F401,E402  (registers all tables on Base.metadata)
from database import SessionLocal  # noqa: E402
from models.application import Application, ApplicationStatus  # noqa: E402
from models.job import Job  # noqa: E402
from models.resume import Resume  # noqa: E402
from models.user import PlanTier, User  # noqa: E402
from security.jwt import hash_password  # noqa: E402

# --------------------------------------------------------------------------- #
# Seed definitions
# --------------------------------------------------------------------------- #
USERS = [
    {"email": "dev@applypilot.local", "password": "DevTest1234!", "name": "Dev User", "plan": PlanTier.free},
    {"email": "pro@applypilot.local", "password": "ProTest1234!", "name": "Pro User", "plan": PlanTier.pro},
]

JOBS = [
    {"source": "greenhouse", "company": "Stripe", "role": "Software Engineer Intern",
     "location": "Remote", "salary_range": "$8k/mo", "jd_url": "https://stripe.com/jobs/swe-intern"},
    {"source": "lever", "company": "Zepto", "role": "Associate Product Manager",
     "location": "Bengaluru, IN", "salary_range": "₹18-24 LPA", "jd_url": "https://zepto.com/careers/apm"},
    {"source": "greenhouse", "company": "Razorpay", "role": "Backend Engineer",
     "location": "Bengaluru, IN", "salary_range": "₹20-30 LPA", "jd_url": "https://razorpay.com/jobs/backend"},
    {"source": "wellfound", "company": "CRED", "role": "Data Analyst",
     "location": "Bengaluru, IN", "salary_range": "₹14-20 LPA", "jd_url": "https://cred.club/careers/data-analyst"},
    {"source": "lever", "company": "Groww", "role": "iOS Developer",
     "location": "Bengaluru, IN", "salary_range": "₹16-26 LPA", "jd_url": "https://groww.in/careers/ios"},
]

# (job index into JOBS, application status)
APPLICATIONS = [
    (0, ApplicationStatus.pending),
    (2, ApplicationStatus.generated),
    (3, ApplicationStatus.sent),
]


def _get_or_create_user(db: Session, spec: dict) -> User:
    """Return the user with this email, creating it if absent.

    Args:
        db: Active database session.
        spec: Dict with email/password/name/plan keys.

    Returns:
        The existing or newly created User.
    """
    user = db.query(User).filter(User.email == spec["email"]).first()
    if user is not None:
        print(f"= user exists: {spec['email']}")
        return user
    user = User(
        email=spec["email"],
        name=spec["name"],
        plan=spec["plan"],
        password_hash=hash_password(spec["password"]),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"+ created user: {spec['email']} (plan={spec['plan'].value})")
    return user


def _get_or_create_job(db: Session, spec: dict) -> Job:
    """Return the job matching (company, role), creating it if absent.

    Args:
        db: Active database session.
        spec: Dict of Job field values.

    Returns:
        The existing or newly created Job.
    """
    job = (
        db.query(Job)
        .filter(Job.company == spec["company"], Job.role == spec["role"])
        .first()
    )
    if job is not None:
        print(f"= job exists: {spec['company']} — {spec['role']}")
        return job
    job = Job(**spec)
    db.add(job)
    db.commit()
    db.refresh(job)
    print(f"+ created job: {spec['company']} — {spec['role']}")
    return job


def _seed_applications(db: Session, user: User, jobs: list[Job]) -> None:
    """Create the sample applications for *user* if they have none yet.

    Args:
        db: Active database session.
        user: Owner of the applications (the free dev user).
        jobs: The seeded jobs, indexed as in JOBS.
    """
    existing = db.query(Application).filter(Application.user_id == user.id).count()
    if existing:
        print(f"= applications exist for {user.email} ({existing}) — skipping")
        return
    for job_idx, status in APPLICATIONS:
        job = jobs[job_idx]
        app_obj = Application(user_id=user.id, job_id=job.id, status=status)
        if status == ApplicationStatus.sent:
            app_obj.sent_at = datetime.now(timezone.utc)
        db.add(app_obj)
        print(f"+ created application: {job.company} — {job.role} [{status.value}]")
    db.commit()


def _seed_resume(db: Session, user: User) -> None:
    """Create one placeholder resume row for *user* if none exists.

    Args:
        db: Active database session.
        user: Owner of the resume.
    """
    if db.query(Resume).filter(Resume.user_id == user.id).first() is not None:
        print(f"= resume exists for {user.email} — skipping")
        return
    resume = Resume(
        user_id=user.id,
        filename="dev_resume.pdf",
        storage_url=f"http://localhost:9000/applypilot/{user.id}/dev_resume.pdf",
        storage_key=f"{user.id}/dev_resume.pdf",
    )
    db.add(resume)
    db.commit()
    print(f"+ created resume row for {user.email} (placeholder storage_url)")


def main() -> None:
    """Seed users, jobs, applications, and a resume. Idempotent."""
    print("=== ApplyPilot seed ===")
    db = SessionLocal()
    try:
        users = [_get_or_create_user(db, spec) for spec in USERS]
        jobs = [_get_or_create_job(db, spec) for spec in JOBS]
        # Applications + resume belong to the free dev user (users[0]).
        _seed_applications(db, users[0], jobs)
        _seed_resume(db, users[0])
    finally:
        db.close()
    print("=== seed complete ===")


if __name__ == "__main__":
    main()
