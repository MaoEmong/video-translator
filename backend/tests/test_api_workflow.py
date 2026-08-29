from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import get_storage
from app.db.base import Base
from app.db.models import JobStep, SubtitleArtifact, TranslationJob, TranslationVersion, Video
from app.db.session import get_db
from app.domain.enums import JobStepType, VideoStatus
from app.main import app
from app.queue.client import get_queue
from app.queue.messages import JobMessage
from app.storage.s3 import StoredObject, UploadTicket


class MemoryQueue:
    def __init__(self) -> None:
        self.messages: list[JobMessage] = []

    async def enqueue(self, message: JobMessage) -> None:
        self.messages.append(message)


class FakeStorage:
    def create_upload_ticket(self, key: str, content_type: str) -> UploadTicket:
        return UploadTicket(
            url=f"https://storage.test/upload/{key}",
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )

    def head_object(self, key: str) -> StoredObject:
        return StoredObject(size_bytes=123, content_type="video/mp4", etag='"etag"')


@pytest_asyncio.fixture
async def api_client() -> AsyncIterator[
    tuple[httpx.AsyncClient, MemoryQueue, async_sessionmaker[AsyncSession]]
]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    queue = MemoryQueue()
    storage = FakeStorage()

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_queue] = lambda: queue
    app.dependency_overrides[get_storage] = lambda: storage

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, queue, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_upload_completion_and_job_creation(
    api_client: tuple[httpx.AsyncClient, MemoryQueue, async_sessionmaker[AsyncSession]],
) -> None:
    client, queue, session_factory = api_client

    upload_response = await client.post(
        "/api/v1/videos/uploads",
        json={"filename": "episode 01.mp4", "content_type": "video/mp4", "size_bytes": 456},
    )
    assert upload_response.status_code == 201
    video_id = UUID(upload_response.json()["video_id"])
    assert upload_response.json()["upload_url"].startswith("https://storage.test/upload/")

    complete_response = await client.post(f"/api/v1/videos/{video_id}/complete")
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == VideoStatus.READY.value
    assert complete_response.json()["file_size_bytes"] == 123

    job_response = await client.post(
        "/api/v1/translation-jobs",
        json={"video_id": str(video_id), "target_language": "ko"},
    )
    assert job_response.status_code == 202
    job_id = UUID(job_response.json()["id"])
    assert job_response.json()["status"] == "QUEUED"
    assert queue.messages[-1].job_id == job_id
    assert queue.messages[-1].step == JobStepType.VALIDATE

    async with session_factory() as db:
        steps = list(
            await db.scalars(select(JobStep).where(JobStep.translation_job_id == job_id))
        )
    assert {step.step_type for step in steps} == {step.value for step in JobStepType}


@pytest.mark.asyncio
async def test_job_requires_completed_upload(
    api_client: tuple[httpx.AsyncClient, MemoryQueue, async_sessionmaker[AsyncSession]],
) -> None:
    client, _, _ = api_client

    upload_response = await client.post(
        "/api/v1/videos/uploads",
        json={"filename": "pending.mp4", "content_type": "video/mp4", "size_bytes": 10},
    )
    video_id = upload_response.json()["video_id"]

    response = await client.post(
        "/api/v1/translation-jobs",
        json={"video_id": video_id, "target_language": "ko"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Video upload is not ready"


@pytest.mark.asyncio
async def test_export_reuses_existing_artifact(
    api_client: tuple[httpx.AsyncClient, MemoryQueue, async_sessionmaker[AsyncSession]],
) -> None:
    client, queue, session_factory = api_client
    video_id = uuid4()
    job_id = uuid4()
    version_id = uuid4()
    artifact_id = uuid4()

    async with session_factory() as db:
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
            TranslationJob(
                id=job_id,
                video_id=video_id,
                target_language="ko",
                translation_style="natural",
                status="COMPLETED",
                active_version_id=version_id,
                progress=100,
            )
        )
        db.add(
            TranslationVersion(
                id=version_id,
                translation_job_id=job_id,
                version_no=1,
                model="gpt-test-translation",
                prompt_version="v1",
                created_by="ai",
                is_current=True,
            )
        )
        db.add(
            SubtitleArtifact(
                id=artifact_id,
                translation_job_id=job_id,
                translation_version_id=version_id,
                format="srt",
                status="completed",
                storage_key=f"jobs/{job_id}/versions/{version_id}/subtitle.srt",
            )
        )
        await db.commit()

    response = await client.post(
        f"/api/v1/translation-jobs/{job_id}/exports", json={"format": "srt"}
    )

    assert response.status_code == 202
    assert response.json()["artifact_id"] == str(artifact_id)
    assert response.json()["status"] == "completed"
    assert queue.messages == []
