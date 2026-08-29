import re
from uuid import UUID


def safe_filename(filename: str) -> str:
    name = filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1].strip()
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return (name[:240] or "upload.bin").strip(".") or "upload.bin"


def original_video_key(video_id: UUID, filename: str) -> str:
    return f"videos/{video_id}/original/{safe_filename(filename)}"
