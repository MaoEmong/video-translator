import pytest

from app.subtitles.builder import (
    SubtitleSegment,
    SubtitleValidationError,
    build_subtitle,
    format_timestamp,
)


def test_format_timestamp_uses_format_specific_millisecond_separator() -> None:
    assert format_timestamp(3_726_005, "srt") == "01:02:06,005"
    assert format_timestamp(3_726_005, "vtt") == "01:02:06.005"


def test_build_srt() -> None:
    result = build_subtitle(
        [SubtitleSegment(sequence_no=1, start_ms=0, end_ms=1500, text="Hello there")],
        "srt",
    )

    assert result == "1\n00:00:00,000 --> 00:00:01,500\nHello there\n"


def test_build_vtt() -> None:
    result = build_subtitle(
        [SubtitleSegment(sequence_no=1, start_ms=100, end_ms=1500, text="안녕하세요")],
        "vtt",
    )

    assert result == "WEBVTT\n\n00:00:00.100 --> 00:00:01.500\n안녕하세요\n"


def test_invalid_time_is_rejected() -> None:
    with pytest.raises(SubtitleValidationError, match="greater than"):
        build_subtitle(
            [SubtitleSegment(sequence_no=1, start_ms=100, end_ms=100, text="invalid")],
            "srt",
        )


def test_text_is_wrapped() -> None:
    result = build_subtitle(
        [SubtitleSegment(sequence_no=1, start_ms=0, end_ms=1000, text="one two three four")],
        "srt",
        max_chars_per_line=7,
        max_lines=2,
    )

    assert "one two\nthree four" in result
