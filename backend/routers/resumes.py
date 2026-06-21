"""
Module: routers/resumes.py
Purpose: Upload, list, and delete user resumes (stored in MinIO).
Dependencies: fastapi, sqlalchemy, services.storage_service
Author: ApplyPilot
"""
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models.resume import Resume
from models.user import User
from schemas.resume import ResumeOut
from services.storage_service import StorageService, get_storage

ALLOWED_RESUME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

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
    if file.content_type not in ALLOWED_RESUME_TYPES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Only PDF and Word documents are accepted")
    safe_name = re.sub(r"[^\w.\-]", "_", file.filename or "resume")
    key = f"{current_user.id}/{uuid.uuid4()}-{safe_name}"
    data = file.file.read()
    url = storage.upload(key, data, file.content_type or "application/octet-stream")
    resume = Resume(user_id=current_user.id, filename=file.filename or "resume",
                    storage_url=url, storage_key=key)
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
    storage: StorageService = Depends(get_storage),
) -> None:
    """Delete a resume owned by the current user. 404 if not found/owned.

    Removes the stored file from MinIO before deleting the database row to
    avoid orphaned objects in object storage.

    Args:
        resume_id: UUID of the resume to delete.
        db: SQLAlchemy database session.
        current_user: Authenticated user from JWT.
        storage: Storage service for removing the file from MinIO.

    Raises:
        HTTPException: 404 if the resume does not exist or belongs to another user.
    """
    resume = db.query(Resume).filter(
        Resume.id == resume_id, Resume.user_id == current_user.id
    ).first()
    if resume is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")
    if resume.storage_key:
        storage.delete(resume.storage_key)
    db.delete(resume)
    db.commit()
