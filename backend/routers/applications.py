"""
Module: routers/applications.py
Purpose: CRUD and status transitions for a user's applications.
         All endpoints are scoped to the authenticated user; cross-user access
         returns 404 rather than 403 to avoid enumeration.
Author: ApplyPilot
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models.application import Application, ApplicationStatus
from models.job import Job
from models.user import User
from schemas.application import ApplicationCreate, ApplicationOut, ApplicationUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["applications"])


def _owned(db: Session, app_id: uuid.UUID, user: User) -> Application:
    """Return a user-owned application or raise 404.

    Returns 404 for both "not found" and "wrong owner" to prevent
    ID-enumeration attacks.

    Args:
        db: Active database session.
        app_id: UUID of the application to look up.
        user: Currently authenticated user.

    Returns:
        The Application ORM instance owned by the user.

    Raises:
        HTTPException: 404 if the application does not exist or belongs
            to a different user.
    """
    obj = db.query(Application).filter(
        Application.id == app_id, Application.user_id == user.id
    ).first()
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return obj


@router.post(
    "",
    response_model=ApplicationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an application for a job",
)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Application:
    """Create a pending application referencing an existing job.

    Args:
        payload: Request body containing the target job_id.
        db: Active database session (injected).
        current_user: Authenticated user (injected).

    Returns:
        The newly created Application with status='pending' and embedded job.

    Raises:
        HTTPException: 404 if the referenced job does not exist.
    """
    if db.get(Job, payload.job_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    app_obj = Application(
        user_id=current_user.id,
        job_id=payload.job_id,
        status=ApplicationStatus.pending,
    )
    db.add(app_obj)
    db.commit()
    db.refresh(app_obj)
    logger.info("Created application %s for user %s", app_obj.id, current_user.id)
    return app_obj


@router.get(
    "",
    response_model=list[ApplicationOut],
    summary="List applications",
)
def list_applications(
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Application]:
    """List the authenticated user's applications, optionally filtered by status.

    Args:
        status_filter: Optional status value to filter by (passed as ?status=).
        db: Active database session (injected).
        current_user: Authenticated user (injected).

    Returns:
        List of Application objects ordered by creation date descending.
    """
    query = db.query(Application).filter(Application.user_id == current_user.id)
    if status_filter is not None:
        query = query.filter(Application.status == status_filter)
    return query.order_by(Application.created_at.desc()).all()


@router.get(
    "/{application_id}",
    response_model=ApplicationOut,
    summary="Get an application",
)
def get_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Application:
    """Return a single owned application or 404.

    Args:
        application_id: UUID path parameter identifying the application.
        db: Active database session (injected).
        current_user: Authenticated user (injected).

    Returns:
        The Application owned by the current user.

    Raises:
        HTTPException: 404 if not found or not owned by the current user.
    """
    return _owned(db, application_id, current_user)


@router.patch(
    "/{application_id}",
    response_model=ApplicationOut,
    summary="Update an application",
)
def update_application(
    application_id: uuid.UUID,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Application:
    """Apply partial updates (including status transitions) to an application.

    Only fields present in the request body are updated. Invalid status
    values are rejected by Pydantic before reaching this handler (422).

    Args:
        application_id: UUID path parameter identifying the application.
        payload: Partial-update body; all fields are optional.
        db: Active database session (injected).
        current_user: Authenticated user (injected).

    Returns:
        The updated Application record.

    Raises:
        HTTPException: 404 if not found or not owned by the current user.
    """
    obj = _owned(db, application_id, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    logger.info("Updated application %s: %s", obj.id, payload.model_dump(exclude_unset=True))
    return obj


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an application",
)
def delete_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete an owned application.

    Args:
        application_id: UUID path parameter identifying the application.
        db: Active database session (injected).
        current_user: Authenticated user (injected).

    Raises:
        HTTPException: 404 if not found or not owned by the current user.
    """
    db.delete(_owned(db, application_id, current_user))
    db.commit()
    logger.info("Deleted application %s for user %s", application_id, current_user.id)
