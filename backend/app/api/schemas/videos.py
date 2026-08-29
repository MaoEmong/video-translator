from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UploadSessionRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=128)
    size_bytes: int = Field(gt=0)


class UploadSessionResponse(BaseModel):
    video_id: UUID
    upload_url: str
    expires_at: datetime


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    mime_type: str
    file_size_bytes: int
    status: str
    created_at: datetime
