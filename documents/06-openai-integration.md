# 06. OpenAI 연동

현재 모델 선택과 실제 연동에서 확인한 제약은 [ADR-004](./adr/ADR-004-whisper-1-for-timed-segments.md)에
기록한다.

## 연동 구조

OpenAI API 호출은 Controller나 Web UI에서 직접 하지 않는다.

```text
OpenAIClient
 ├─ OpenAISttAdapter
 │   └─ transcribe(audio_asset, options)
 └─ OpenAITranslationAdapter
     └─ translate(segment_batch, options)
```

## STT Adapter

입력:

```text
audio_asset
source_language_hint?
keyword_hints?
chunk_index
offset_ms
```

출력:

```text
provider
model
detected_language
segments[]
provider_metadata
```

Worker는 provider 결과를 내부 `transcripts`와 `transcript_segments` 구조로 변환한다.
현재 구현은 `whisper-1`을 기본 STT 모델로 사용한다. 자막 파이프라인에 필요한 세그먼트
시간 정보가 있어야 하므로 `verbose_json`과 `timestamp_granularities=["segment"]`를
요청하며, 사용자가 원본 언어를 지정한 경우 `language` 힌트도 전달한다. 다른 STT 모델을
사용하려면 동일한 timed segment 응답을 지원하는지 먼저 확인해야 한다.

## 번역 Adapter

입력:

```json
{
  "source_language": "en",
  "target_language": "ko",
  "translation_style": "natural",
  "segments": [
    {
      "segment_id": "seg_001",
      "source_text": "Where are you going?"
    }
  ]
}
```

출력:

```json
{
  "translations": [
    {
      "segment_id": "seg_001",
      "translated_text": "어디 가고 있어?"
    }
  ]
}
```

## LLM 응답 규칙

- 가능한 경우 JSON Schema 기반 구조화 출력을 사용한다.
- 입력에 없는 `segment_id`를 생성하지 못하게 한다.
- 요청한 모든 세그먼트를 반환하게 한다.
- 시간 정보는 반환하지 않게 한다.
- 설명, 마크다운, 코드 블록을 반환하지 않게 한다.
- 번역문 안의 줄바꿈은 자막 생성 단계에서 정규화한다.

## Prompt 관리

Prompt는 코드에 문자열로 흩어 놓지 않고 다음 정보를 함께 관리한다.

```text
prompt_name
prompt_version
source_language
target_language
translation_style
glossary_version
```

번역 결과에는 사용한 `prompt_version`을 기록한다.

## 오류 처리

Adapter는 외부 오류를 내부 오류 코드로 변환한다.

```text
OPENAI_TIMEOUT
OPENAI_RATE_LIMITED
OPENAI_AUTH_ERROR
OPENAI_BAD_REQUEST
OPENAI_SERVER_ERROR
OPENAI_SCHEMA_ERROR
```

현재 구현은 timeout, rate limit, 인증, 잘못된 요청, 연결 오류, 서버 오류를 구분하고,
나머지 호출 오류는 작업별 `OPENAI_*_ERROR`로 기록한다.

## 기록할 정보

```text
provider
model
request_id
response_id
input_usage
output_usage
latency_ms
status
error_json
created_at
```

API 키는 DB나 로그에 저장하지 않는다. 원본 오디오와 전체 prompt/raw response도 기본적으로 장기 보관하지 않는다.

## 설정

```text
OPENAI_API_KEY
OPENAI_STT_MODEL
OPENAI_TRANSLATION_MODEL
OPENAI_TIMEOUT_SECONDS
OPENAI_MAX_CONCURRENCY
```

모델 설정은 환경변수로 시작하되, 나중에 관리자 설정으로 이동할 수 있게 Adapter에 주입한다.
