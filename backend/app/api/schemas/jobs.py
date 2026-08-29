from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateTranslationJobRequest(BaseModel):
    video_id: UUID
    source_language: str = Field(default="auto", min_length=2, max_length=16)
    target_language: str = Field(min_length=2, max_length=16)
    translation_style: str = Field(default="natural", min_length=1, max_length=32)


class TranslationJobResponse(BaseModel):
    id: UUID
    video_id: UUID
    transcript_id: UUID | None
    source_language: str | None
    target_language: str
    translation_style: str
    status: str
    current_step: str | None
    progress: int
    created_at: datetime
    completed_at: datetime | None
    error_code: str | None


class TranslationSegmentResponse(BaseModel):
    id: UUID
    sequence_no: int
    start_ms: int
    end_ms: int
    source_text: str
    translated_text: str
    display_start_ms: int
    display_end_ms: int
    review_status: str
    version: int


class TranslationSegmentUpdateRequest(BaseModel):
    translated_text: str = Field(min_length=1)
    display_start_ms: int | None = Field(default=None, ge=0)
    display_end_ms: int | None = Field(default=None, ge=1)


class RetranslateRequest(BaseModel):
    translation_style: str | None = Field(default=None, min_length=1, max_length=32)
    preserve_user_edits: bool = False
