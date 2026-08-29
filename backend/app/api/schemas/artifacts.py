from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    format: str = Field(pattern="^(srt|vtt)$")


class ExportResponse(BaseModel):
    artifact_id: UUID
    translation_job_id: UUID
    translation_version_id: UUID
    format: str
    status: str


class ArtifactResponse(BaseModel):
    id: UUID
    translation_job_id: UUID
    translation_version_id: UUID
    format: str
    status: str
    download_url: str | None = None
    expires_at: datetime | None = None
    error_code: str | None = None
