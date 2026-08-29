from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas.artifacts import ExportRequest, ExportResponse
from app.api.schemas.jobs import (
    CreateTranslationJobRequest,
    RetranslateRequest,
    TranslationJobResponse,
    TranslationSegmentResponse,
    TranslationSegmentUpdateRequest,
)
from app.config import Settings, get_settings
from app.db.models import (
    JobStep,
    SubtitleArtifact,
    Transcript,
    TranslationJob,
    TranslationSegment,
    TranslationVersion,
    Video,
)
from app.db.session import get_db
from app.domain.enums import JobStatus, JobStepType, StepStatus, VideoStatus
from app.queue.client import QueueError, RedisQueue, get_queue
from app.queue.messages import JobMessage

router = APIRouter(prefix="/translation-jobs", tags=["translation-jobs"])


def to_job_response(
    job: TranslationJob, source_language: str | None = None
) -> TranslationJobResponse:
    return TranslationJobResponse(
        id=job.id,
        video_id=job.video_id,
        transcript_id=job.transcript_id,
        source_language=source_language,
        target_language=job.target_language,
        translation_style=job.translation_style,
        status=job.status,
        current_step=job.current_step,
        progress=job.progress,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error_code=job.error_code,
    )


def new_step(job_id: UUID, step_type: JobStepType) -> JobStep:
    return JobStep(
        translation_job_id=job_id,
        step_type=step_type.value,
        status=StepStatus.QUEUED.value,
        idempotency_key=f"{job_id}:{step_type.value}",
    )


@router.post("", response_model=TranslationJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_translation_job(
    payload: CreateTranslationJobRequest,
    db: AsyncSession = Depends(get_db),
    queue: RedisQueue = Depends(get_queue),
) -> TranslationJobResponse:
    video = await db.scalar(
        select(Video).where(Video.id == payload.video_id, Video.deleted_at.is_(None))
    )
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.status != VideoStatus.READY.value:
        raise HTTPException(status_code=409, detail="Video upload is not ready")

    transcript = await db.scalar(
        select(Transcript)
        .where(Transcript.video_id == video.id, Transcript.status == "completed")
        .order_by(Transcript.created_at.desc())
    )
    job = TranslationJob(
        id=uuid4(),
        video_id=video.id,
        transcript_id=transcript.id if transcript else None,
        source_language_hint=None if payload.source_language == "auto" else payload.source_language,
        target_language=payload.target_language,
        translation_style=payload.translation_style,
        status=JobStatus.QUEUED.value,
        current_step=JobStepType.VALIDATE.value,
        progress=0,
    )
    db.add(job)
    for step_type in JobStepType:
        db.add(new_step(job.id, step_type))
    await db.commit()

    try:
        await queue.enqueue(JobMessage(job_id=job.id, step=JobStepType.VALIDATE))
    except QueueError as exc:
        job.status = JobStatus.FAILED.value
        job.error_code = "QUEUE_UNAVAILABLE"
        await db.commit()
        raise HTTPException(status_code=503, detail="Job queue is unavailable") from exc

    await db.refresh(job)
    return to_job_response(
        job,
        transcript.source_language if transcript else job.source_language_hint,
    )


@router.get("/{job_id}", response_model=TranslationJobResponse)
async def get_translation_job(
    job_id: UUID, db: AsyncSession = Depends(get_db)
) -> TranslationJobResponse:
    job = await db.scalar(
        select(TranslationJob)
        .options(selectinload(TranslationJob.transcript))
        .where(TranslationJob.id == job_id)
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Translation job not found")
    return to_job_response(
        job, job.transcript.source_language if job.transcript else job.source_language_hint
    )


@router.get("/{job_id}/segments", response_model=list[TranslationSegmentResponse])
async def get_translation_segments(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[TranslationSegmentResponse]:
    job = await db.scalar(select(TranslationJob).where(TranslationJob.id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Translation job not found")
    if job.active_version_id is None:
        return []

    rows = await db.execute(
        select(TranslationSegment)
        .options(selectinload(TranslationSegment.transcript_segment))
        .where(TranslationSegment.translation_version_id == job.active_version_id)
        .order_by(TranslationSegment.sequence_no)
    )
    return [
        TranslationSegmentResponse(
            id=segment.id,
            sequence_no=segment.sequence_no,
            start_ms=segment.transcript_segment.start_ms,
            end_ms=segment.transcript_segment.end_ms,
            source_text=segment.transcript_segment.source_text,
            translated_text=segment.translated_text,
            display_start_ms=(
                segment.display_start_ms
                if segment.display_start_ms is not None
                else segment.transcript_segment.start_ms
            ),
            display_end_ms=(
                segment.display_end_ms
                if segment.display_end_ms is not None
                else segment.transcript_segment.end_ms
            ),
            review_status=segment.review_status,
            version=segment.version,
        )
        for segment in rows.scalars()
    ]


@router.patch("/{job_id}/segments/{segment_id}", response_model=TranslationSegmentResponse)
async def update_translation_segment(
    job_id: UUID,
    segment_id: UUID,
    payload: TranslationSegmentUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> TranslationSegmentResponse:
    job = await db.scalar(select(TranslationJob).where(TranslationJob.id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Translation job not found")
    if job.active_version_id is None:
        raise HTTPException(status_code=409, detail="Translation is not ready")

    segment = await db.scalar(
        select(TranslationSegment)
        .options(selectinload(TranslationSegment.transcript_segment))
        .where(
            TranslationSegment.id == segment_id,
            TranslationSegment.translation_version_id == job.active_version_id,
        )
    )
    if segment is None:
        raise HTTPException(status_code=404, detail="Translation segment not found")

    start_ms = (
        payload.display_start_ms
        if payload.display_start_ms is not None
        else segment.transcript_segment.start_ms
    )
    end_ms = (
        payload.display_end_ms
        if payload.display_end_ms is not None
        else segment.transcript_segment.end_ms
    )
    if end_ms <= start_ms:
        raise HTTPException(
            status_code=422, detail="Subtitle end time must be greater than start time"
        )

    segment.translated_text = payload.translated_text.strip()
    segment.display_start_ms = payload.display_start_ms
    segment.display_end_ms = payload.display_end_ms
    segment.review_status = "edited"
    segment.version += 1
    await db.commit()
    await db.refresh(segment)

    return TranslationSegmentResponse(
        id=segment.id,
        sequence_no=segment.sequence_no,
        start_ms=segment.transcript_segment.start_ms,
        end_ms=segment.transcript_segment.end_ms,
        source_text=segment.transcript_segment.source_text,
        translated_text=segment.translated_text,
        display_start_ms=start_ms,
        display_end_ms=end_ms,
        review_status=segment.review_status,
        version=segment.version,
    )


@router.post("/{job_id}/cancel", response_model=TranslationJobResponse)
async def cancel_translation_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TranslationJobResponse:
    job = await db.scalar(
        select(TranslationJob)
        .options(selectinload(TranslationJob.transcript))
        .where(TranslationJob.id == job_id)
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Translation job not found")
    if job.status not in {
        JobStatus.COMPLETED.value,
        JobStatus.FAILED.value,
        JobStatus.CANCELLED.value,
    }:
        job.status = JobStatus.CANCEL_REQUESTED.value
        await db.commit()
    source_language = job.transcript.source_language if job.transcript else job.source_language_hint
    return to_job_response(job, source_language)


@router.post("/{job_id}/retranslate", response_model=TranslationJobResponse)
async def retranslate_job(
    job_id: UUID,
    payload: RetranslateRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    queue: RedisQueue = Depends(get_queue),
) -> TranslationJobResponse:
    job = await db.scalar(
        select(TranslationJob)
        .options(selectinload(TranslationJob.transcript))
        .where(TranslationJob.id == job_id)
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Translation job not found")
    if job.transcript_id is None:
        raise HTTPException(status_code=409, detail="Transcript is not ready")

    if payload.translation_style:
        job.translation_style = payload.translation_style
    max_version = await db.scalar(
        select(func.max(TranslationVersion.version_no)).where(
            TranslationVersion.translation_job_id == job.id
        )
    )
    await db.execute(
        update(TranslationVersion)
        .where(TranslationVersion.translation_job_id == job.id)
        .values(is_current=False)
    )
    version = TranslationVersion(
        id=uuid4(),
        translation_job_id=job.id,
        version_no=(max_version or 0) + 1,
        provider="openai",
        model=settings.openai_translation_model or "unconfigured",
        prompt_version=settings.openai_translation_prompt_version,
        created_by="ai",
        is_current=True,
    )
    job.active_version_id = version.id
    job.status = JobStatus.TRANSLATING.value
    job.current_step = JobStepType.TRANSLATE.value
    job.progress = 40
    step = await db.scalar(
        select(JobStep).where(
            JobStep.translation_job_id == job.id,
            JobStep.step_type == JobStepType.TRANSLATE.value,
        )
    )
    if step:
        step.status = StepStatus.QUEUED.value
        step.attempt_count += 1
        step.idempotency_key = f"{job.id}:{JobStepType.TRANSLATE.value}:{version.id}"
    db.add(version)
    await db.commit()

    try:
        await queue.enqueue(
            JobMessage(
                job_id=job.id,
                step=JobStepType.TRANSLATE,
                transcript_id=job.transcript_id,
                translation_version_id=version.id,
            )
        )
    except QueueError as exc:
        job.status = JobStatus.FAILED.value
        job.error_code = "QUEUE_UNAVAILABLE"
        await db.commit()
        raise HTTPException(status_code=503, detail="Job queue is unavailable") from exc

    source_language = job.transcript.source_language if job.transcript else job.source_language_hint
    return to_job_response(job, source_language)


@router.post(
    "/{job_id}/exports",
    response_model=ExportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_export(
    job_id: UUID,
    payload: ExportRequest,
    db: AsyncSession = Depends(get_db),
    queue: RedisQueue = Depends(get_queue),
) -> ExportResponse:
    job = await db.scalar(select(TranslationJob).where(TranslationJob.id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Translation job not found")
    if job.active_version_id is None:
        raise HTTPException(status_code=409, detail="Translation is not ready")

    artifact = await db.scalar(
        select(SubtitleArtifact).where(
            SubtitleArtifact.translation_job_id == job.id,
            SubtitleArtifact.translation_version_id == job.active_version_id,
            SubtitleArtifact.format == payload.format,
        )
    )

    if artifact is not None and artifact.status != "failed":
        return ExportResponse(
            artifact_id=artifact.id,
            translation_job_id=artifact.translation_job_id,
            translation_version_id=artifact.translation_version_id,
            format=artifact.format,
            status=artifact.status,
        )

    if artifact is None:
        artifact = SubtitleArtifact(
            id=uuid4(),
            translation_job_id=job.id,
            translation_version_id=job.active_version_id,
            format=payload.format,
            status="queued",
            storage_key=f"jobs/{job.id}/versions/{job.active_version_id}/subtitle.{payload.format}",
        )
        db.add(artifact)
    else:
        artifact.status = "queued"
        artifact.error_code = None
    await db.commit()

    try:
        await queue.enqueue(
            JobMessage(
                job_id=job.id,
                step=JobStepType.BUILD_SUBTITLE,
                translation_version_id=job.active_version_id,
                artifact_id=artifact.id,
            )
        )
    except QueueError as exc:
        artifact.status = "failed"
        artifact.error_code = "QUEUE_UNAVAILABLE"
        await db.commit()
        raise HTTPException(status_code=503, detail="Job queue is unavailable") from exc

    return ExportResponse(
        artifact_id=artifact.id,
        translation_job_id=artifact.translation_job_id,
        translation_version_id=artifact.translation_version_id,
        format=artifact.format,
        status=artifact.status,
    )
