from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_storage
from app.api.schemas.videos import UploadSessionRequest, UploadSessionResponse, VideoResponse
from app.config import Settings, get_settings
from app.db.models import Video
from app.db.session import get_db
from app.domain.enums import VideoStatus
from app.storage.keys import original_video_key
from app.storage.s3 import S3Storage, StorageError

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("/uploads", response_model=UploadSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_upload_session(
    payload: UploadSessionRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    storage: S3Storage = Depends(get_storage),
) -> UploadSessionResponse:
    if payload.size_bytes > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413, detail="Uploaded file exceeds the configured size limit"
        )
    if not payload.content_type.startswith("video/"):
        raise HTTPException(status_code=415, detail="Only video uploads are supported")

    video_id = uuid4()
    video = Video(
        id=video_id,
        original_filename=payload.filename,
        storage_key=original_video_key(video_id, payload.filename),
        mime_type=payload.content_type,
        file_size_bytes=payload.size_bytes,
        status=VideoStatus.PENDING_UPLOAD.value,
    )

    try:
        ticket = storage.create_upload_ticket(video.storage_key, payload.content_type)
    except StorageError as exc:
        raise HTTPException(status_code=503, detail="Object storage is unavailable") from exc

    db.add(video)
    await db.commit()

    return UploadSessionResponse(
        video_id=video.id,
        upload_url=ticket.url,
        expires_at=ticket.expires_at,
    )


@router.post("/{video_id}/complete", response_model=VideoResponse)
async def complete_upload(
    video_id: UUID,
    db: AsyncSession = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> VideoResponse:
    video = await db.scalar(select(Video).where(Video.id == video_id, Video.deleted_at.is_(None)))
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        stored_object = storage.head_object(video.storage_key)
    except StorageError as exc:
        raise HTTPException(status_code=409, detail="Uploaded object was not found") from exc

    if stored_object.content_type and stored_object.content_type != video.mime_type:
        raise HTTPException(
            status_code=400, detail="Uploaded content type does not match the request"
        )

    if stored_object.size_bytes is not None:
        video.file_size_bytes = stored_object.size_bytes
    video.status = VideoStatus.READY.value
    await db.commit()
    await db.refresh(video)
    return VideoResponse.model_validate(video)


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(video_id: UUID, db: AsyncSession = Depends(get_db)) -> VideoResponse:
    video = await db.scalar(select(Video).where(Video.id == video_id, Video.deleted_at.is_(None)))
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return VideoResponse.model_validate(video)
