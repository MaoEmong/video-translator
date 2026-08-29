from uuid import UUID

from app.storage.keys import original_video_key, safe_filename


def test_safe_filename_removes_path_and_unsafe_characters() -> None:
    assert safe_filename(r"..\folder/my lecture (final).mp4") == "my_lecture_final_.mp4"


def test_original_video_key_is_scoped_to_video() -> None:
    video_id = UUID("11111111-1111-1111-1111-111111111111")

    assert original_video_key(video_id, "clip.mp4") == (
        "videos/11111111-1111-1111-1111-111111111111/original/clip.mp4"
    )
