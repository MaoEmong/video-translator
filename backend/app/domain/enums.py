from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    VALIDATING = "VALIDATING"
    EXTRACTING_AUDIO = "EXTRACTING_AUDIO"
    TRANSCRIBING = "TRANSCRIBING"
    NORMALIZING = "NORMALIZING"
    TRANSLATING = "TRANSLATING"
    BUILDING_SUBTITLE = "BUILDING_SUBTITLE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"


class JobStepType(StrEnum):
    VALIDATE = "validate"
    EXTRACT_AUDIO = "extract_audio"
    TRANSCRIBE = "transcribe"
    NORMALIZE = "normalize"
    TRANSLATE = "translate"
    BUILD_SUBTITLE = "build_subtitle"
    FINALIZE = "finalize"


class VideoStatus(StrEnum):
    PENDING_UPLOAD = "pending_upload"
    READY = "ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    DELETED = "deleted"


class TranscriptStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    EDITED = "edited"
