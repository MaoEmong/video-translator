# Architecture Decision Records

ADR은 구현 결과만 적는 문서가 아니라, 당시의 문제와 선택 이유를 남기는 기록이다. 상태가
`Accepted`인 결정은 현재 MVP에 반영되어 있으며, 나중에 바뀌면 새 ADR을 추가한다.

## 결정 목록

| ID | 결정 | 상태 |
|---|---|---|
| [ADR-001](./ADR-001-openai-for-stt-and-translation.md) | STT와 번역 provider로 OpenAI 사용 | Accepted |
| [ADR-002](./ADR-002-redis-queue-and-worker.md) | Redis Queue와 별도 Worker로 비동기 처리 | Accepted |
| [ADR-003](./ADR-003-signed-url-object-storage.md) | Private Object Storage와 signed URL 사용 | Accepted |
| [ADR-004](./ADR-004-whisper-1-for-timed-segments.md) | MVP 기본 STT 모델로 `whisper-1` 사용 | Accepted |

세부 구현 계획은 [arc42 결정 섹션](../arc42/09-architecture-decisions.md)과 [구현 계획](../12-implementation-plan.md)을
함께 참조한다.
