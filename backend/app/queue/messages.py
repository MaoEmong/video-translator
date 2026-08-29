from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import JobStepType


class JobMessage(BaseModel):
    job_id: UUID
    step: JobStepType
    transcript_id: UUID | None = None
    translation_version_id: UUID | None = None
    artifact_id: UUID | None = None
    batch_index: int | None = Field(default=None, ge=0)
    attempt: int = Field(default=1, ge=1)
