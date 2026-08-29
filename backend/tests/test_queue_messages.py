from uuid import UUID

from app.domain.enums import JobStepType
from app.queue.messages import JobMessage


def test_job_message_serializes_stable_contract() -> None:
    message = JobMessage(
        job_id=UUID("11111111-1111-1111-1111-111111111111"),
        step=JobStepType.TRANSLATE,
        batch_index=2,
    )

    assert message.model_dump() == {
        "job_id": UUID("11111111-1111-1111-1111-111111111111"),
        "step": JobStepType.TRANSLATE,
        "transcript_id": None,
        "translation_version_id": None,
        "artifact_id": None,
        "batch_index": 2,
        "attempt": 1,
    }
