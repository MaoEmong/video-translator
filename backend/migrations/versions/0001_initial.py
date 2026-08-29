"""Initial video translation schema."""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "videos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )

    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )

    op.create_table(
        "transcripts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("source_language", sa.String(length=16), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "transcript_segments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transcript_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("start_ms", sa.Integer(), nullable=False),
        sa.Column("end_ms", sa.Integer(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("words_json", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["transcript_id"], ["transcripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transcript_id", "sequence_no"),
    )

    op.create_table(
        "translation_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("transcript_id", sa.Uuid(), nullable=True),
        sa.Column("source_language_hint", sa.String(length=16), nullable=True),
        sa.Column("target_language", sa.String(length=16), nullable=False),
        sa.Column("translation_style", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_step", sa.String(length=32), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("active_version_id", sa.Uuid(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transcript_id"], ["transcripts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "translation_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("translation_job_id", sa.Uuid(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=16), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["translation_job_id"], ["translation_jobs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("translation_job_id", "version_no"),
    )

    op.create_table(
        "translation_segments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("translation_version_id", sa.Uuid(), nullable=False),
        sa.Column("transcript_segment_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=False),
        sa.Column("display_start_ms", sa.Integer(), nullable=True),
        sa.Column("display_end_ms", sa.Integer(), nullable=True),
        sa.Column("review_status", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["transcript_segment_id"], ["transcript_segments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["translation_version_id"], ["translation_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("translation_version_id", "transcript_segment_id"),
    )

    op.create_table(
        "job_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("translation_job_id", sa.Uuid(), nullable=False),
        sa.Column("step_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["translation_job_id"], ["translation_jobs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
        sa.UniqueConstraint("translation_job_id", "step_type"),
    )

    op.create_table(
        "ai_api_calls",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_step_id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=255), nullable=True),
        sa.Column("response_id", sa.String(length=255), nullable=True),
        sa.Column("input_usage", sa.Integer(), nullable=True),
        sa.Column("output_usage", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_step_id"], ["job_steps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "subtitle_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("translation_job_id", sa.Uuid(), nullable=False),
        sa.Column("translation_version_id", sa.Uuid(), nullable=False),
        sa.Column("format", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["translation_job_id"], ["translation_jobs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["translation_version_id"], ["translation_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )

    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_videos_status", "videos", ["status"], unique=False)
    op.create_index("ix_media_assets_video_id", "media_assets", ["video_id"], unique=False)
    op.create_index("ix_media_assets_asset_type", "media_assets", ["asset_type"], unique=False)
    op.create_index("ix_transcripts_video_id", "transcripts", ["video_id"], unique=False)
    op.create_index("ix_transcripts_status", "transcripts", ["status"], unique=False)
    op.create_index(
        "ix_transcript_segments_transcript_id",
        "transcript_segments",
        ["transcript_id"],
        unique=False,
    )
    op.create_index(
        "ix_translation_jobs_transcript_id", "translation_jobs", ["transcript_id"], unique=False
    )
    op.create_index("ix_translation_jobs_status", "translation_jobs", ["status"], unique=False)
    op.create_index("ix_translation_jobs_video_id", "translation_jobs", ["video_id"], unique=False)
    op.create_index(
        "ix_translation_versions_translation_job_id",
        "translation_versions",
        ["translation_job_id"],
        unique=False,
    )
    op.create_index(
        "ix_translation_versions_is_current", "translation_versions", ["is_current"], unique=False
    )
    op.create_index(
        "ix_translation_segments_translation_version_id",
        "translation_segments",
        ["translation_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_translation_segments_transcript_segment_id",
        "translation_segments",
        ["transcript_segment_id"],
        unique=False,
    )
    op.create_index(
        "ix_job_steps_translation_job_id", "job_steps", ["translation_job_id"], unique=False
    )
    op.create_index("ix_ai_api_calls_job_step_id", "ai_api_calls", ["job_step_id"], unique=False)
    op.create_index("ix_ai_api_calls_request_id", "ai_api_calls", ["request_id"], unique=False)
    op.create_index(
        "ix_subtitle_artifacts_translation_job_id",
        "subtitle_artifacts",
        ["translation_job_id"],
        unique=False,
    )
    op.create_index(
        "ix_subtitle_artifacts_translation_version_id",
        "subtitle_artifacts",
        ["translation_version_id"],
        unique=False,
    )
    op.create_index("ix_subtitle_artifacts_status", "subtitle_artifacts", ["status"], unique=False)


def downgrade() -> None:
    op.drop_table("subtitle_artifacts")
    op.drop_table("ai_api_calls")
    op.drop_table("job_steps")
    op.drop_table("translation_segments")
    op.drop_table("translation_versions")
    op.drop_table("translation_jobs")
    op.drop_table("transcript_segments")
    op.drop_table("transcripts")
    op.drop_table("media_assets")
    op.drop_table("videos")
    op.drop_table("users")
