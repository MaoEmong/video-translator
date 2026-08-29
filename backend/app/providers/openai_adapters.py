import json
from collections.abc import Sequence
from dataclasses import dataclass
from time import perf_counter
from typing import Any, BinaryIO

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    RateLimitError,
)

from app.config import Settings


class ProviderError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class TranscribedSegment:
    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    source_language: str | None
    segments: list[TranscribedSegment]
    request_id: str | None
    latency_ms: int
    input_usage: int | None = None
    output_usage: int | None = None


@dataclass(frozen=True)
class TranslationInput:
    segment_id: str
    source_text: str


@dataclass(frozen=True)
class TranslationItem:
    segment_id: str
    translated_text: str


@dataclass(frozen=True)
class TranslationResult:
    translations: list[TranslationItem]
    response_id: str | None
    request_id: str | None
    input_usage: int | None
    output_usage: int | None
    latency_ms: int


def _request_id(response: Any) -> str | None:
    return getattr(response, "_request_id", None) or getattr(response, "request_id", None)


def _provider_error(operation: str, exc: Exception) -> ProviderError:
    if isinstance(exc, APITimeoutError):
        code = "OPENAI_TIMEOUT"
    elif isinstance(exc, RateLimitError):
        code = "OPENAI_RATE_LIMITED"
    elif isinstance(exc, AuthenticationError):
        code = "OPENAI_AUTH_ERROR"
    elif isinstance(exc, BadRequestError):
        code = "OPENAI_BAD_REQUEST"
    elif isinstance(exc, APIConnectionError):
        code = "OPENAI_CONNECTION_ERROR"
    elif isinstance(exc, APIStatusError) and (getattr(exc, "status_code", 0) or 0) >= 500:
        code = "OPENAI_SERVER_ERROR"
    else:
        code = f"OPENAI_{operation.upper()}_ERROR"
    detail = ""
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error_body = body.get("error")
        if isinstance(error_body, dict) and isinstance(error_body.get("message"), str):
            detail = error_body["message"][:500]
    if not detail:
        detail = str(exc)[:500]
    message = f"OpenAI {operation} request failed"
    if detail:
        message = f"{message}: {detail}"
    return ProviderError(code, message)


class OpenAISttAdapter:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.settings = settings
        self.client = client

    def _client(self) -> Any:
        if self.client is None:
            if not self.settings.openai_api_key:
                raise ProviderError("OPENAI_NOT_CONFIGURED", "OPENAI_API_KEY is not configured")
            self.client = OpenAI(
                api_key=self.settings.openai_api_key,
                timeout=self.settings.openai_timeout_seconds,
            )
        return self.client

    def transcribe(
        self,
        audio_file: BinaryIO,
        filename: str,
        content_type: str = "audio/wav",
        prompt: str | None = None,
        language: str | None = None,
    ) -> TranscriptionResult:
        started = perf_counter()
        try:
            client = self._client()
            request: dict[str, Any] = {
                "model": self.settings.openai_stt_model,
                "file": (filename, audio_file, content_type),
                "response_format": "verbose_json",
                "timestamp_granularities": ["segment"],
            }
            if prompt:
                request["prompt"] = prompt
            if language and language != "auto":
                request["language"] = language
            response = client.audio.transcriptions.create(**request)
        except ProviderError:
            raise
        except Exception as exc:
            raise _provider_error("transcription", exc) from exc

        raw_segments = getattr(response, "segments", None) or []
        segments = []
        for raw in raw_segments:
            start = getattr(raw, "start", None)
            end = getattr(raw, "end", None)
            text = str(getattr(raw, "text", "")).strip()
            if start is None or end is None or not text:
                continue
            segments.append(
                TranscribedSegment(
                    start_ms=max(0, round(float(start) * 1000)),
                    end_ms=max(0, round(float(end) * 1000)),
                    text=text,
                )
            )

        usage = getattr(response, "usage", None)
        return TranscriptionResult(
            text=str(getattr(response, "text", "")).strip(),
            source_language=getattr(response, "language", None),
            segments=segments,
            request_id=_request_id(response),
            latency_ms=round((perf_counter() - started) * 1000),
            input_usage=getattr(usage, "input_tokens", None) if usage else None,
            output_usage=getattr(usage, "output_tokens", None) if usage else None,
        )


class OpenAITranslationAdapter:
    response_schema = {
        "type": "object",
        "properties": {
            "translations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "segment_id": {"type": "string"},
                        "translated_text": {"type": "string"},
                    },
                    "required": ["segment_id", "translated_text"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["translations"],
        "additionalProperties": False,
    }

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.settings = settings
        self.client = client

    def _client(self) -> Any:
        if self.client is None:
            if not self.settings.openai_api_key:
                raise ProviderError("OPENAI_NOT_CONFIGURED", "OPENAI_API_KEY is not configured")
            self.client = OpenAI(
                api_key=self.settings.openai_api_key,
                timeout=self.settings.openai_timeout_seconds,
            )
        return self.client

    def translate(
        self,
        segments: Sequence[TranslationInput],
        source_language: str,
        target_language: str,
        style: str = "natural",
    ) -> TranslationResult:
        if not segments:
            return TranslationResult([], None, None, 0, 0, 0)
        if not self.settings.openai_translation_model:
            raise ProviderError(
                "OPENAI_TRANSLATION_MODEL_NOT_CONFIGURED", "Translation model is not configured"
            )

        payload = {
            "source_language": source_language,
            "target_language": target_language,
            "style": style,
            "segments": [
                {"segment_id": item.segment_id, "source_text": item.source_text}
                for item in segments
            ],
        }
        instructions = (
            "Translate subtitle segments. Preserve meaning and speaker intent. "
            "Return only the requested JSON structure. Do not change segment IDs or timestamps. "
            f"Translate from {source_language} to {target_language} in a {style} subtitle style."
        )
        started = perf_counter()
        try:
            client = self._client()
            response = client.responses.create(
                model=self.settings.openai_translation_model,
                input=[
                    {"role": "developer", "content": instructions},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "subtitle_translations",
                        "schema": self.response_schema,
                        "strict": True,
                    }
                },
                store=False,
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise _provider_error("translation", exc) from exc

        raw_output = str(getattr(response, "output_text", "")).strip()
        try:
            parsed = json.loads(raw_output)
            translations = [
                TranslationItem(
                    segment_id=str(item["segment_id"]),
                    translated_text=str(item["translated_text"]).strip(),
                )
                for item in parsed["translations"]
            ]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProviderError(
                "OPENAI_SCHEMA_ERROR", "OpenAI translation response has invalid JSON"
            ) from exc

        expected_ids = {item.segment_id for item in segments}
        actual_ids = [item.segment_id for item in translations]
        if set(actual_ids) != expected_ids or len(actual_ids) != len(expected_ids):
            raise ProviderError(
                "OPENAI_SCHEMA_ERROR", "Translation response does not match requested segments"
            )
        if any(not item.translated_text for item in translations):
            raise ProviderError("OPENAI_SCHEMA_ERROR", "Translation response contains empty text")

        usage = getattr(response, "usage", None)
        return TranslationResult(
            translations=translations,
            response_id=getattr(response, "id", None),
            request_id=_request_id(response),
            input_usage=getattr(usage, "input_tokens", None) if usage else None,
            output_usage=getattr(usage, "output_tokens", None) if usage else None,
            latency_ms=round((perf_counter() - started) * 1000),
        )
