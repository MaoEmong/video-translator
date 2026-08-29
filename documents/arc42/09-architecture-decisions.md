# 9. 아키텍처 결정

주요 결정은 별도 ADR로 관리한다. ADR에는 선택 이유, 고려한 대안, 결과와 현재 구현 상태를
함께 기록한다.

- [ADR-001 OpenAI Adapter 선택](../adr/ADR-001-openai-for-stt-and-translation.md)
- [ADR-002 Redis Queue와 Worker 선택](../adr/ADR-002-redis-queue-and-worker.md)
- [ADR-003 Private Object Storage와 signed URL 선택](../adr/ADR-003-signed-url-object-storage.md)
- [ADR-004 `whisper-1` 기본 STT 모델 선택](../adr/ADR-004-whisper-1-for-timed-segments.md)

운영 확장 시 새 결정을 추가하고, 기존 결정을 조용히 덮어쓰지 않는다.
