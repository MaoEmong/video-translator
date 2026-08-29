import io
import json
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.providers.openai_adapters import (
    OpenAISttAdapter,
    OpenAITranslationAdapter,
    ProviderError,
    TranslationInput,
)


def test_stt_adapter_maps_timed_segments() -> None:
    response = SimpleNamespace(
        text="Hello there",
        language="en",
        segments=[SimpleNamespace(start=1.25, end=2.75, text=" Hello there ")],
        _request_id="req_stt_1",
    )

    class Transcriptions:
        def create(self, **kwargs):
            assert kwargs["model"] == "gpt-test-stt"
            assert kwargs["timestamp_granularities"] == ["segment"]
            return response

    client = SimpleNamespace(audio=SimpleNamespace(transcriptions=Transcriptions()))
    adapter = OpenAISttAdapter(Settings(openai_stt_model="gpt-test-stt"), client=client)

    result = adapter.transcribe(io.BytesIO(b"audio"), "chunk.wav")

    assert result.source_language == "en"
    assert result.request_id == "req_stt_1"
    assert result.segments[0].start_ms == 1250
    assert result.segments[0].end_ms == 2750
    assert result.segments[0].text == "Hello there"


def test_translation_adapter_validates_segment_ids() -> None:
    response = SimpleNamespace(
        id="resp_1",
        output_text=json.dumps(
            {"translations": [{"segment_id": "seg_1", "translated_text": "안녕하세요"}]}
        ),
        usage=SimpleNamespace(input_tokens=10, output_tokens=4),
        _request_id="req_translation_1",
    )

    class Responses:
        def create(self, **kwargs):
            assert kwargs["text"]["format"]["type"] == "json_schema"
            return response

    client = SimpleNamespace(responses=Responses())
    settings = Settings(openai_translation_model="gpt-test-translation")
    adapter = OpenAITranslationAdapter(settings, client=client)

    result = adapter.translate(
        [TranslationInput(segment_id="seg_1", source_text="Hello")],
        source_language="en",
        target_language="ko",
    )

    assert result.response_id == "resp_1"
    assert result.request_id == "req_translation_1"
    assert result.translations[0].translated_text == "안녕하세요"
    assert result.input_usage == 10
    assert result.output_usage == 4


def test_translation_adapter_rejects_missing_segment() -> None:
    response = SimpleNamespace(
        output_text=json.dumps({"translations": []}),
        usage=None,
    )
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: response))
    adapter = OpenAITranslationAdapter(Settings(openai_translation_model="gpt-test"), client=client)

    with pytest.raises(ProviderError, match="does not match"):
        adapter.translate(
            [TranslationInput(segment_id="seg_1", source_text="Hello")],
            source_language="en",
            target_language="ko",
        )


def test_adapter_requires_api_key_when_no_client_is_injected() -> None:
    adapter = OpenAISttAdapter(Settings(openai_api_key=""))

    with pytest.raises(ProviderError) as error:
        adapter.transcribe(io.BytesIO(b"audio"), "chunk.wav")

    assert error.value.code == "OPENAI_NOT_CONFIGURED"
