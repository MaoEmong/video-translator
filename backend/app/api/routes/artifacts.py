from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_storage
from app.api.schemas.artifacts import ArtifactResponse
from app.db.models import SubtitleArtifact
from app.db.session import get_db
from app.storage.s3 import S3Storage, StorageError

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> ArtifactResponse:
    artifact = await db.scalar(select(SubtitleArtifact).where(SubtitleArtifact.id == artifact_id))
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")

    download_url = None
    expires_at = None
    if artifact.status == "completed":
        try:
            ticket = storage.create_download_url(artifact.storage_key)
        except StorageError as exc:
            raise HTTPException(status_code=503, detail="Object storage is unavailable") from exc
        download_url = ticket.url
        expires_at = ticket.expires_at

    return ArtifactResponse(
        id=artifact.id,
        translation_job_id=artifact.translation_job_id,
        translation_version_id=artifact.translation_version_id,
        format=artifact.format,
        status=artifact.status,
        download_url=download_url,
        expires_at=expires_at,
        error_code=artifact.error_code,
    )
