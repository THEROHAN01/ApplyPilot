"""
Module: routers/jobs.py
Purpose: Job listing with filters/pagination, retrieval, and manual create
         (the scraper populates jobs in Phase 3; manual create supports seeding).
Author: ApplyPilot
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models.job import Job
from models.user import User
from schemas.job import JobCreate, JobList, JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED, summary="Create a job")
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Job:
    """
    Insert a job (manual/seed). Jobs are global, not user-scoped.

    Args:
        payload: Job fields to insert.
        db: Database session from dependency injection.
        current_user: Authenticated user (required; result not stored).

    Returns:
        The newly created Job row.
    """
    job = Job(**payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=JobList, summary="List jobs with filters and pagination")
def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company: str | None = None,
    source: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> JobList:
    """
    Return a paginated, filterable list of jobs ordered by recency.

    Args:
        db: Database session from dependency injection.
        current_user: Authenticated user.
        company: Filter by company name (case-insensitive substring match).
        source: Filter by exact source string (e.g. "greenhouse").
        q: Full-text search on role and company fields.
        page: 1-based page number (must be >= 1).
        page_size: Results per page (1–100, default 20).

    Returns:
        JobList with items, total count, page, and page_size.
    """
    query = db.query(Job)
    if company:
        query = query.filter(Job.company.ilike(f"%{company}%"))
    if source:
        query = query.filter(Job.source == source)
    if q:
        query = query.filter(or_(Job.role.ilike(f"%{q}%"), Job.company.ilike(f"%{q}%")))
    total = query.with_entities(func.count(Job.id)).scalar() or 0
    items = (
        query.order_by(Job.scraped_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return JobList(
        items=[JobOut.model_validate(j) for j in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id}", response_model=JobOut, summary="Get a job by id")
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Job:
    """
    Return a single job or 404.

    Args:
        job_id: UUID of the job to retrieve.
        db: Database session from dependency injection.
        current_user: Authenticated user.

    Returns:
        The Job row.

    Raises:
        HTTPException: 404 if the job does not exist.
    """
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job
