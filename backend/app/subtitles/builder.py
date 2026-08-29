from dataclasses import dataclass


class SubtitleValidationError(ValueError):
    """Raised when subtitle data cannot be rendered safely."""


@dataclass(frozen=True)
class SubtitleSegment:
    sequence_no: int
    start_ms: int
    end_ms: int
    text: str


def format_timestamp(milliseconds: int, subtitle_format: str) -> str:
    if milliseconds < 0:
        raise SubtitleValidationError("Subtitle timestamp cannot be negative")
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    separator = "," if subtitle_format == "srt" else "."
    return f"{hours:02}:{minutes:02}:{seconds:02}{separator}{millis:03}"


def _wrap_text(text: str, max_chars_per_line: int, max_lines: int) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        raise SubtitleValidationError("Subtitle text cannot be empty")

    lines: list[str] = []
    current = ""
    for word in normalized.split(" "):
        if len(word) > max_chars_per_line:
            if current:
                lines.append(current)
                current = ""
            while len(word) > max_chars_per_line:
                lines.append(word[:max_chars_per_line])
                word = word[max_chars_per_line:]
            current = word
            continue

        candidate = f"{current} {word}" if current else word
        if len(candidate) <= max_chars_per_line:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)

    if len(lines) > max_lines:
        # Preserve all translation text. The quality checker can flag an
        # overlong final line; silently truncating a subtitle is unacceptable.
        lines = lines[: max_lines - 1] + [" ".join(lines[max_lines - 1 :])]
    return "\n".join(lines[:max_lines])


def build_subtitle(
    segments: list[SubtitleSegment],
    subtitle_format: str,
    max_chars_per_line: int = 42,
    max_lines: int = 2,
) -> str:
    if subtitle_format not in {"srt", "vtt"}:
        raise SubtitleValidationError(f"Unsupported subtitle format: {subtitle_format}")
    if max_chars_per_line < 1 or max_lines < 1:
        raise SubtitleValidationError("Subtitle layout limits must be positive")

    rendered: list[str] = ["WEBVTT", ""] if subtitle_format == "vtt" else []
    for index, segment in enumerate(segments, start=1):
        if segment.end_ms <= segment.start_ms:
            raise SubtitleValidationError("Subtitle end time must be greater than start time")
        text = _wrap_text(segment.text, max_chars_per_line, max_lines)
        start = format_timestamp(segment.start_ms, subtitle_format)
        end = format_timestamp(segment.end_ms, subtitle_format)
        if subtitle_format == "srt":
            rendered.extend([str(index), f"{start} --> {end}", text, ""])
        else:
            rendered.extend([f"{start} --> {end}", text, ""])
    return "\n".join(rendered).rstrip() + "\n"
