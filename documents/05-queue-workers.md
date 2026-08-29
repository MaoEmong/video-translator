# 05. Queue와 Worker

## Queue 작업 종류

```text
video.validate
media.extract_audio
stt.transcribe
transcript.normalize
translation.translate
subtitle.build
job.finalize
```

## 메시지 형식

```json
{
  "job_id": "job_456",
  "step": "translation.translate",
  "transcript_id": "tr_001",
  "translation_version_id": "tv_002",
  "batch_index": 4,
  "attempt": 1
}
```

메시지는 필요한 ID와 위치 정보만 포함하고, 큰 텍스트나 오디오 데이터는 Storage와 DB에서 읽는다.

## 작업 상태

```text
QUEUED
  ↓
VALIDATING
  ↓
EXTRACTING_AUDIO
  ↓
TRANSCRIBING
  ↓
NORMALIZING
  ↓
TRANSLATING
  ↓
BUILDING_SUBTITLE
  ↓
COMPLETED
```

공통 종료 상태:

```text
FAILED
CANCELLED
```

## 재시도

> 아래 재시도와 운영 제어는 목표 설계다. 현재 포트폴리오 MVP는 단계 상태와 오류를 기록하고,
> 자동 재시도·Dead Letter Queue·distributed lock은 후속 작업으로 남겨둔다.

재시도 대상:

- Timeout
- 429 rate limit
- 일시적인 5xx
- 일시적인 Storage 또는 DB 연결 오류

재시도하지 않는 대상:

- 지원하지 않는 파일 형식
- 오디오 트랙 없음
- 잘못된 사용자 요청
- 번역 응답 Schema 오류
- 반복되는 인증 오류

재시도는 exponential backoff와 jitter를 사용한다. 최대 시도 횟수를 초과하면 Dead Letter Queue 또는 실패 기록으로 이동한다.

## 멱등성

- `idempotency_key`를 단계별로 저장한다.
- 이미 완료된 `job_step`은 중복 메시지가 와도 다시 실행하지 않는다.
- 파일 생성 전 동일 artifact가 있는지 확인한다.
- 번역 결과 저장 시 `(translation_version_id, transcript_segment_id)`를 unique로 둔다.

## 동시성

- Media 작업과 OpenAI API 작업의 동시성은 별도로 제한한다.
- OpenAI 호출은 사용자별 quota와 전체 rate limit을 함께 적용한다.
- 동일한 Job을 동시에 처리하지 않도록 distributed lock을 사용한다.
- 장시간 작업은 heartbeat 또는 lease 만료로 worker 장애를 감지한다.

## 취소

사용자가 취소하면:

1. Job을 `CANCEL_REQUESTED`로 표시한다.
2. Worker가 다음 checkpoint에서 취소 여부를 확인한다.
3. 실행 중인 외부 API 요청은 가능한 범위에서 중단한다.
4. 최종 상태를 `CANCELLED`로 전환한다.
