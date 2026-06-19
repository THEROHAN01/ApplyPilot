"""
Module: routers/resumes.py
Purpose: Upload, list, and delete user resumes (stored in MinIO).
Author: ApplyPilot
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models.resume import Resume
from models.user import User
from schemas.resume import ResumeOut
from services.storage_service import StorageService, get_storage

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("", response_model=ResumeOut, status_code=status.HTTP_201_CREATED,
             summary="Upload a resume")
def upload_resume(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: StorageService = Depends(get_storage),
) -> Resume:
    """Store an uploaded resume file and persist its metadata.

    Args:
        file: Uploaded file from the multipart form.
        db: SQLAlchemy database session.
        current_user: Authenticated user from JWT.
        storage: Storage service for persisting the file.

    Returns:
        The newly created Resume record.
    """
    key = f"{current_user.id}/{uuid.uuid4()}-{file.filename}"
    data = file.file.read()
    url = storage.upload(key, data, file.content_type or "application/octet-stream")
    resume = Resume(user_id=current_user.id, filename=file.filename or "resume", storage_url=url)
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("", response_model=list[ResumeOut], summary="List the user's resumes")
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Resume]:
    """Return all resumes owned by the current user.

    Args:
        db: SQLAlchemy database session.
        current_user: Authenticated user from JWT.

    Returns:
        List of Resume records ordered by creation date descending.
    """
    return db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.created_at.desc()).all()


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a resume")
def delete_resume(
    resume_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a resume owned by the current user. 404 if not found/owned.

    Args:
        resume_id: UUID of the resume to delete.
        db: SQLAlchemy database session.
        current_user: Authenticated user from JWT.

    Raises:
        HTTPException: 404 if the resume does not exist or belongs to another user.
    """
    resume = db.query(Resume).filter(
        Resume.id == resume_id, Resume.user_id == current_user.id
    ).first()
    if resume is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")
    db.delete(resume)
    db.commit()
