import asyncio
import hashlib
import tempfile
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.db.models import (
    AIAPICall,
    JobStep,
    MediaAsset,
    SubtitleArtifact,
    Transcript,
    TranscriptSegment,
    TranslationJob,
    TranslationSegment,
    TranslationVersion,
    Video,
    utc_now,
)
from app.domain.enums import JobStatus, JobStepType, StepStatus, VideoStatus
from app.providers.openai_adapters import (
    OpenAISttAdapter,
    OpenAITranslationAdapter,
    ProviderError,
    TranslationInput,
)
from app.queue.client import QueueClient, QueueError
from app.queue.messages import JobMessage
from app.storage.s3 import S3Storage, StorageError
from app.subtitles.builder import SubtitleSegment, build_subtitle


class PipelineError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


async def _get_step(db: AsyncSession, job_id: UUID, step: JobStepType) -> JobStep | None:
    return await db.scalar(
        select(JobStep).where(JobStep.translation_job_id == job_id, JobStep.step_type == step.value)
    )


async def _start_step(db: AsyncSession, job: TranslationJob, step: JobStepType) -> JobStep:
    job.current_step = step.value
    step_row = await _get_step(db, job.id, step)
    if step_row is None:
        step_row = JobStep(
            translation_job_id=job.id,
            step_type=step.value,
            status=StepStatus.RUNNING.value,
            attempt_count=1,
            idempotency_key=f"{job.id}:{step.value}:{uuid4()}",
            started_at=utc_now(),
        )
        db.add(step_row)
    else:
        step_row.status = StepStatus.RUNNING.value
        step_row.attempt_count += 1
        step_row.started_at = utc_now()
    return step_row


async def _complete_step(db: AsyncSession, step: JobStep) -> None:
    step.status = StepStatus.COMPLETED.value
    step.completed_at = utc_now()
    await db.commit()


async def _enqueue(queue: QueueClient, message: JobMessage) -> None:
    await queue.enqueue(message)


async def _run_ffmpeg(settings: Settings, source: Path, destination: Path) -> None:
    process = await asyncio.create_subprocess_exec(
        settings.ffmpeg_binary,
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(destination),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        error = stderr.decode(errors="replace")[-1000:]
        raise PipelineError("FFMPEG_FAILED", error or "FFmpeg failed")


async def _handle_validate(
    db: AsyncSession, job: TranslationJob, queue: QueueClient, step: JobStepType
) -> None:
    video = await db.scalar(select(Video).where(Video.id == job.video_id))
    if video is None:
        raise PipelineError("VIDEO_NOT_FOUND", "Video does not exist")
    if video.status != VideoStatus.READY.value:
        raise PipelineError("VIDEO_NOT_READY", "Video upload is not ready")

    job.status = JobStatus.VALIDATING.value
    step_row = await _start_step(db, job, step)
    if job.transcript_id:
        await _complete_step(db, step_row)
        await _enqueue(
            queue,
            JobMessage(job_id=job.id, step=JobStepType.TRANSLATE, transcript_id=job.transcript_id),
        )
        return

    job.status = JobStatus.EXTRACTING_AUDIO.value
    job.progress = 5
    await _complete_step(db, step_row)
    await _enqueue(queue, JobMessage(job_id=job.id, step=JobStepType.EXTRACT_AUDIO))


async def _handle_extract_audio(
    db: AsyncSession,
    job: TranslationJob,
    queue: QueueClient,
    storage: S3Storage,
    settings: Settings,
) -> None:
    step_row = await _start_step(db, job, JobStepType.EXTRACT_AUDIO)
    video = await db.scalar(select(Video).where(Video.id == job.video_id))
    if video is None:
        raise PipelineError("VIDEO_NOT_FOUND", "Video does not exist")

    with tempfile.TemporaryDirectory(prefix="video-translator-") as temp_dir:
        source = Path(temp_dir) / "source.video"
        audio = Path(temp_dir) / "audio.wav"
        await asyncio.to_thread(storage.download_file, video.storage_key, source)
        await _run_ffmpeg(settings, source, audio)
        audio_key = f"videos/{video.id}/derived/normalized.wav"
        await asyncio.to_thread(storage.upload_file, audio, audio_key, "audio/wav")

        asset = await db.scalar(
            select(MediaAsset).where(
                MediaAsset.video_id == video.id, MediaAsset.asset_type == "normalized_audio"
            )
        )
        if asset is None:
            asset = MediaAsset(
                video_id=video.id, asset_type="normalized_audio", storage_key=audio_key
            )
            db.add(asset)
        asset.file_size_bytes = audio.stat().st_size

    job.status = JobStatus.TRANSCRIBING.value
    job.progress = 10
    await _complete_step(db, step_row)
    await _enqueue(queue, JobMessage(job_id=job.id, step=JobStepType.TRANSCRIBE))


async def _handle_transcribe(
    db: AsyncSession,
    job: TranslationJob,
    queue: QueueClient,
    storage: S3Storage,
    settings: Settings,
) -> None:
    step_row = await _start_step(db, job, JobStepType.TRANSCRIBE)
    asset = await db.scalar(
        select(MediaAsset).where(
            MediaAsset.video_id == job.video_id, MediaAsset.asset_type == "normalized_audio"
        )
    )
    if asset is None:
        raise PipelineError("AUDIO_NOT_FOUND", "Normalized audio does not exist")

    with tempfile.TemporaryDirectory(prefix="video-translator-") as temp_dir:
        audio_path = Path(temp_dir) / "audio.wav"
        await asyncio.to_thread(storage.download_file, asset.storage_key, audio_path)
        adapter = OpenAISttAdapter(settings)
        with audio_path.open("rb") as audio_file:
            result = await asyncio.to_thread(
                adapter.transcribe,
                audio_file,
                audio_path.name,
                "audio/wav",
                None,
                job.source_language_hint,
            )

    if not result.segments:
        raise PipelineError("OPENAI_STT_NO_TIMED_SEGMENTS", "STT did not return timed segments")

    transcript = Transcript(
        id=uuid4(),
        video_id=job.video_id,
        source_language=result.source_language or job.source_language_hint,
        provider="openai",
        model=settings.openai_stt_model,
        status="completed",
        completed_at=utc_now(),
    )
    db.add(transcript)
    for sequence_no, segment in enumerate(result.segments, start=1):
        db.add(
            TranscriptSegment(
                transcript_id=transcript.id,
                sequence_no=sequence_no,
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
                source_text=segment.text,
            )
        )
    db.add(
        AIAPICall(
            job_step_id=step_row.id,
            operation="transcription",
            provider="openai",
            model=settings.openai_stt_model,
            request_id=result.request_id,
            input_usage=result.input_usage,
            output_usage=result.output_usage,
            latency_ms=result.latency_ms,
            status="succeeded",
        )
    )
    job.transcript_id = transcript.id
    job.status = JobStatus.NORMALIZING.value
    job.progress = 35
    await _complete_step(db, step_row)
    await _enqueue(
        queue,
        JobMessage(job_id=job.id, step=JobStepType.NORMALIZE, transcript_id=transcript.id),
    )


async def _handle_normalize(
    db: AsyncSession, job: TranslationJob, queue: QueueClient, message: JobMessage
) -> None:
    step_row = await _start_step(db, job, JobStepType.NORMALIZE)
    transcript = await db.scalar(select(Transcript).where(Transcript.id == message.transcript_id))
    if transcript is None:
        raise PipelineError("TRANSCRIPT_NOT_FOUND", "Transcript does not exist")
    segments = await db.scalars(
        select(TranscriptSegment)
        .where(TranscriptSegment.transcript_id == transcript.id)
        .order_by(TranscriptSegment.sequence_no)
    )
    if any(item.end_ms <= item.start_ms or not item.source_text.strip() for item in segments):
        raise PipelineError("INVALID_TRANSCRIPT_SEGMENTS", "Transcript contains invalid segments")

    job.status = JobStatus.TRANSLATING.value
    job.progress = 40
    await _complete_step(db, step_row)
    await _enqueue(
        queue,
        JobMessage(job_id=job.id, step=JobStepType.TRANSLATE, transcript_id=transcript.id),
    )


async def _handle_translate(
    db: AsyncSession,
    job: TranslationJob,
    queue: QueueClient,
    settings: Settings,
    message: JobMessage,
) -> None:
    step_row = await _start_step(db, job, JobStepType.TRANSLATE)
    transcript_id = message.transcript_id or job.transcript_id
    if transcript_id is None:
        raise PipelineError("TRANSCRIPT_NOT_READY", "Transcript is not ready")
    transcript = await db.scalar(select(Transcript).where(Transcript.id == transcript_id))
    if transcript is None:
        raise PipelineError("TRANSCRIPT_NOT_FOUND", "Transcript does not exist")
    source_segments = list(
        await db.scalars(
            select(TranscriptSegment)
            .where(TranscriptSegment.transcript_id == transcript.id)
            .order_by(TranscriptSegment.sequence_no)
        )
    )
    if not source_segments:
        raise PipelineError("TRANSCRIPT_EMPTY", "Transcript has no segments")

    version = None
    if message.translation_version_id:
        version = await db.scalar(
            select(TranslationVersion).where(
                TranslationVersion.id == message.translation_version_id
            )
        )
    if version is None:
        version = TranslationVersion(
            id=uuid4(),
            translation_job_id=job.id,
            version_no=1,
            provider="openai",
            model=settings.openai_translation_model or "unconfigured",
            prompt_version=settings.openai_translation_prompt_version,
            created_by="ai",
            is_current=True,
        )
        db.add(version)
    job.active_version_id = version.id

    existing = {
        item.transcript_segment_id: item
        for item in await db.scalars(
            select(TranslationSegment).where(
                TranslationSegment.translation_version_id == version.id
            )
        )
    }
    adapter = OpenAITranslationAdapter(settings)
    batch_size = max(1, settings.translation_batch_size)
    for offset in range(0, len(source_segments), batch_size):
        batch = source_segments[offset : offset + batch_size]
        result = await asyncio.to_thread(
            adapter.translate,
            [TranslationInput(str(item.id), item.source_text) for item in batch],
            transcript.source_language or job.source_language_hint or "auto",
            job.target_language,
            job.translation_style,
        )
        by_id = {item.segment_id: item.translated_text for item in result.translations}
        for source_segment in batch:
            translated = by_id[str(source_segment.id)]
            target = existing.get(source_segment.id)
            if target is None:
                target = TranslationSegment(
                    translation_version_id=version.id,
                    transcript_segment_id=source_segment.id,
                    sequence_no=source_segment.sequence_no,
                    translated_text=translated,
                    review_status="pending",
                )
                db.add(target)
                existing[source_segment.id] = target
            else:
                target.translated_text = translated
        db.add(
            AIAPICall(
                job_step_id=step_row.id,
                operation="translation",
                provider="openai",
                model=settings.openai_translation_model or "unconfigured",
                request_id=result.request_id,
                response_id=result.response_id,
                input_usage=result.input_usage,
                output_usage=result.output_usage,
                latency_ms=result.latency_ms,
                status="succeeded",
            )
        )
        job.progress = 40 + round(((offset + len(batch)) / len(source_segments)) * 45)
        await db.flush()

    artifact = await db.scalar(
        select(SubtitleArtifact).where(
            SubtitleArtifact.translation_job_id == job.id,
            SubtitleArtifact.translation_version_id == version.id,
            SubtitleArtifact.format == "srt",
        )
    )
    if artifact is None:
        artifact = SubtitleArtifact(
            id=uuid4(),
            translation_job_id=job.id,
            translation_version_id=version.id,
            format="srt",
            status="queued",
            storage_key=f"jobs/{job.id}/versions/{version.id}/subtitle.srt",
        )
        db.add(artifact)
    job.status = JobStatus.BUILDING_SUBTITLE.value
    job.current_step = JobStepType.BUILD_SUBTITLE.value
    job.progress = 90
    await _complete_step(db, step_row)
    await _enqueue(
        queue,
        JobMessage(
            job_id=job.id,
            step=JobStepType.BUILD_SUBTITLE,
            translation_version_id=version.id,
            artifact_id=artifact.id,
        ),
    )


async def _handle_build_subtitle(
    db: AsyncSession,
    job: TranslationJob,
    storage: S3Storage,
    message: JobMessage,
) -> None:
    step_row = await _start_step(db, job, JobStepType.BUILD_SUBTITLE)
    artifact = None
    if message.artifact_id:
        artifact = await db.scalar(
            select(SubtitleArtifact).where(SubtitleArtifact.id == message.artifact_id)
        )
    if artifact is None:
        artifact = await db.scalar(
            select(SubtitleArtifact)
            .where(
                SubtitleArtifact.translation_job_id == job.id,
                SubtitleArtifact.translation_version_id == message.translation_version_id,
                SubtitleArtifact.status == "queued",
            )
            .order_by(SubtitleArtifact.created_at.desc())
        )
    if artifact is None:
        raise PipelineError("ARTIFACT_NOT_FOUND", "Subtitle artifact does not exist")
    if artifact.status == "completed":
        return

    segments = list(
        await db.scalars(
            select(TranslationSegment)
            .options(selectinload(TranslationSegment.transcript_segment))
            .where(TranslationSegment.translation_version_id == artifact.translation_version_id)
            .order_by(TranslationSegment.sequence_no)
        )
    )
    subtitle_segments = [
        SubtitleSegment(
            sequence_no=item.sequence_no,
            start_ms=(
                item.display_start_ms
                if item.display_start_ms is not None
                else item.transcript_segment.start_ms
            ),
            end_ms=(
                item.display_end_ms
                if item.display_end_ms is not None
                else item.transcript_segment.end_ms
            ),
            text=item.translated_text,
        )
        for item in segments
    ]
    content = build_subtitle(subtitle_segments, artifact.format)
    await asyncio.to_thread(
        storage.put_bytes, content.encode("utf-8"), artifact.storage_key, "text/plain"
    )
    artifact.status = "completed"
    artifact.file_size_bytes = len(content.encode("utf-8"))
    artifact.checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
    job.status = JobStatus.COMPLETED.value
    job.current_step = JobStepType.FINALIZE.value
    job.progress = 100
    job.completed_at = utc_now()
    finalize_step = await _get_step(db, job.id, JobStepType.FINALIZE)
    if finalize_step:
        finalize_step.status = StepStatus.COMPLETED.value
        finalize_step.attempt_count = max(1, finalize_step.attempt_count)
        finalize_step.started_at = finalize_step.started_at or utc_now()
        finalize_step.completed_at = utc_now()
    await _complete_step(db, step_row)


async def _fail_message(db: AsyncSession, message: JobMessage, code: str, detail: str) -> None:
    await db.rollback()
    job = await db.scalar(select(TranslationJob).where(TranslationJob.id == message.job_id))
    if job is None:
        return
    job.status = JobStatus.FAILED.value
    job.error_code = code
    step = await _get_step(db, job.id, message.step)
    if step:
        step.status = StepStatus.FAILED.value
        step.error_code = code
        step.error_message = detail[:2000]
        step.completed_at = utc_now()
    await db.commit()


async def process_message(
    message: JobMessage,
    db: AsyncSession,
    queue: QueueClient,
    storage: S3Storage,
    settings: Settings,
) -> None:
    job = await db.scalar(select(TranslationJob).where(TranslationJob.id == message.job_id))
    if job is None:
        return
    if job.status == JobStatus.CANCEL_REQUESTED.value:
        job.status = JobStatus.CANCELLED.value
        job.cancelled_at = utc_now()
        await db.commit()
        return

    try:
        if message.step == JobStepType.VALIDATE:
            await _handle_validate(db, job, queue, message.step)
        elif message.step == JobStepType.EXTRACT_AUDIO:
            await _handle_extract_audio(db, job, queue, storage, settings)
        elif message.step == JobStepType.TRANSCRIBE:
            await _handle_transcribe(db, job, queue, storage, settings)
        elif message.step == JobStepType.NORMALIZE:
            await _handle_normalize(db, job, queue, message)
        elif message.step == JobStepType.TRANSLATE:
            await _handle_translate(db, job, queue, settings, message)
        elif message.step == JobStepType.BUILD_SUBTITLE:
            await _handle_build_subtitle(db, job, storage, message)
        else:
            raise PipelineError("UNSUPPORTED_STEP", f"Unsupported step: {message.step}")
    except ProviderError as exc:
        await _fail_message(db, message, exc.code, str(exc))
    except (PipelineError, StorageError) as exc:
        code = exc.code if isinstance(exc, PipelineError) else "STORAGE_ERROR"
        await _fail_message(db, message, code, str(exc))
    except QueueError as exc:
        await _fail_message(db, message, "QUEUE_UNAVAILABLE", str(exc))
    except Exception as exc:
        await _fail_message(db, message, "UNEXPECTED_ERROR", str(exc))
