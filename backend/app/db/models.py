from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    videos: Mapped[list["Video"]] = relationship(back_populates="user")


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(1024), unique=True)
    mime_type: Mapped[str] = mapped_column(String(128))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="pending_upload", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User | None] = relationship(back_populates="videos")
    media_assets: Mapped[list["MediaAsset"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    transcripts: Mapped[list["Transcript"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    translation_jobs: Mapped[list["TranslationJob"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    video_id: Mapped[UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    asset_type: Mapped[str] = mapped_column(String(32), index=True)
    storage_key: Mapped[str] = mapped_column(String(1024), unique=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    video: Mapped[Video] = relationship(back_populates="media_assets")


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    video_id: Mapped[UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    source_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    provider: Mapped[str] = mapped_column(String(32), default="openai")
    model: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    video: Mapped[Video] = relationship(back_populates="transcripts")
    segments: Mapped[list["TranscriptSegment"]] = relationship(
        back_populates="transcript", cascade="all, delete-orphan"
    )
    translation_jobs: Mapped[list["TranslationJob"]] = relationship(back_populates="transcript")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    __table_args__ = (UniqueConstraint("transcript_id", "sequence_no"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    transcript_id: Mapped[UUID] = mapped_column(
        ForeignKey("transcripts.id", ondelete="CASCADE"), index=True
    )
    sequence_no: Mapped[int] = mapped_column(Integer)
    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)
    source_text: Mapped[str] = mapped_column(Text)
    words_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    transcript: Mapped[Transcript] = relationship(back_populates="segments")
    translation_segments: Mapped[list["TranslationSegment"]] = relationship(
        back_populates="transcript_segment"
    )


class TranslationJob(Base):
    __tablename__ = "translation_jobs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    video_id: Mapped[UUID] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    transcript_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("transcripts.id", ondelete="SET NULL"), index=True, nullable=True
    )
    source_language_hint: Mapped[str | None] = mapped_column(String(16), nullable=True)
    target_language: Mapped[str] = mapped_column(String(16))
    translation_style: Mapped[str] = mapped_column(String(32), default="natural")
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    current_step: Mapped[str | None] = mapped_column(String(32), nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    active_version_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    video: Mapped[Video] = relationship(back_populates="translation_jobs")
    transcript: Mapped[Transcript | None] = relationship(back_populates="translation_jobs")
    versions: Mapped[list["TranslationVersion"]] = relationship(
        back_populates="translation_job", cascade="all, delete-orphan"
    )
    steps: Mapped[list["JobStep"]] = relationship(
        back_populates="translation_job", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["SubtitleArtifact"]] = relationship(
        back_populates="translation_job", cascade="all, delete-orphan"
    )


class TranslationVersion(Base):
    __tablename__ = "translation_versions"
    __table_args__ = (UniqueConstraint("translation_job_id", "version_no"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    translation_job_id: Mapped[UUID] = mapped_column(
        ForeignKey("translation_jobs.id", ondelete="CASCADE"), index=True
    )
    version_no: Mapped[int] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(32), default="openai")
    model: Mapped[str] = mapped_column(String(128))
    prompt_version: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(String(16), default="ai")
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    translation_job: Mapped[TranslationJob] = relationship(back_populates="versions")
    segments: Mapped[list["TranslationSegment"]] = relationship(
        back_populates="translation_version", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["SubtitleArtifact"]] = relationship(back_populates="translation_version")


class TranslationSegment(Base):
    __tablename__ = "translation_segments"
    __table_args__ = (UniqueConstraint("translation_version_id", "transcript_segment_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    translation_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("translation_versions.id", ondelete="CASCADE"), index=True
    )
    transcript_segment_id: Mapped[UUID] = mapped_column(
        ForeignKey("transcript_segments.id", ondelete="CASCADE"), index=True
    )
    sequence_no: Mapped[int] = mapped_column(Integer)
    translated_text: Mapped[str] = mapped_column(Text)
    display_start_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    display_end_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    review_status: Mapped[str] = mapped_column(String(16), default="pending")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    translation_version: Mapped[TranslationVersion] = relationship(back_populates="segments")
    transcript_segment: Mapped[TranscriptSegment] = relationship(
        back_populates="translation_segments"
    )


class JobStep(Base):
    __tablename__ = "job_steps"
    __table_args__ = (UniqueConstraint("translation_job_id", "step_type"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    translation_job_id: Mapped[UUID] = mapped_column(
        ForeignKey("translation_jobs.id", ondelete="CASCADE"), index=True
    )
    step_type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    translation_job: Mapped[TranslationJob] = relationship(back_populates="steps")
    api_calls: Mapped[list["AIAPICall"]] = relationship(
        back_populates="job_step", cascade="all, delete-orphan"
    )


class AIAPICall(Base):
    __tablename__ = "ai_api_calls"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    job_step_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_steps.id", ondelete="CASCADE"), index=True
    )
    operation: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str] = mapped_column(String(32), default="openai")
    model: Mapped[str] = mapped_column(String(128))
    request_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    response_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_usage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_usage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16))
    error_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    job_step: Mapped[JobStep] = relationship(back_populates="api_calls")


class SubtitleArtifact(Base):
    __tablename__ = "subtitle_artifacts"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    translation_job_id: Mapped[UUID] = mapped_column(
        ForeignKey("translation_jobs.id", ondelete="CASCADE"), index=True
    )
    translation_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("translation_versions.id", ondelete="CASCADE"), index=True
    )
    format: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    storage_key: Mapped[str] = mapped_column(String(1024), unique=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    translation_job: Mapped[TranslationJob] = relationship(back_populates="artifacts")
    translation_version: Mapped[TranslationVersion] = relationship(back_populates="artifacts")
