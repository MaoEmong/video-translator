from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from worker import pipeline

from app.config import Settings
from app.db.base import Base
from app.db.models import (
    JobStep,
    SubtitleArtifact,
    Transcript,
    TranscriptSegment,
    TranslationJob,
    TranslationSegment,
    Video,
    utc_now,
)
from app.domain.enums import JobStatus, JobStepType, StepStatus, VideoStatus
from app.providers.openai_adapters import TranslationItem, TranslationResult
from app.queue.messages import JobMessage


class MemoryQueue:
    def __init__(self) -> None:
        self.messages: list[JobMessage] = []

    async def enqueue(self, message: JobMessage) -> None:
        self.messages.append(message)


class MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put_bytes(self, content: bytes, key: str, content_type: str) -> None:
        self.objects[key] = (content, content_type)


@pytest_asyncio.fixture
async def pipeline_session() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    yield session_factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_translation_and_subtitle_pipeline(
    pipeline_session: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    video_id = uuid4()
    transcript_id = uuid4()
    job_id = uuid4()

    async with pipeline_session() as db:
        db.add(
            Video(
                id=video_id,
                original_filename="episode.mp4",
                storage_key=f"videos/{video_id}/original/episode.mp4",
                mime_type="video/mp4",
                file_size_bytes=100,
                status=VideoStatus.READY.value,
            )
        )
        db.add(
            Transcript(
                id=transcript_id,
                video_id=video_id,
                source_language="en",
                provider="openai",
                model="gpt-transcribe",
                status="completed",
                completed_at=utc_now(),
            )
        )
        db.add_all(
            [
                TranscriptSegment(
                    id=uuid4(),
                    transcript_id=transcript_id,
                    sequence_no=1,
                    start_ms=0,
                    end_ms=1400,
                    source_text="Hello there",
                ),
                TranscriptSegment(
                    id=uuid4(),
                    transcript_id=transcript_id,
                    sequence_no=2,
                    start_ms=1500,
                    end_ms=3000,
                    source_text="How are you?",
                ),
            ]
        )
        db.add(
            TranslationJob(
                id=job_id,
                video_id=video_id,
                transcript_id=transcript_id,
                target_language="ko",
                translation_style="natural",
                status=JobStatus.TRANSLATING.value,
                current_step=JobStepType.TRANSLATE.value,
                progress=40,
            )
        )
        db.add(
            JobStep(
                translation_job_id=job_id,
                step_type=JobStepType.TRANSLATE.value,
                status=StepStatus.QUEUED.value,
                idempotency_key=f"{job_id}:translate",
            )
        )
        await db.commit()

        class FakeTranslationAdapter:
            def __init__(self, settings: Settings) -> None:
                self.settings = settings

            def translate(self, segments, source_language, target_language, style):
                assert source_language == "en"
                assert target_language == "ko"
                return TranslationResult(
                    translations=[
                        TranslationItem(item.segment_id, f"번역: {item.source_text}")
                        for item in segments
                    ],
                    response_id="response-1",
                    request_id="request-1",
                    input_usage=20,
                    output_usage=10,
                    latency_ms=15,
                )

        monkeypatch.setattr(pipeline, "OpenAITranslationAdapter", FakeTranslationAdapter)
        queue = MemoryQueue()
        storage = MemoryStorage()
        settings = Settings(openai_translation_model="gpt-test-translation")

        await pipeline.process_message(
            JobMessage(job_id=job_id, step=JobStepType.TRANSLATE, transcript_id=transcript_id),
            db,
            queue,
            storage,
            settings,
        )
        assert queue.messages[-1].step == JobStepType.BUILD_SUBTITLE

        await pipeline.process_message(queue.messages[-1], db, queue, storage, settings)

        job = await db.scalar(select(TranslationJob).where(TranslationJob.id == job_id))
        artifact = await db.scalar(
            select(SubtitleArtifact).where(SubtitleArtifact.translation_job_id == job_id)
        )
        translations = list(
            await db.scalars(
                select(TranslationSegment)
                .where(TranslationSegment.translation_version_id == job.active_version_id)
                .order_by(TranslationSegment.sequence_no)
            )
        )

    assert job is not None
    assert job.status == JobStatus.COMPLETED.value
    assert job.progress == 100
    assert artifact is not None
    assert artifact.status == "completed"
    assert len(translations) == 2
    assert storage.objects[artifact.storage_key][0].decode("utf-8").startswith("1\n")
