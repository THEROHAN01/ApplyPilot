"""
Module: services/storage_service.py
Purpose: S3-compatible object storage (MinIO) for resume files.
Dependencies: minio
Author: ApplyPilot
"""
import io

from minio import Minio
from minio.error import S3Error

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class StorageService:
    """Wrapper around a MinIO/S3 bucket for file upload and deletion."""

    def __init__(self) -> None:
        self._client = Minio(
            settings.s3_endpoint, access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key, secure=settings.s3_secure,
        )
        self._bucket = settings.s3_bucket

    def ensure_bucket(self) -> None:
        """Create the configured bucket if it does not exist."""
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def upload(self, key: str, data: bytes, content_type: str) -> str:
        """Upload bytes under key and return a retrievable URL.

        Args:
            key: Object key path within the bucket.
            data: Raw file bytes to upload.
            content_type: MIME type of the file (e.g. 'application/pdf').

        Returns:
            A full URL string pointing to the uploaded object.
        """
        self.ensure_bucket()
        self._client.put_object(
            self._bucket, key, io.BytesIO(data), length=len(data), content_type=content_type
        )
        scheme = "https" if settings.s3_secure else "http"
        return f"{scheme}://{settings.s3_endpoint}/{self._bucket}/{key}"

    def delete(self, key: str) -> None:
        """Delete the object at key (idempotent — silent on missing key).

        Swallows S3 NoSuchKey errors so that deleting an already-deleted or
        never-created object is safe to call without pre-checking existence.
        All other S3 errors are re-raised.

        Args:
            key: Object key path within the bucket.

        Raises:
            S3Error: If the storage backend returns any error other than
                ``NoSuchKey``.
        """
        try:
            self._client.remove_object(self._bucket, key)
        except S3Error as exc:
            if exc.code == "NoSuchKey":
                logger.debug("delete(%s): object not found, skipping (idempotent)", key)
                return
            raise


def get_storage() -> StorageService:
    """FastAPI dependency returning a StorageService."""
    return StorageService()
